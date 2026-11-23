import logging
from shared.parsing import parse_line

logging.basicConfig(level=logging.INFO)

def transform(event):
    raw = event.get("raw_message") or event.get("message")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("log event requires a non-empty message")
    timestamp, severity, clean = parse_line(raw)
    result = dict(event)
    result["raw_message"] = raw
    result["message"] = clean
    result["severity"] = str(result.get("severity") or severity).upper()
    result["timestamp"] = result.get("timestamp") or timestamp
    result["preprocessed_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    result["processing_stage"] = "preprocessed"
    return result

if __name__ == "__main__":
    from shared.worker import run_stage
    run_stage(input_topic="logs.raw", output_topic="logs.preprocessed", group_id="logiq-preprocessor-v1", transform=transform)
