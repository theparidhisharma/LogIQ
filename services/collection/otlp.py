"""OpenTelemetry Logs decoding helpers (OTLP/HTTP JSON and protobuf)."""
from datetime import datetime, timezone
import base64


def _any_value(value):
    if not isinstance(value, dict):
        return value
    for key in ("stringValue", "boolValue", "intValue", "doubleValue", "bytesValue", "arrayValue", "kvlistValue"):
        if key in value:
            inner = value[key]
            if key == "arrayValue":
                return [_any_value(item.get("value", item)) for item in inner.get("values", [])]
            if key == "kvlistValue":
                return {item.get("key"): _any_value(item.get("value", {})) for item in inner.get("values", [])}
            return inner
    return value


def _attributes(items):
    return {item.get("key"): _any_value(item.get("value", {})) for item in (items or []) if item.get("key")}


def _normalize_id(value):
    if not value:
        return None
    if isinstance(value, bytes):
        return value.hex()
    value = str(value)
    if len(value) in (16, 32):
        try:
            bytes.fromhex(value)
            return value.lower()
        except ValueError:
            pass
    try:
        return base64.b64decode(value, validate=True).hex()
    except Exception:
        return value


def _ns_iso(value):
    if not value:
        return None
    return datetime.fromtimestamp(int(value) / 1_000_000_000, timezone.utc).isoformat()


def _severity(number, text):
    if text:
        return str(text).upper()
    if isinstance(number, str):
        # Protobuf JSON renders enum values as names, e.g. SEVERITY_NUMBER_ERROR2.
        for label in ("FATAL", "ERROR", "WARN", "INFO", "DEBUG", "TRACE"):
            if label in number.upper():
                return label
        return "INFO"
    number = int(number or 0)
    if number >= 21: return "FATAL"
    if number >= 17: return "ERROR"
    if number >= 13: return "WARN"
    if number >= 9: return "INFO"
    if number >= 5: return "DEBUG"
    if number > 0: return "TRACE"
    return "INFO"


def decode_otlp_json(payload):
    """Flatten the standard OTLP ExportLogsServiceRequest JSON shape."""
    records = []
    for resource_log in payload.get("resourceLogs", []):
        resource = _attributes(resource_log.get("resource", {}).get("attributes"))
        for scope_log in resource_log.get("scopeLogs", resource_log.get("instrumentationLibraryLogs", [])):
            scope = scope_log.get("scope", scope_log.get("instrumentationLibrary", {})) or {}
            for record in scope_log.get("logRecords", []):
                body = _any_value(record.get("body", {}))
                attrs = {**resource, **_attributes(record.get("attributes"))}
                records.append({
                    "message": body if isinstance(body, str) else str(body),
                    "severity": _severity(record.get("severityNumber", 0), record.get("severityText")),
                    "timestamp": _ns_iso(record.get("timeUnixNano") or record.get("observedTimeUnixNano")),
                    "service_name": resource.get("service.name", "unknown"),
                    "environment": resource.get("deployment.environment.name", resource.get("deployment.environment", "development")),
                    "application_id": resource.get("logiq.application_id", "unknown"),
                    "tenant_id": resource.get("logiq.tenant_id"),
                    "trace_id": _normalize_id(record.get("traceId")), "span_id": _normalize_id(record.get("spanId")),
                    "attributes": {**attrs, "otel_scope_name": scope.get("name"), "otel_scope_version": scope.get("version")},
                    "source_type": "otlp", "source_name": "opentelemetry",
                })
    return records


def decode_otlp_protobuf(raw):
    """Decode OTLP protobuf using generated classes from opentelemetry-proto."""
    from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
    from google.protobuf.json_format import MessageToDict
    request = ExportLogsServiceRequest()
    request.ParseFromString(raw)
    # Preserve protobuf bytes/IDs as hex and map the canonical message to the JSON flattener.
    payload = MessageToDict(request, preserving_proto_field_name=False)
    for resource_log in payload.get("resourceLogs", []):
        for scope_log in resource_log.get("scopeLogs", []):
            for record in scope_log.get("logRecords", []):
                for field in ("traceId", "spanId"):
                    value = record.get(field)
                    if isinstance(value, str):
                        try: record[field] = base64.b64decode(value).hex()
                        except Exception:
                            try: record[field] = bytes.fromhex(value).hex()
                            except ValueError: pass
    return decode_otlp_json(payload)
