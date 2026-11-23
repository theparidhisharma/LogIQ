from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

def test_compose_provisions_separate_identity_and_core_databases():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    services = compose["services"]
    assert "migrate" in services and "migrate-identity" in services
    assert "logiq_core" in services["migrate"]["environment"]["DATABASE_URL"]
    assert "logiq_identity" in services["migrate-identity"]["environment"]["DATABASE_URL"]
    assert "logiq_identity" in services["identity"]["environment"]["DATABASE_URL"]
    assert "logiq_core" in services["analytics"]["environment"]["DATABASE_URL"]

def test_identity_bootstrap_is_mounted_as_postgres_init_script():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    volumes = compose["services"]["postgres"]["volumes"]
    assert any("init-databases.sh:/docker-entrypoint-initdb.d/" in item for item in volumes)
    assert (ROOT / "infrastructure/postgres/init-databases.sh").exists()

def test_authentication_reads_identity_database():
    security = (ROOT / "shared/security.py").read_text()
    assert security.count("identity_db().connect()") == 2


def test_identity_migration_config_is_baked_into_service_image():
    dockerfile = (ROOT / "Dockerfile.service").read_text()
    assert "COPY alembic_identity.ini ./alembic_identity.ini" in dockerfile
    config = (ROOT / "alembic_identity.ini").read_text()
    assert "logiq_identity" in config


def test_dataset_service_has_its_own_database_and_migration_gate():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    services = compose["services"]
    dataset_url = services["dataset"]["environment"]["DATABASE_URL"]
    assert "logiq_dataset" in dataset_url
    assert services["dataset"]["depends_on"]["migrate-dataset"]["condition"] == "service_completed_successfully"
    assert services["migrate-dataset"]["command"] == ["alembic", "-c", "alembic_dataset.ini", "upgrade", "head"]
    assert "logiq_dataset" in services["dataset-progress-worker"]["environment"]["DATASET_DATABASE_URL"]


def test_dataset_database_bootstrap_provisions_a_separate_role_and_database():
    bootstrap = (ROOT / "infrastructure/postgres/init-databases.sh").read_text()
    assert "CREATE ROLE logiq_dataset" in bootstrap
    assert "CREATE DATABASE logiq_dataset OWNER logiq_dataset" in bootstrap


def test_dataset_service_uses_owned_database_and_never_reads_core_log_events():
    source = (ROOT / "services/dataset/main.py").read_text()
    assert "from shared.common import dataset_db as db" in source
    assert "FROM log_events" not in source
    assert "FROM datasets" in source
    assert "DELETE FROM dataset_progress_events" in source


def test_intelligence_publishes_progress_instead_of_updating_dataset_database():
    source = (ROOT / "services/intelligence/worker.py").read_text()
    assert 'persisted["event_type"] = "log_persisted"' in source
    assert "UPDATE datasets" not in source


def test_dataset_progress_consumer_is_idempotent_and_dataset_owned():
    source = (ROOT / "services/dataset/progress_worker.py").read_text()
    assert "from shared.common import dataset_db" in source
    assert "ON CONFLICT(event_id) DO NOTHING RETURNING event_id" in source
    assert "logiq-dataset-progress-v1" in source


def test_core_database_migration_removes_dataset_table_after_ownership_move():
    migration = ROOT / "migrations/versions/0002_remove_shared_datasets.py"
    assert "ALTER TABLE public.datasets RENAME TO datasets_legacy_archive" in migration.read_text()
    dataset_migration = (ROOT / "migrations_dataset/versions/0001_dataset_schema.py").read_text()
    assert "CREATE TABLE datasets" in dataset_migration
    assert "CREATE TABLE dataset_progress_events" in dataset_migration


def _stub_kafka_import(monkeypatch):
    import sys
    from types import SimpleNamespace
    monkeypatch.setitem(sys.modules, 'kafka', SimpleNamespace(KafkaProducer=object, KafkaConsumer=object))


def test_dataset_progress_consumer_ignores_notifications_from_old_attempt(monkeypatch):
    _stub_kafka_import(monkeypatch)
    from services.dataset import progress_worker

    class Result:
        def scalar_one_or_none(self):
            return 3

    class Connection:
        statements = []
        def execute(self, statement, params=None):
            self.statements.append(str(statement))
            return Result()

    class Transaction:
        def __init__(self, connection): self.connection = connection
        def __enter__(self): return self.connection
        def __exit__(self, *args): return False

    connection = Connection()
    class Engine:
        def begin(self): return Transaction(connection)

    monkeypatch.setattr(progress_worker, 'dataset_db', lambda: Engine())
    result = progress_worker.transform({
        'event_type': 'log_persisted', 'dataset_id': 'd1', 'tenant_id': 't1',
        'event_id': 'e1', 'processing_attempt': 2,
    })
    assert result is None
    assert len(connection.statements) == 1  # no progress mutation for stale attempt


def test_dataset_progress_consumer_updates_only_once_per_event(monkeypatch):
    _stub_kafka_import(monkeypatch)
    from services.dataset import progress_worker

    class Result:
        def __init__(self, value): self.value = value
        def scalar_one_or_none(self): return self.value

    class Connection:
        def __init__(self): self.calls = 0
        def execute(self, statement, params=None):
            self.calls += 1
            if self.calls == 1: return Result(1)  # current attempt
            if self.calls == 2: return Result(None)  # duplicate progress event
            return Result(None)

    class Transaction:
        def __init__(self, connection): self.connection = connection
        def __enter__(self): return self.connection
        def __exit__(self, *args): return False

    connection = Connection()
    class Engine:
        def begin(self): return Transaction(connection)

    monkeypatch.setattr(progress_worker, 'dataset_db', lambda: Engine())
    progress_worker.transform({
        'event_type': 'log_persisted', 'dataset_id': 'd1', 'tenant_id': 't1',
        'event_id': 'e1', 'processing_attempt': 1,
    })
    assert connection.calls == 2  # insert dedupe row; no counter update


def test_intelligence_emits_persisted_notification_even_on_duplicate_log(monkeypatch):
    _stub_kafka_import(monkeypatch)
    from services.intelligence import worker

    class Result:
        def scalar_one_or_none(self): return None

    class Connection:
        def execute(self, statement, params=None): return Result()

    class Transaction:
        def __enter__(self): return Connection()
        def __exit__(self, *args): return False

    class Engine:
        def begin(self): return Transaction()

    monkeypatch.setattr(worker, 'db', lambda: Engine())
    source = {'event_id': 'evt-1', 'message': 'duplicate but already persisted',
              'tenant_id': 'tenant-1', 'dataset_id': 'dataset-1', 'processing_attempt': 2}
    result = worker.transform(source)
    assert result['event_type'] == 'log_persisted'
    assert result['processing_attempt'] == 2
    assert result['event_id'] == 'evt-1'
