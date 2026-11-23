import json
import logging

from shared.observability import JsonFormatter


def test_json_formatter_emits_structured_service_log(monkeypatch):
    monkeypatch.setenv('SERVICE_NAME', 'collection')
    record = logging.LogRecord('logiq.test', logging.WARNING, __file__, 10, 'request failed', (), None)
    record.request_id = 'req-123'
    payload = json.loads(JsonFormatter().format(record))
    assert payload['service'] == 'collection'
    assert payload['level'] == 'WARNING'
    assert payload['message'] == 'request failed'
    assert payload['request_id'] == 'req-123'
    assert payload['timestamp']


def test_json_formatter_reads_async_request_context(monkeypatch):
    from shared.observability import request_id_context
    monkeypatch.setenv('SERVICE_NAME', 'gateway')
    token = request_id_context.set('trace-456')
    try:
        record = logging.LogRecord('logiq.test', logging.INFO, __file__, 20, 'proxy request', (), None)
        payload = json.loads(JsonFormatter().format(record))
        assert payload['request_id'] == 'trace-456'
    finally:
        request_id_context.reset(token)


def test_metric_path_normalizes_uuid_and_numeric_segments():
    from shared.observability import normalize_metric_path
    assert normalize_metric_path('/v1/logs/123e4567-e89b-12d3-a456-426614174000') == '/v1/logs/{id}'
    assert normalize_metric_path('/v1/datasets/42/events') == '/v1/datasets/{id}/events'
