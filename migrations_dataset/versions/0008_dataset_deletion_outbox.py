"""Durable outbox for cross-service dataset erasure."""
from alembic import op
revision = "dataset_0008"
down_revision = "dataset_0007"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("ALTER TABLE datasets ADD COLUMN IF NOT EXISTS artifact_deleted_at TIMESTAMPTZ")
    op.execute("CREATE TABLE IF NOT EXISTS dataset_deletion_outbox (event_id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL, tenant_id TEXT NOT NULL, payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), published_at TIMESTAMPTZ, publish_attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_dataset_deletion_outbox_pending ON dataset_deletion_outbox(created_at) WHERE published_at IS NULL")

def downgrade():
    op.execute("DROP TABLE IF EXISTS dataset_deletion_outbox")
    op.execute("ALTER TABLE datasets DROP COLUMN IF EXISTS artifact_deleted_at")
