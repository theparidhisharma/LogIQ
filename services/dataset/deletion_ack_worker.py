"""Finalize Dataset tombstones after Intelligence confirms data erasure."""
import json, logging, os, time
from kafka import KafkaConsumer
from sqlalchemy import text
from shared.common import dataset_db, KAFKA, producer

log = logging.getLogger("logiq.dataset.deletion_ack")

def apply_ack(payload, engine=None):
    if payload.get("event_type") != "dataset.deletion_acknowledged" or payload.get("schema_version") != 1:
        raise ValueError("unsupported dataset deletion acknowledgement")
    if payload.get("service") != "intelligence" or not all(payload.get(k) for k in ("event_id", "dataset_id", "tenant_id")):
        raise ValueError("invalid dataset deletion acknowledgement")
    engine = engine or dataset_db()
    with engine.begin() as conn:
        row = conn.execute(text("""UPDATE datasets SET deleted_at=COALESCE(deleted_at,now()),
            status='deleted',deletion_error=NULL WHERE id=:dataset AND tenant_id=:tenant
            AND deletion_requested_at IS NOT NULL AND artifact_deleted_at IS NOT NULL
            RETURNING id"""), {"dataset": payload["dataset_id"], "tenant": payload["tenant_id"]}).scalar_one_or_none()
    return bool(row)

def run_forever():
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    while True:
        consumer = None
        try:
            consumer = KafkaConsumer("datasets.deletion_acknowledged", bootstrap_servers=KAFKA,
                group_id="logiq-dataset-deletion-ack-v1", enable_auto_commit=False,
                auto_offset_reset="earliest", value_deserializer=lambda b: json.loads(b.decode()))
            for record in consumer:
                try:
                    accepted = apply_ack(record.value)
                    if not accepted:
                        raise ValueError("acknowledgement does not match a pending tenant-owned tombstone")
                except Exception as exc:
                    # Quarantine invalid or unmatchable acknowledgements instead
                    # of pinning the partition forever. Valid messages are committed
                    # only after the Dataset DB transaction succeeds.
                    p = producer()
                    try:
                        p.send("datasets.deletion_acknowledged.dlq", {
                            "error_type": type(exc).__name__, "payload": record.value,
                            "source_topic": "datasets.deletion_acknowledged"},
                            key=str(record.value.get("dataset_id", "unknown")).encode()).get(timeout=30)
                        p.flush(timeout=30)
                    finally:
                        p.close()
                consumer.commit()
        except Exception:
            log.exception("dataset deletion acknowledgement consumer unavailable; reconnecting")
            time.sleep(5)
        finally:
            if consumer:
                consumer.close()

if __name__ == "__main__":
    run_forever()
