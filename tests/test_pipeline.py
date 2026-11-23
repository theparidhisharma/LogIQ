from services.preprocessing.worker import transform as preprocess
from services.parser.worker import transform as parse
from services.parser.engine import benchmark


def sample_event():
    return {
        "event_id": "evt-1", "application_id": "orders", "service_name": "checkout",
        "message": "2026-11-20T08:00:00Z ERROR request 123 failed after 42 ms",
        "raw_message": "2026-11-20T08:00:00Z ERROR request 123 failed after 42 ms",
        "severity": None,
    }


def test_preprocessing_preserves_raw_and_extracts_severity():
    original = sample_event()
    result = preprocess(original)
    assert result["raw_message"] == original["raw_message"]
    assert result["severity"] == "ERROR"
    assert result["message"] == "request 123 failed after 42 ms"
    assert result["processing_stage"] == "preprocessed"


def test_parser_adds_stable_template_and_parameters():
    result = parse(preprocess(sample_event()))
    assert result["template_id"]
    assert "<*>" in result["template"]
    assert result["parser"] == "baseline-token-mask-v1"
    assert result["processing_stage"] == "parsed"


def test_benchmark_is_reproducible_and_reports_limitations():
    lines = ["request 123 failed", "request 456 failed", "user 99 logged in"]
    result = benchmark(lines, seed=7)
    assert result["seed"] == 7
    assert result["sample_size"] == 3
    assert result["results"]
    assert result["selected_parser"]
    assert "No ground-truth" in result["quality_note"]
