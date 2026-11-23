"""Create initial LogIQ persistence schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-20
"""
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS tenants (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
    tenant_id TEXT NOT NULL REFERENCES tenants(id), role TEXT NOT NULL DEFAULT 'member',
    is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_users_tenant ON users(tenant_id);
CREATE TABLE IF NOT EXISTS applications (
    id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL REFERENCES tenants(id), name TEXT NOT NULL,
    environment TEXT NOT NULL DEFAULT 'development', created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id,name)
);
CREATE TABLE IF NOT EXISTS api_keys (
    id TEXT UNIQUE, key_hash TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, application_id TEXT,
    label TEXT NOT NULL, scopes JSONB NOT NULL DEFAULT '["ingest"]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(), expires_at TIMESTAMPTZ, revoked_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_api_keys_id ON api_keys(id);
CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL DEFAULT 'default', name TEXT, source_type TEXT,
    status TEXT, line_count INT DEFAULT 0, created_at TIMESTAMPTZ DEFAULT now(),
    object_key TEXT, byte_size BIGINT, sha256 TEXT, content_type TEXT,
    processed_count BIGINT NOT NULL DEFAULT 0, failed_count BIGINT NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ, error_message TEXT
);
CREATE INDEX IF NOT EXISTS ix_datasets_tenant_created ON datasets(tenant_id,created_at DESC);
CREATE TABLE IF NOT EXISTS log_events (
    event_id TEXT PRIMARY KEY, tenant_id TEXT, application_id TEXT, service_name TEXT,
    environment TEXT, timestamp TIMESTAMPTZ, received_at TIMESTAMPTZ, severity TEXT,
    message TEXT NOT NULL, raw_message TEXT, trace_id TEXT, span_id TEXT, request_id TEXT,
    correlation_id TEXT, template_id TEXT, template TEXT, parameters JSONB DEFAULT '{}'::jsonb,
    attributes JSONB DEFAULT '{}'::jsonb, source_type TEXT, dataset_id TEXT
);
CREATE INDEX IF NOT EXISTS ix_log_events_time ON log_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_log_events_service ON log_events(service_name,severity);
CREATE INDEX IF NOT EXISTS ix_log_events_tenant_time ON log_events(tenant_id,timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_log_events_tenant_service_time ON log_events(tenant_id,service_name,timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_log_events_tenant_severity_time ON log_events(tenant_id,severity,timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_log_events_tenant_app_time ON log_events(tenant_id,application_id,timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_log_events_tenant_template_time ON log_events(tenant_id,template_id,timestamp DESC);
CREATE TABLE IF NOT EXISTS anomalies (
    id BIGSERIAL PRIMARY KEY, tenant_id TEXT NOT NULL DEFAULT 'default', kind TEXT,
    severity TEXT, service_name TEXT, description TEXT, created_at TIMESTAMPTZ DEFAULT now(),
    sample JSONB DEFAULT '{}'::jsonb, dedupe_key TEXT UNIQUE
);
ALTER TABLE anomalies ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'default';
ALTER TABLE anomalies ADD COLUMN IF NOT EXISTS dedupe_key TEXT;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS id TEXT;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS application_id TEXT;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS scopes JSONB NOT NULL DEFAULT '["ingest"]'::jsonb;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ;
UPDATE api_keys SET id=md5(key_hash) WHERE id IS NULL;
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'default';
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS object_key TEXT;
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS byte_size BIGINT;
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS sha256 TEXT;
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS content_type TEXT;
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS processed_count BIGINT NOT NULL DEFAULT 0;
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS failed_count BIGINT NOT NULL DEFAULT 0;
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
ALTER TABLE datasets ADD COLUMN IF NOT EXISTS error_message TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS ux_anomalies_dedupe_key ON anomalies(dedupe_key) WHERE dedupe_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_anomalies_tenant_created ON anomalies(tenant_id,created_at DESC);
CREATE TABLE IF NOT EXISTS template_registry (
    tenant_id TEXT NOT NULL, application_id TEXT NOT NULL, service_name TEXT NOT NULL,
    template_id TEXT NOT NULL, template TEXT NOT NULL, frequency BIGINT NOT NULL DEFAULT 0,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT now(), last_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY(tenant_id,application_id,service_name,template_id)
);
CREATE INDEX IF NOT EXISTS ix_template_registry_frequency ON template_registry(frequency DESC);
CREATE INDEX IF NOT EXISTS ix_template_registry_last_seen ON template_registry(last_seen DESC);
"""


def upgrade():
    # Idempotent DDL also permits adoption of development databases created by
    # the earlier runtime ensure_tables() bootstrap.
    for statement in UPGRADE_SQL.split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade():
    op.execute("DROP TABLE IF EXISTS template_registry CASCADE")
    op.execute("DROP TABLE IF EXISTS anomalies CASCADE")
    op.execute("DROP TABLE IF EXISTS log_events CASCADE")
    op.execute("DROP TABLE IF EXISTS datasets CASCADE")
    op.execute("DROP TABLE IF EXISTS api_keys CASCADE")
    op.execute("DROP TABLE IF EXISTS applications CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
    op.execute("DROP TABLE IF EXISTS tenants CASCADE")
