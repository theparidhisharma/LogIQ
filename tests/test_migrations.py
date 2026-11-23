from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

def test_initial_migration_covers_persisted_service_entities():
    migration = (ROOT / "migrations/versions/0001_initial_schema.py").read_text()
    for table in ("tenants", "users", "applications", "api_keys", "datasets",
                  "log_events", "anomalies", "template_registry"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in migration
    assert "ADD COLUMN IF NOT EXISTS tenant_id" in migration
    assert "CREATE INDEX IF NOT EXISTS ix_log_events_tenant_time" in migration

def test_compose_runs_migrations_before_application_services():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    services = compose["services"]
    assert services["migrate"]["command"] == ["alembic", "upgrade", "head"]
    assert services["migrate"]["depends_on"]["postgres"]["condition"] == "service_healthy"
    for name in ("collection", "preprocessing", "parser", "intelligence",
                 "preprocessing-worker", "parser-worker", "intelligence-worker", "analytics"):
        assert services[name]["depends_on"]["migrate"]["condition"] == "service_completed_successfully"
    assert services["dataset"]["depends_on"]["migrate-dataset"]["condition"] == "service_completed_successfully"
    for name in ("collection", "dataset", "analytics", "identity"):
        assert services[name]["depends_on"]["migrate-identity"]["condition"] == "service_completed_successfully"

def test_services_do_not_run_schema_creation_on_startup():
    for path in (ROOT / "services").rglob("*.py"):
        source = path.read_text()
        assert "ensure_tables()" not in source, f"runtime DDL remains in {path}"


def test_dataset_service_migration_has_its_own_alembic_script_location():
    config = (ROOT / "alembic_dataset.ini").read_text()
    env = (ROOT / "migrations_dataset/env.py").read_text()
    assert "script_location = migrations_dataset" in config
    assert "DATASET_DATABASE_URL" in env


def test_dataset_publish_job_migration_and_worker_are_registered():
    migration = (ROOT / "migrations_dataset/versions/0002_dataset_publish_jobs.py").read_text()
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    assert "CREATE TABLE dataset_publish_jobs" in migration
    assert "next_line_number" in migration and "processing_attempt" in migration
    assert "dataset-publisher-worker" in compose["services"]
    assert compose["services"]["dataset-publisher-worker"]["depends_on"]["migrate-dataset"]["condition"] == "service_completed_successfully"


def test_dataset_increment_22_migration_adds_durable_metrics_and_cancellation():
    migration = (ROOT / "migrations_dataset/versions/0006_publish_metrics_and_cancel.py").read_text()
    assert "cancel_requested BOOLEAN" in migration
    assert "published_bytes BIGINT" in migration
    assert "total_publish_ms BIGINT" in migration
    assert "'cancelled'" in migration


def test_dataset_publisher_checks_cancellation_and_persists_acknowledged_batch_metrics():
    worker = (ROOT / "services/dataset/publisher_worker.py").read_text()
    assert "if job[\"cancel_requested\"]" in worker
    assert "if current['cancel_requested']" in worker
    assert "publish_events_acknowledged(p, records" in worker
    assert "published_bytes=published_bytes+:bytes" in worker
    assert "total_publish_ms=total_publish_ms+:elapsed" in worker


def test_dataset_cancellation_locks_only_the_job_row_to_avoid_lock_order_inversion():
    source = (ROOT / "services/dataset/main.py").read_text()
    cancel_source = source.split("def cancel_dataset", 1)[1].split("@app.post('/v1/datasets/synthetic')", 1)[0]
    assert "FOR UPDATE OF j" in cancel_source
    assert "FOR UPDATE OF d,j" not in cancel_source
