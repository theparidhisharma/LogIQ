from types import SimpleNamespace

import pytest
from sqlalchemy import text

from services.parser import worker
from services.parser.engine import BaselineParser


class FakeConnection:
    def __init__(self, row):
        self.row = row
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def execute(self, statement, params):
        return SimpleNamespace(mappings=lambda: SimpleNamespace(first=lambda: self.row))


class FakeEngine:
    def __init__(self, row):
        self.row = row
    def connect(self):
        return FakeConnection(self.row)


def test_live_events_use_baseline_without_dataset(monkeypatch):
    event = {"message": "GET /health status=200"}
    result = worker.transform(event)
    assert result["parser"] == BaselineParser.name
    assert result["processing_stage"] == "parsed"


def test_dataset_event_uses_persisted_parser_selection(monkeypatch):
    worker._PARSER_CACHE.clear()
    worker._SELECTION_CACHE.clear()
    monkeypatch.setattr(worker, "dataset_db", lambda: FakeEngine({
        "selected_parser": BaselineParser.name,
        "selected_parser_version": BaselineParser.version,
        "processing_attempt": 1,
    }))
    result = worker.transform({"message": "request id=123 failed", "dataset_id": "ds-1", "processing_attempt": 1})
    assert result["parser"] == BaselineParser.name
    assert result["parser_version"] == BaselineParser.version

def test_dataset_event_rejects_missing_benchmark_selection(monkeypatch):
    worker._PARSER_CACHE.clear()
    worker._SELECTION_CACHE.clear()
    monkeypatch.setattr(worker, "dataset_db", lambda: FakeEngine(None))
    with pytest.raises(RuntimeError, match="No benchmark-selected parser"):
        worker.transform({"message": "hello", "dataset_id": "ds-missing", "processing_attempt": 1})


def test_dataset_event_rejects_stale_processing_attempt(monkeypatch):
    worker._PARSER_CACHE.clear()
    worker._SELECTION_CACHE.clear()
    monkeypatch.setattr(worker, "dataset_db", lambda: FakeEngine({
        "selected_parser": BaselineParser.name,
        "selected_parser_version": BaselineParser.version,
        "processing_attempt": 2,
    }))
    with pytest.raises(RuntimeError, match="stale processing attempt"):
        worker.transform({"message": "hello", "dataset_id": "ds-stale", "processing_attempt": 1})
