"""Process-local Prometheus instrumentation for LogIQ workers and JSON logs."""
import json
import logging
import os
import re
import socket
import threading
import time
from contextvars import ContextVar
from datetime import datetime, timezone

from prometheus_client import Counter, Gauge, Histogram, start_http_server

WORKER_PROCESSED = Counter('logiq_worker_messages_processed_total', 'Messages successfully processed by a worker', ['service', 'topic'])
WORKER_FAILED = Counter('logiq_worker_messages_failed_total', 'Messages sent to a dead-letter topic or exhausted by a worker', ['service', 'topic'])
WORKER_RETRIES = Counter('logiq_worker_message_retries_total', 'Message processing retries', ['service', 'topic'])
WORKER_DURATION = Histogram('logiq_worker_message_duration_seconds', 'Worker message processing duration', ['service', 'topic'])
WORKER_HEARTBEAT = Gauge('logiq_worker_last_heartbeat_timestamp_seconds', 'Unix timestamp of the last worker loop heartbeat', ['service'])
WORKER_CONNECTED = Gauge('logiq_worker_connected', '1 when the worker consumer has partitions assigned and its Kafka bootstrap is reachable, else 0', ['service'])
WORKER_UP = Gauge('logiq_worker_process_up', 'Whether the worker process initialized its metrics endpoint', ['service', 'instance'])

request_id_context: ContextVar[str | None] = ContextVar("logiq_request_id", default=None)

_started = set()
_lock = threading.Lock()


def start_worker_metrics(service: str | None = None, port: int | None = None) -> None:
    configure_json_logging()
    service = service or os.getenv('SERVICE_NAME', 'logiq-worker')
    port = int(port if port is not None else os.getenv('METRICS_PORT', '9100'))
    with _lock:
        if service in _started:
            return
        start_http_server(port, addr='0.0.0.0')
        WORKER_UP.labels(service, socket.gethostname()).set(1)
        WORKER_HEARTBEAT.labels(service).set(time.time())
        _started.add(service)


def worker_heartbeat(service: str | None = None) -> None:
    WORKER_HEARTBEAT.labels(service or os.getenv('SERVICE_NAME', 'logiq-worker')).set(time.time())


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per line; avoid serializing arbitrary message objects."""
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            'timestamp': datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'service': os.getenv('SERVICE_NAME', 'logiq-service'),
            'message': record.getMessage(),
        }
        request_id = getattr(record, 'request_id', None) or request_id_context.get()
        if request_id:
            payload['request_id'] = request_id
        if record.exc_info:
            payload['exception'] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_json_logging() -> None:
    root = logging.getLogger()
    if getattr(root, '_logiq_json_configured', False):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.handlers[:] = [handler]
    root.setLevel(os.getenv('LOG_LEVEL', 'INFO').upper())
    root._logiq_json_configured = True


def normalize_metric_path(path: str) -> str:
    """Reduce common ID-bearing URL segments before using a path as a metric label."""
    path = re.sub(r"(?i)(?<=/)[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?=/|$)", "{id}", path)
    path = re.sub(r"(?<=/)\d+(?=/|$)", "{id}", path)
    return path
