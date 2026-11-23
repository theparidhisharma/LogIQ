from datetime import datetime, timezone

from services.collection.otlp import decode_otlp_json, _severity


def test_otlp_json_flattens_resource_scope_and_log_record():
    payload = {
        'resourceLogs': [{
            'resource': {'attributes': [
                {'key': 'service.name', 'value': {'stringValue': 'checkout'}},
                {'key': 'logiq.tenant_id', 'value': {'stringValue': 'tenant-1'}},
                {'key': 'deployment.environment.name', 'value': {'stringValue': 'prod'}},
            ]},
            'scopeLogs': [{
                'scope': {'name': 'example.instrumentation', 'version': '1.2'},
                'logRecords': [{
                    'timeUnixNano': '1795190400000000000',
                    'severityNumber': 17,
                    'severityText': 'FATAL',
                    'body': {'stringValue': 'payment failed'},
                    'traceId': '0123456789abcdef0123456789abcdef',
                    'spanId': '0123456789abcdef',
                    'attributes': [{'key': 'http.status_code', 'value': {'intValue': '500'}}],
                }],
            }],
        }]
    }
    records = decode_otlp_json(payload)
    assert len(records) == 1
    record = records[0]
    assert record['message'] == 'payment failed'
    assert record['severity'] == 'FATAL'
    assert record['service_name'] == 'checkout'
    assert record['tenant_id'] == 'tenant-1'
    assert record['environment'] == 'prod'
    assert record['trace_id'] == '0123456789abcdef0123456789abcdef'
    assert record['span_id'] == '0123456789abcdef'
    assert record['attributes']['http.status_code'] == '500'
    assert record['source_type'] == 'otlp'


def test_otlp_empty_resource_logs_returns_no_records():
    assert decode_otlp_json({'resourceLogs': []}) == []


def test_otlp_severity_number_mapping():
    assert _severity(9, '') == 'INFO'
    assert _severity(13, '') == 'WARN'
    assert _severity(5, '') == 'DEBUG'
    assert _severity(0, '') == 'INFO'
    assert _severity(17, '') == 'ERROR'
    assert _severity(21, '') == 'FATAL'
    assert _severity('SEVERITY_NUMBER_ERROR2', '') == 'ERROR'
    assert _severity(17, 'CRITICAL') == 'CRITICAL'


def test_otlp_http_internal_token_publishes_to_raw_topic(monkeypatch):
    from contextlib import contextmanager
    from fastapi.testclient import TestClient
    from services.collection import main as collection

    class Result:
        def scalar(self): return 1
    class Conn:
        def execute(self, *args, **kwargs): return Result()
    class Engine:
        @contextmanager
        def connect(self): yield Conn()
    class Producer:
        def __init__(self): self.sent = []
        def send(self, topic, value, key=None):
            self.sent.append((topic, value, key))
            return type('Future', (), {'get': lambda self, timeout=None: None})()
        def flush(self): pass
    producer = Producer()
    monkeypatch.setenv('LOGIQ_OTLP_INGEST_TOKEN', 'test-secret')
    monkeypatch.setattr(collection, 'identity_db', lambda: Engine())
    monkeypatch.setattr(collection, 'producer', lambda: producer)
    payload = {'resourceLogs': [{'resource': {'attributes': [
        {'key': 'service.name', 'value': {'stringValue': 'checkout'}},
        {'key': 'logiq.tenant_id', 'value': {'stringValue': 'tenant-a'}},
    ]}, 'scopeLogs': [{'logRecords': [{'body': {'stringValue': 'hello'}}]}]}]}
    response = TestClient(collection.app).post('/v1/otlp/logs', json=payload,
        headers={'x-logiq-otlp-token': 'test-secret'})
    assert response.status_code == 200, response.text
    assert response.json()['accepted'] == 1
    assert producer.sent[0][0] == 'logs.raw'
    assert producer.sent[0][1]['tenant_id'] == 'tenant-a'
    assert producer.sent[0][1]['message'] == 'hello'


def test_otlp_protobuf_decodes_ids_and_enum_severity():
    from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
    from services.collection.otlp import decode_otlp_protobuf
    request = ExportLogsServiceRequest()
    resource_log = request.resource_logs.add()
    item = resource_log.resource.attributes.add(); item.key = 'service.name'; item.value.string_value = 'checkout'
    item = resource_log.resource.attributes.add(); item.key = 'logiq.tenant_id'; item.value.string_value = 'tenant-a'
    record = resource_log.scope_logs.add().log_records.add()
    record.body.string_value = 'protobuf event'
    record.severity_number = 17
    record.trace_id = bytes.fromhex('0123456789abcdef0123456789abcdef')
    record.span_id = bytes.fromhex('0123456789abcdef')
    result = decode_otlp_protobuf(request.SerializeToString())[0]
    assert result['message'] == 'protobuf event'
    assert result['severity'] == 'ERROR'
    assert result['trace_id'] == '0123456789abcdef0123456789abcdef'
    assert result['span_id'] == '0123456789abcdef'
