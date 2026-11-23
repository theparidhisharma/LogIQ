"""Restartable publisher for raw dataset artifacts.

A batch is acknowledged only after Kafka confirms delivery and the cursor commits.
A crash between those operations can replay a batch; deterministic event IDs make
that replay idempotent in the downstream persistence stage.
"""
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timezone

from sqlalchemy import text

from shared.common import dataset_db, event, parse_line, producer
from shared.dataset_utils import dataset_event_id
from shared.object_storage import sample_raw_dataset, iter_raw_dataset_lines
from services.parser.engine import benchmark, parser_by_name
from shared.observability import (WORKER_FAILED, WORKER_PROCESSED, WORKER_HEARTBEAT, start_worker_metrics, worker_heartbeat)

log = logging.getLogger("logiq.dataset.publisher")
BATCH_SIZE = int(os.getenv("DATASET_PUBLISH_BATCH_SIZE", "500"))
if not 1 <= BATCH_SIZE <= 5000:
    raise RuntimeError("DATASET_PUBLISH_BATCH_SIZE must be between 1 and 5000")
MAX_ATTEMPTS = int(os.getenv("DATASET_PUBLISH_MAX_ATTEMPTS", "10"))
POLL_SECONDS = float(os.getenv("DATASET_PUBLISH_POLL_SECONDS", "2"))


def publish_events_acknowledged(producer_client, records, timeout: float = 30.0) -> int:
    """Wait for Kafka acknowledgement of every record before cursor advancement."""
    futures = [producer_client.send(topic, payload, key=key)
               for topic, payload, key in records]
    producer_client.flush(timeout=timeout)
    for future in futures:
        future.get(timeout=timeout)
    return len(futures)



def publish_one_batch() -> bool:
    """Benchmark and publish one batch, committing parser choice before Kafka send."""
    dataset_id = None
    try:
        # Phase 1: claim/read the current job and persist the parser decision.
        # This transaction commits before Kafka publication so downstream parser
        # workers can always observe the selected parser when the first event arrives.
        with dataset_db().begin() as conn:
            job = conn.execute(text("""SELECT j.dataset_id,j.tenant_id,j.processing_attempt,
                    j.next_line_number,j.cancel_requested,d.name,d.object_key,d.sha256,d.line_count,
                    d.selected_parser,d.parser_policy,d.parser_seed,d.parser_sample_size,d.parser_min_quality,
                    d.parser_sampling_strategy,d.parser_ground_truth
                FROM dataset_publish_jobs j JOIN datasets d ON d.id=j.dataset_id
                WHERE j.status IN ('queued','publishing') AND j.next_attempt_at <= now() AND d.deletion_requested_at IS NULL
                ORDER BY j.created_at LIMIT 1 FOR UPDATE OF j SKIP LOCKED""")).mappings().first()
            if not job:
                return False
            dataset_id = job["dataset_id"]
            if job["cancel_requested"]:
                conn.execute(text("UPDATE dataset_publish_jobs SET status='cancelled',updated_at=now() WHERE dataset_id=:id"), {"id": dataset_id})
                conn.execute(text("UPDATE datasets SET status='cancelled',completed_at=now(),error_message=NULL WHERE id=:id AND status NOT IN ('completed','failed')"), {"id": dataset_id})
                return True
            if not job["selected_parser"]:
                lines, sample_indices, total_lines = sample_raw_dataset(
                    job["object_key"], job["sha256"], int(job["parser_sample_size"]),
                    job["parser_sampling_strategy"], int(job["parser_seed"]))
                if job["parser_policy"] in {"quality_constrained", "multi_objective"}:
                    labels = job["parser_ground_truth"]
                    if labels is None:
                        raise ValueError("ground-truth labels are required by the selected parser policy")
                    sampled_labels = [labels[index] for index in sample_indices]
                else:
                    sampled_labels = None
                report = benchmark(
                    lines,
                    seed=int(job["parser_seed"]),
                    sample_size=len(lines),
                    sampling_strategy="first_n",
                    selection_policy=job["parser_policy"],
                    min_quality=float(job["parser_min_quality"]),
                    ground_truth_templates=sampled_labels,
                )
                report["sampling_strategy"] = job["parser_sampling_strategy"]
                report["sample_indices"] = sample_indices
                report["dataset_line_count"] = total_lines
                selected_name = report.get("selected_parser")
                if not selected_name:
                    raise RuntimeError("No eligible parser could be selected for this dataset")
                selected = parser_by_name(selected_name)
                conn.execute(text("""UPDATE datasets SET selected_parser=:parser,
                    selected_parser_version=:version,parser_benchmark=CAST(:report AS jsonb),
                    parser_selected_at=now() WHERE id=:id AND selected_parser IS NULL"""),
                    {"parser": selected.name, "version": selected.version,
                     "report": json.dumps(report), "id": dataset_id})

        # Phase 2: reacquire the job lock. The benchmark decision is now committed
        # and visible to parser workers before any event is emitted to Kafka.
        with dataset_db().begin() as conn:
            current = conn.execute(text("""SELECT j.dataset_id,j.tenant_id,j.processing_attempt,
                    j.next_line_number,j.next_byte_offset,j.cancel_requested,j.published_bytes,j.total_publish_ms,d.name,d.source_type,d.object_key
                FROM dataset_publish_jobs j JOIN datasets d ON d.id=j.dataset_id
                WHERE j.dataset_id=:id AND j.status IN ('queued','publishing')
                  AND j.next_attempt_at <= now() AND d.deletion_requested_at IS NULL
                FOR UPDATE OF j SKIP LOCKED"""), {"id": dataset_id}).mappings().first()
            if not current:
                return True  # another publisher acquired or completed the job
            if current['cancel_requested']:
                conn.execute(text("UPDATE dataset_publish_jobs SET status='cancelled',updated_at=now() WHERE dataset_id=:id"), {'id': dataset_id})
                conn.execute(text("UPDATE datasets SET status='cancelled',completed_at=now(),error_message=NULL WHERE id=:id AND status NOT IN ('completed','failed')"), {'id': dataset_id})
                return True
            batch_started = time.perf_counter()
            batch = list(iter_raw_dataset_lines(current["object_key"], int(current["next_line_number"]), BATCH_SIZE, int(current["next_byte_offset"])))
            if not batch:
                conn.execute(text("""UPDATE dataset_publish_jobs SET status='published',
                    updated_at=now(),last_batch_at=now(),last_error=NULL WHERE dataset_id=:id"""), {"id": dataset_id})
                return True

            records = []
            for line_number, line, _end_offset in batch:
                ts, severity, message = parse_line(line)
                service_match = re.search(r"\bservice=([A-Za-z0-9_.-]+)", message)
                service_name = service_match.group(1) if service_match else "unknown"
                application_id = "synthetic-app" if current["source_type"] == "synthetic" else "dataset-import"
                item = event(message, tenant_id=current["tenant_id"],
                    application_id=application_id, timestamp=ts or datetime.now(timezone.utc).isoformat(),
                    severity=severity, source_type=current["source_type"], source_name=current["name"],
                    service_name=service_name, attributes={"line_number": line_number},
                    dataset_id=dataset_id)
                item["event_id"] = dataset_event_id(dataset_id, line_number)
                item["processing_attempt"] = int(current["processing_attempt"])
                records.append(("logs.raw", item, dataset_id))
            p = producer()
            try:
                publish_events_acknowledged(p, records, timeout=30)
            finally:
                p.close()

            next_line = batch[-1][0] + 1
            next_offset = batch[-1][2]
            elapsed_ms = max(0, int((time.perf_counter() - batch_started) * 1000))
            byte_delta = max(0, next_offset - int(current['next_byte_offset']))
            conn.execute(text("""UPDATE dataset_publish_jobs SET next_line_number=:next,next_byte_offset=:byte_offset,
                status='publishing',publish_attempts=0,last_error=NULL,updated_at=now(),
                started_at=COALESCE(started_at,now()),last_batch_at=now(),
                total_publish_ms=total_publish_ms+:elapsed,published_bytes=published_bytes+:bytes,last_batch_ms=:elapsed
                WHERE dataset_id=:id"""), {"next": next_line, "byte_offset": next_offset, "elapsed": elapsed_ms, "bytes": byte_delta, "id": dataset_id})
            return True
    except Exception as exc:
        raise PublishBatchError(dataset_id or "unknown", type(exc).__name__) from exc


class PublishBatchError(RuntimeError):
    def __init__(self, dataset_id: str, error_type: str):
        self.dataset_id = dataset_id
        self.error_type = error_type
        super().__init__(f"dataset {dataset_id}: {error_type}")


def record_failure(error: PublishBatchError) -> None:
    with dataset_db().begin() as conn:
        attempts = conn.execute(text("""UPDATE dataset_publish_jobs SET
            publish_attempts=publish_attempts+1,last_error=:error,
            status=CASE WHEN cancel_requested THEN 'cancelled' WHEN publish_attempts+1 >= :max_attempts THEN 'failed' ELSE 'queued' END,
            next_attempt_at=now() + (LEAST(60, POWER(2,LEAST(publish_attempts,6))) * interval '1 second'),
            updated_at=now()
            WHERE dataset_id=:id RETURNING publish_attempts,status"""),
            {"id": error.dataset_id, "error": error.error_type, "max_attempts": MAX_ATTEMPTS}).mappings().first()
        if attempts and attempts["status"] in {"failed", "cancelled"}:
            if attempts["status"] == "cancelled":
                conn.execute(text("UPDATE datasets SET status='cancelled',completed_at=now(),error_message=NULL WHERE id=:id"), {"id": error.dataset_id})
            else:
                conn.execute(text("""UPDATE datasets SET status='failed',error_message=:error,
                    completed_at=now() WHERE id=:id"""),
                    {"id": error.dataset_id, "error": f"Dataset publishing failed after {attempts['publish_attempts']} attempts: {error.error_type}"})


def run_forever():
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    service = os.getenv("SERVICE_NAME", "dataset-publisher-worker")
    start_worker_metrics(service)
    while True:
        worker_heartbeat(service)
        try:
            found = publish_one_batch()
            if found:
                WORKER_PROCESSED.labels(service, "dataset_publish_jobs").inc()
            if not found:
                time.sleep(POLL_SECONDS)
        except PublishBatchError as exc:
            WORKER_FAILED.labels(service, "dataset_publish_jobs").inc()
            log.exception("dataset batch publication failed")
            record_failure(exc)
        except Exception:
            WORKER_FAILED.labels(service, "dataset_publish_jobs").inc()
            log.exception("dataset publisher loop failed")
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run_forever()
