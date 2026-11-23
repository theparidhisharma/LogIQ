"""Apply dataset erasure commands to Intelligence-owned persisted records.

Analytics queries the same Core log_events read model, so removing rows here
also removes them from Analytics without a second competing delete consumer.
"""
import json, logging, os, time
from kafka import KafkaConsumer
from sqlalchemy import text
from shared.common import db, producer, KAFKA

log = logging.getLogger("logiq.intelligence.dataset_deletion")
TOPIC = "datasets.deletion_requested"
GROUP = "logiq-intelligence-dataset-deletion-v1"

def validate_command(payload):
    if payload.get("event_type") != "dataset.deletion_requested" or payload.get("schema_version") != 1:
        raise ValueError("unsupported dataset deletion event")
    if not payload.get("event_id") or not payload.get("dataset_id") or not payload.get("tenant_id"):
        raise ValueError("dataset deletion event requires event_id, dataset_id and tenant_id")
    return payload

def apply_deletion(payload, engine=None):
    payload = validate_command(payload)
    engine = engine or db()
    with engine.begin() as conn:
        existing = conn.execute(text("SELECT tenant_id,event_id FROM dataset_deletion_receipts WHERE dataset_id=:dataset"),
            {"dataset": payload["dataset_id"]}).mappings().first()
        if existing:
            if existing["tenant_id"] != payload["tenant_id"]:
                raise ValueError("dataset deletion receipt tenant mismatch")
            return {"deleted_events": 0, "duplicate": True}
        deleted_ids = conn.execute(text("""DELETE FROM log_events
            WHERE dataset_id=:dataset AND tenant_id=:tenant RETURNING event_id"""),
            {"dataset": payload["dataset_id"], "tenant": payload["tenant_id"]}).scalars().all()
        # Registry rows are aggregate across datasets. Recompute their counts and
        # timestamps from surviving events rather than deleting shared templates.
        conn.execute(text("""WITH remaining AS (
            SELECT tenant_id,application_id,service_name,template_id,count(*) AS frequency,
                   min(timestamp) AS first_seen,max(timestamp) AS last_seen,
                   min(template) AS template
            FROM log_events WHERE template_id IS NOT NULL
            GROUP BY tenant_id,application_id,service_name,template_id
        ) UPDATE template_registry tr SET frequency=r.frequency,first_seen=r.first_seen,
            last_seen=r.last_seen,template=r.template FROM remaining r
            WHERE tr.tenant_id=r.tenant_id AND tr.application_id=r.application_id
              AND tr.service_name=r.service_name AND tr.template_id=r.template_id"""))
        conn.execute(text("""DELETE FROM template_registry tr WHERE NOT EXISTS (
            SELECT 1 FROM log_events e WHERE e.tenant_id=tr.tenant_id
              AND e.application_id=tr.application_id AND e.service_name=tr.service_name
              AND e.template_id=tr.template_id)"""))
        if deleted_ids:
            conn.execute(text("""DELETE FROM anomalies WHERE kind='error_event'
                AND sample->>'event_id' = ANY(:event_ids)"""), {"event_ids": deleted_ids})
        conn.execute(text("""INSERT INTO dataset_deletion_receipts(dataset_id,tenant_id,event_id,deleted_events)
            VALUES(:dataset,:tenant,:event,:count) ON CONFLICT(dataset_id) DO NOTHING"""), {
                "dataset": payload["dataset_id"], "tenant": payload["tenant_id"],
                "event": payload["event_id"], "count": len(deleted_ids)})
    return {"deleted_events": len(deleted_ids), "duplicate": False}

def process_payload(payload, engine=None, send_ack=None):
    result = apply_deletion(payload, engine=engine)
    ack = {"event_type": "dataset.deletion_acknowledged", "schema_version": 1,
           "event_id": f"dataset-deletion-ack:{payload['dataset_id']}",
           "dataset_id": payload["dataset_id"], "tenant_id": payload["tenant_id"],
           "service": "intelligence", "deleted_events": result["deleted_events"]}
    if send_ack:
        send_ack(ack)
    else:
        p = producer()
        try:
            p.send("datasets.deletion_acknowledged", ack, key=payload["dataset_id"].encode()).get(timeout=30)
            p.flush(timeout=30)
        finally:
            p.close()
    return result

def run_forever():
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    while True:
        consumer = None
        try:
            consumer = KafkaConsumer(TOPIC, bootstrap_servers=KAFKA, group_id=GROUP,
                enable_auto_commit=False, auto_offset_reset="earliest", value_deserializer=lambda b: json.loads(b.decode()))
            for record in consumer:
                process_payload(record.value)
                consumer.commit()
        except Exception:
            log.exception("dataset deletion consumer unavailable; will reconnect")
            time.sleep(5)
        finally:
            if consumer:
                consumer.close()

if __name__ == "__main__":
    run_forever()
