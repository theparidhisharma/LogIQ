"""Idempotency ledger for dataset deletion commands."""
from alembic import op
revision = "0005_dataset_deletion_receipts"
down_revision = "0004_analytics_query_indexes"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE TABLE IF NOT EXISTS dataset_deletion_receipts (dataset_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, event_id TEXT NOT NULL UNIQUE, deleted_events BIGINT NOT NULL DEFAULT 0, completed_at TIMESTAMPTZ NOT NULL DEFAULT now())")

def downgrade():
    op.execute("DROP TABLE IF EXISTS dataset_deletion_receipts")
