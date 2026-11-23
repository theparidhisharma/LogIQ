"""Apply the parser selected for each uploaded dataset."""
import logging
from sqlalchemy import text

from shared.common import dataset_db
from .engine import BaselineParser, parser_by_name

logging.basicConfig(level=logging.INFO)
_PARSER_CACHE = {}
_SELECTION_CACHE = {}

def _selected_parser(event):
    dataset_id = event.get("dataset_id")
    if not dataset_id:
        return BaselineParser()
    attempt = int(event.get("processing_attempt", 1))
    cache_key = (dataset_id, attempt)
    if cache_key not in _SELECTION_CACHE:
        with dataset_db().connect() as conn:
            row = conn.execute(text("""SELECT selected_parser,selected_parser_version,processing_attempt
                FROM datasets WHERE id=:id"""), {"id": dataset_id}).mappings().first()
        if not row or not row["selected_parser"]:
            raise RuntimeError(f"No benchmark-selected parser is recorded for dataset {dataset_id}")
        if int(row["processing_attempt"]) != attempt:
            raise RuntimeError("Dataset event belongs to a stale processing attempt")
        _SELECTION_CACHE[cache_key] = (row["selected_parser"], row["selected_parser_version"])
    name, version = _SELECTION_CACHE[cache_key]
    parser_key = (dataset_id, attempt, name, version)
    if parser_key not in _PARSER_CACHE:
        parser = parser_by_name(name)
        if str(getattr(parser, "version", "unknown")) != str(version):
            raise RuntimeError(f"Selected parser version changed: expected {version}, got {parser.version}")
        _PARSER_CACHE[parser_key] = parser
    return _PARSER_CACHE[parser_key]

def transform(event):
    message = event.get("message", "")
    if not message:
        raise ValueError("preprocessed event has no message")
    parser = _selected_parser(event)
    tid, template, params = parser.parse(message)
    result = dict(event)
    result.update(template_id=tid, template=template, parameters=params,
                  parser=parser.name, parser_version=getattr(parser, "version", "unknown"),
                  processing_stage="parsed")
    return result

if __name__ == "__main__":
    from shared.worker import run_stage
    run_stage(input_topic="logs.preprocessed", output_topic="logs.parsed", group_id="logiq-parser-v1", transform=transform)
