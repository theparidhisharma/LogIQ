import pytest


def test_deletion_worker_retries_idempotently_after_object_delete_before_commit(monkeypatch):
    from services.dataset import deletion_worker as worker
    calls = {"delete": 0, "commit": 0}

    class Result:
        def mappings(self): return self
        def first(self): return {"id": "d-1", "tenant_id": "t-1", "object_key": "tenants/t/datasets/d-1/raw"}

    class Conn:
        def execute(self, statement, params=None):
            sql = str(statement)
            if "SELECT id,object_key" in sql:
                return Result()
            return Result()

    class Tx:
        def __enter__(self): return Conn()
        def __exit__(self, exc_type, exc, tb):
            calls["commit"] += 1
            if calls["commit"] == 1:
                raise RuntimeError("simulated database commit failure")
            return False

    class DB:
        def begin(self): return Tx()

    monkeypatch.setattr(worker, "dataset_db", lambda: DB())
    def remove(key):
        assert key == "tenants/t/datasets/d-1/raw"
        calls["delete"] += 1
    monkeypatch.setattr(worker, "delete_raw_dataset", remove)

    with pytest.raises(RuntimeError, match="commit failure"):
        worker.process_one_deletion()
    assert worker.process_one_deletion() is True
    assert calls == {"delete": 2, "commit": 2}


def test_deletion_failure_is_recorded_and_retried(monkeypatch):
    from services.dataset import deletion_worker as worker
    executed = []
    class Result:
        def mappings(self): return self
        def first(self): return {"id": "d-2", "tenant_id": "t-2", "object_key": "raw/key"}
    class Conn:
        def execute(self, statement, params=None):
            executed.append((str(statement), params))
            return Result()
    class Tx:
        def __enter__(self): return Conn()
        def __exit__(self, *args): return False
    class DB:
        def begin(self): return Tx()
    monkeypatch.setattr(worker, "dataset_db", lambda: DB())
    monkeypatch.setattr(worker, "delete_raw_dataset", lambda key: (_ for _ in ()).throw(OSError("minio down")))
    assert worker.process_one_deletion() is False
    assert any("deletion_attempts=deletion_attempts+1" in sql for sql, _ in executed)
    assert not any("deleted_at=now()" in sql for sql, _ in executed)


def test_dataset_deletion_endpoint_and_worker_are_registered():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    api = (root / "services/dataset/main.py").read_text()
    worker = (root / "services/dataset/deletion_worker.py").read_text()
    compose = (root / "docker-compose.yml").read_text()
    assert "@app.delete('/v1/datasets/{dataset_id}')" in api
    assert "deletion_requested_at=now()" in api
    assert "FOR UPDATE SKIP LOCKED" in worker
    assert "dataset-deletion-worker" in compose


def test_deletion_migration_adds_tombstone_queue_and_retry_state():
    from pathlib import Path
    migration = (Path(__file__).resolve().parents[1] / "migrations_dataset/versions/0007_dataset_artifact_deletion.py").read_text()
    assert 'revision = "dataset_0007"' in migration
    assert 'down_revision = "dataset_0006"' in migration
    assert "deletion_requested_at" in migration
    assert "deletion_attempts" in migration
    assert "ix_datasets_deletion_queue" in migration


def test_publisher_and_progress_consumer_skip_deleting_datasets():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    publisher = (root / "services/dataset/publisher_worker.py").read_text()
    progress = (root / "services/dataset/progress_worker.py").read_text()
    assert "d.deletion_requested_at IS NULL" in publisher
    assert "deletion_requested_at IS NULL FOR UPDATE" in progress
