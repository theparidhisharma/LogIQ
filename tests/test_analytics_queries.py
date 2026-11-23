from contextlib import contextmanager
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from services.analytics import main as analytics


class FakeResult:
    def __init__(self, rows=None, scalar=0):
        self._rows = rows or []
        self._scalar = scalar

    def scalar(self):
        return self._scalar

    def mappings(self):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class FakeConnection:
    def __init__(self):
        self.calls = []

    def execute(self, query, params=None):
        self.calls.append((str(query), params or {}))
        return FakeResult([{
            "event_id": "evt-2",
            "timestamp": datetime(2026, 11, 20, tzinfo=timezone.utc),
            "message": "sample",
        }])


class FakeEngine:
    def __init__(self):
        self.connection = FakeConnection()

    @contextmanager
    def connect(self):
        yield self.connection


def test_time_filters_normalize_naive_datetimes():
    clauses, params = analytics._time_filters(datetime(2026, 1, 1), None)
    assert clauses == ["timestamp >= :start_time"]
    assert params["start_time"].tzinfo == timezone.utc


def test_time_filters_reject_reversed_range():
    with pytest.raises(HTTPException) as exc:
        analytics._time_filters(datetime(2026, 2, 1), datetime(2026, 1, 1))
    assert exc.value.status_code == 422


def test_log_search_uses_tenant_scope_and_stable_cursor(monkeypatch):
    engine = FakeEngine()
    monkeypatch.setattr(analytics, "db", lambda: engine)
    result = analytics.logs(
        service="api", severity="error", q="timeout", application_id="app-a",
        environment="prod", template_id="tpl-a", trace_id="trace-a",
        request_id="req-a", source_type="otlp", dataset_id="ds-a",
        start_time=None, end_time=None, limit=25, offset=0,
        before_timestamp=datetime(2026, 11, 20, tzinfo=timezone.utc),
        before_event_id="evt-3", include_total=True, user={"tenant_id": "tenant-a"},
    )
    sql, params = engine.connection.calls[0]
    assert "tenant_id=:tenant" in sql
    assert "(timestamp,event_id) < (:before_timestamp,:before_event_id)" in sql
    assert params["tenant"] == "tenant-a"
    assert params["severity"] == "ERROR"
    assert params["trace_id"] == "trace-a"
    assert params["dataset_id"] == "ds-a"
    assert result["pagination"] == "cursor"
    assert result["items"][0]["event_id"] == "evt-2"


def test_log_search_requires_both_cursor_fields(monkeypatch):
    engine = FakeEngine()
    monkeypatch.setattr(analytics, "db", lambda: engine)
    with pytest.raises(HTTPException) as exc:
        analytics.logs(
            service=None, severity=None, q=None, application_id=None, environment=None,
            template_id=None, trace_id=None, request_id=None, source_type=None, dataset_id=None,
            start_time=None, end_time=None, limit=25, offset=0,
            before_timestamp=datetime(2026, 11, 20, tzinfo=timezone.utc),
            before_event_id=None, include_total=False, user={"tenant_id": "tenant-a"},
        )
    assert exc.value.status_code == 422
    assert not engine.connection.calls


def test_template_trend_is_event_activity_not_lifetime_frequency():
    source = (analytics.__file__)
    import pathlib
    text = pathlib.Path(source).read_text()
    assert "count(*) AS event_count" in text
    assert "templates_discovered" in text
    assert "sum(frequency) AS cumulative_event_frequency" not in text


def test_offset_mode_retains_offset_compatibility(monkeypatch):
    engine = FakeEngine()
    monkeypatch.setattr(analytics, "db", lambda: engine)
    result = analytics.logs(
        service=None, severity=None, q=None, application_id=None, environment=None,
        template_id=None, trace_id=None, request_id=None, source_type=None, dataset_id=None,
        start_time=None, end_time=None, limit=10, offset=20,
        before_timestamp=None, before_event_id=None, include_total=True,
        user={"tenant_id": "tenant-b"},
    )
    assert len(engine.connection.calls) == 2
    query, params = engine.connection.calls[1]
    assert "OFFSET :offset" in query
    assert params["offset"] == 20
    assert result["pagination"] == "offset"
    assert result["total"] == 0


def test_gateway_routes_log_detail_to_analytics():
    import pathlib
    source = pathlib.Path(analytics.__file__).parents[1] / "gateway" / "main.py"
    assert "elif route.startswith('/v1/logs/')" in source.read_text()
