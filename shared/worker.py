"""At-least-once Kafka stage runner with bounded retries and dead-letter routing.

Health contract (exported via Prometheus on METRICS_PORT):
- logiq_worker_connected = 1 only while the consumer has partitions assigned AND a
  Kafka bootstrap connection is live. 0 during connect/reconnect and during broker outages.
- logiq_worker_last_heartbeat_timestamp_seconds is refreshed on every poll loop while
  connected, so an idle but healthy worker stays fresh and a stalled or disconnected one goes stale.
"""
import json, logging, os, time
from kafka import KafkaConsumer, KafkaProducer
from shared.observability import (WORKER_CONNECTED, WORKER_DURATION, WORKER_FAILED, WORKER_PROCESSED,
                                  WORKER_RETRIES, start_worker_metrics, worker_heartbeat)

log = logging.getLogger("logiq.worker")
POLL_MS = 1000


def _is_connected(consumer) -> bool:
    if not consumer.assignment():
        return False
    try:
        # kafka-python 2.0.x: True while a bootstrap broker connection is live.
        return bool(consumer._client.bootstrap_connected())
    except Exception:
        return True


def _dead_letter(record, *, producer, input_topic, service, max_retries, exc, payload):
    dead = {
        "source_topic": input_topic, "source_partition": record.partition,
        "source_offset": record.offset, "failed_at": time.time(),
        "error_type": type(exc).__name__, "payload": payload,
    }
    WORKER_FAILED.labels(service, input_topic).inc()
    producer.send(f"{input_topic}.dlq", dead).get(timeout=30)
    producer.flush(timeout=30)
    if payload.get("dataset_id") and input_topic != "logs.persisted":
        try:
            producer.send("logs.persisted", {
                "event_type": "dataset_processing_failed",
                "event_id": f"{payload.get('event_id', record.offset)}:{input_topic}:failed",
                "dataset_id": payload.get("dataset_id"),
                "tenant_id": payload.get("tenant_id", "default"),
                "processing_attempt": payload.get("processing_attempt", 1),
                "source_topic": input_topic,
                "error": f"{input_topic} failed after {max_retries + 1} attempts: {type(exc).__name__}",
            }, key=str(payload.get("dataset_id")).encode()).get(timeout=30)
            producer.flush(timeout=30)
        except Exception:
            log.exception("could not publish dataset failure event")
    log.exception("stage message moved to DLQ")


def _process(record, *, consumer, producer, transform, input_topic, output_topic, service, max_retries):
    payload = record.value
    started = time.perf_counter()
    for attempt in range(max_retries + 1):
        try:
            result = transform(payload)
            if result is not None:
                values = result if isinstance(result, list) else [result]
                for value in values:
                    producer.send(output_topic, value, key=str(value.get("application_id") or value.get("event_id") or "").encode()).get(timeout=30)
            producer.flush(timeout=30)
            consumer.commit()
            WORKER_PROCESSED.labels(service, input_topic).inc()
            WORKER_DURATION.labels(service, input_topic).observe(time.perf_counter() - started)
            return
        except Exception as exc:
            if attempt < max_retries:
                WORKER_RETRIES.labels(service, input_topic).inc()
                time.sleep(min(2 ** attempt, 8))
                continue
            WORKER_DURATION.labels(service, input_topic).observe(time.perf_counter() - started)
            _dead_letter(record, producer=producer, input_topic=input_topic, service=service,
                         max_retries=max_retries, exc=exc, payload=payload)
            consumer.commit()
            return


def run_stage(*, input_topic: str, output_topic: str, group_id: str, transform, max_retries: int = 3):
    service = os.getenv("SERVICE_NAME", group_id)
    start_worker_metrics(service)
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    WORKER_CONNECTED.labels(service).set(0)
    while True:
        consumer = None
        producer = None
        try:
            consumer = KafkaConsumer(
                input_topic, bootstrap_servers=bootstrap, group_id=group_id,
                enable_auto_commit=False, auto_offset_reset="earliest",
                value_deserializer=lambda b: json.loads(b.decode("utf-8")),
                max_poll_records=100, session_timeout_ms=30000,
                heartbeat_interval_ms=10000,
            )
            producer = KafkaProducer(
                bootstrap_servers=bootstrap,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                retries=5, acks="all", max_in_flight_requests_per_connection=1,
            )
            log.info(json.dumps({"event": "worker_started", "input": input_topic, "output": output_topic, "group": group_id}))
            while True:
                records = consumer.poll(timeout_ms=POLL_MS)
                connected = _is_connected(consumer)
                WORKER_CONNECTED.labels(service).set(1 if connected else 0)
                if connected:
                    worker_heartbeat(service)
                # While not connected the gauge is 0 and the heartbeat goes stale; poll keeps retrying.
                for _tp, messages in (records.items() if connected else []):
                    for record in messages:
                        _process(record, consumer=consumer, producer=producer, transform=transform,
                                 input_topic=input_topic, output_topic=output_topic, service=service,
                                 max_retries=max_retries)
        except Exception:
            WORKER_CONNECTED.labels(service).set(0)
            log.exception("worker connection failed; reconnecting")
            time.sleep(5)
        finally:
            if consumer:
                consumer.close()
            if producer:
                producer.close()
