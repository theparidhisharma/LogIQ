"""Retryable MinIO artifact cleanup for tenant-owned dataset tombstones.

The dataset row is retained as a tombstone for auditability. If the worker dies
after MinIO deletion but before the DB commit, the next pass repeats the
idempotent object deletion and then commits the tombstone state.
"""
import logging
import os
import time
from sqlalchemy import text
from shared.common import dataset_db
from shared.object_storage import delete_raw_dataset
from shared.common import producer
import json, uuid

log = logging.getLogger("logiq.dataset.deletion")
POLL_SECONDS = float(os.getenv("DATASET_DELETE_POLL_SECONDS", "5"))


def process_one_deletion() -> bool:
    # First remove the object; persist a stable outbox event in the same DB
    # transaction as the artifact tombstone. A crash before commit repeats the
    # idempotent MinIO delete; a crash after commit leaves a publishable outbox.
    with dataset_db().begin() as conn:
        row = conn.execute(text("""SELECT id,tenant_id,object_key FROM datasets
            WHERE deletion_requested_at IS NOT NULL AND deleted_at IS NULL
              AND artifact_deleted_at IS NULL
            ORDER BY deletion_requested_at,created_at
            LIMIT 1 FOR UPDATE SKIP LOCKED""")).mappings().first()
        if not row:
            return False
        try:
            if row["object_key"]:
                delete_raw_dataset(row["object_key"])
        except Exception as exc:
            conn.execute(text("""UPDATE datasets SET deletion_attempts=deletion_attempts+1,
                deletion_error=:error WHERE id=:id"""),
                {"id": row["id"], "error": type(exc).__name__})
            return False
        event_id = f"dataset-deletion:{row['id']}"
        payload = {"event_id": event_id, "event_type": "dataset.deletion_requested",
                   "dataset_id": row["id"], "tenant_id": row["tenant_id"], "schema_version": 1}
        conn.execute(text("""UPDATE datasets SET object_key=NULL,sha256=NULL,byte_size=NULL,
            artifact_deleted_at=now(),deletion_error=NULL WHERE id=:id"""), {"id": row["id"]})
        conn.execute(text("""INSERT INTO dataset_deletion_outbox(event_id,dataset_id,tenant_id,payload)
            VALUES(:event_id,:dataset_id,:tenant,CAST(:payload AS jsonb))
            ON CONFLICT(event_id) DO NOTHING"""),
            {"event_id": event_id, "dataset_id": row["id"], "tenant": row["tenant_id"],
             "payload": json.dumps(payload)})
    return True


def publish_one_deletion_event() -> bool:
    with dataset_db().connect() as conn:
        row = conn.execute(text("""SELECT event_id,payload FROM dataset_deletion_outbox
            WHERE published_at IS NULL ORDER BY created_at LIMIT 1""")).mappings().first()
    if not row:
        return False
    client = producer()
    try:
        client.send("datasets.deletion_requested", dict(row["payload"]),
                    key=str(row["event_id"]).encode()).get(timeout=30)
        client.flush(timeout=30)
    except Exception as exc:
        with dataset_db().begin() as conn:
            conn.execute(text("""UPDATE dataset_deletion_outbox SET publish_attempts=publish_attempts+1,
                last_error=:error WHERE event_id=:id"""),
                {"id": row["event_id"], "error": type(exc).__name__})
        raise
    finally:
        client.close()
    with dataset_db().begin() as conn:
        conn.execute(text("""UPDATE dataset_deletion_outbox SET published_at=now(),
            publish_attempts=publish_attempts+1,last_error=NULL WHERE event_id=:id"""),
            {"id": row["event_id"]})
    return True


def run_forever():
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    while True:
        try:
            did_work = process_one_deletion()
            did_work = publish_one_deletion_event() or did_work
            if not did_work:
                time.sleep(POLL_SECONDS)
        except Exception:
            log.exception("dataset artifact deletion failed; tombstone will be retried")
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run_forever()
