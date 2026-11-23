import pytest
from services.intelligence.deletion_worker import validate_command
from services.dataset.deletion_ack_worker import apply_ack


def test_deletion_command_requires_versioned_identity():
    valid = {"event_type": "dataset.deletion_requested", "schema_version": 1,
             "event_id": "dataset-deletion:d1", "dataset_id": "d1", "tenant_id": "t1"}
    assert validate_command(valid) == valid
    for key in ("event_id", "dataset_id", "tenant_id"):
        invalid = dict(valid); invalid.pop(key)
        with pytest.raises(ValueError):
            validate_command(invalid)
    invalid = dict(valid, schema_version=2)
    with pytest.raises(ValueError):
        validate_command(invalid)


def test_ack_requires_intelligence_and_versioned_contract():
    class Result:
        def scalar_one_or_none(self): return "d1"
    class Connection:
        def execute(self, *args, **kwargs): return Result()
    class Begin:
        def __enter__(self): return Connection()
        def __exit__(self, *args): pass
    class Engine:
        def begin(self): return Begin()
    ack = {"event_type": "dataset.deletion_acknowledged", "schema_version": 1,
           "event_id": "ack:d1", "dataset_id": "d1", "tenant_id": "t1", "service": "intelligence"}
    assert apply_ack(ack, engine=Engine()) is True
    with pytest.raises(ValueError):
        apply_ack(dict(ack, service="analytics"), engine=Engine())


def test_existing_deletion_receipt_cannot_be_replayed_across_tenants():
    from services.intelligence.deletion_worker import apply_deletion

    class Result:
        def mappings(self): return self
        def first(self): return {"tenant_id": "tenant-a", "event_id": "event-a"}
    class Connection:
        def execute(self, *args, **kwargs): return Result()
    class Begin:
        def __enter__(self): return Connection()
        def __exit__(self, *args): pass
    class Engine:
        def begin(self): return Begin()
    payload = {"event_type": "dataset.deletion_requested", "schema_version": 1,
               "event_id": "event-b", "dataset_id": "dataset-1", "tenant_id": "tenant-b"}
    with pytest.raises(ValueError, match="tenant mismatch"):
        apply_deletion(payload, engine=Engine())
