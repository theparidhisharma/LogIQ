"""Add anomaly lifecycle and recurrence metadata.

Revision ID: 0003_anomaly_lifecycle
Revises: 0002_remove_shared_datasets
"""
from alembic import op

revision = "0003_anomaly_lifecycle"
down_revision = "0002_remove_shared_datasets"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE anomalies ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'open'")
    op.execute("ALTER TABLE anomalies ADD COLUMN IF NOT EXISTS first_seen TIMESTAMPTZ NOT NULL DEFAULT now()")
    op.execute("ALTER TABLE anomalies ADD COLUMN IF NOT EXISTS last_seen TIMESTAMPTZ NOT NULL DEFAULT now()")
    op.execute("ALTER TABLE anomalies ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ")
    op.execute("ALTER TABLE anomalies ADD COLUMN IF NOT EXISTS occurrence_count BIGINT NOT NULL DEFAULT 1")
    op.execute("ALTER TABLE anomalies ADD COLUMN IF NOT EXISTS rule_version TEXT NOT NULL DEFAULT '1'")
    op.execute("CREATE INDEX IF NOT EXISTS ix_anomalies_tenant_status_last_seen ON anomalies(tenant_id,status,last_seen DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_anomalies_kind_last_seen ON anomalies(kind,last_seen DESC)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_anomalies_kind_last_seen")
    op.execute("DROP INDEX IF EXISTS ix_anomalies_tenant_status_last_seen")
    op.execute("ALTER TABLE anomalies DROP COLUMN IF EXISTS rule_version")
    op.execute("ALTER TABLE anomalies DROP COLUMN IF EXISTS occurrence_count")
    op.execute("ALTER TABLE anomalies DROP COLUMN IF EXISTS resolved_at")
    op.execute("ALTER TABLE anomalies DROP COLUMN IF EXISTS last_seen")
    op.execute("ALTER TABLE anomalies DROP COLUMN IF EXISTS first_seen")
    op.execute("ALTER TABLE anomalies DROP COLUMN IF EXISTS status")
