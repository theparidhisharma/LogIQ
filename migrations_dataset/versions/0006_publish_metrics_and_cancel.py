"""Persist publisher throughput counters and cooperative cancellation state."""
from alembic import op

revision = "dataset_0006"
down_revision = "dataset_0005"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE dataset_publish_jobs ADD COLUMN IF NOT EXISTS cancel_requested BOOLEAN NOT NULL DEFAULT FALSE")
    op.execute("ALTER TABLE dataset_publish_jobs ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ")
    op.execute("ALTER TABLE dataset_publish_jobs ADD COLUMN IF NOT EXISTS last_batch_at TIMESTAMPTZ")
    op.execute("ALTER TABLE dataset_publish_jobs ADD COLUMN IF NOT EXISTS total_publish_ms BIGINT NOT NULL DEFAULT 0 CHECK (total_publish_ms >= 0)")
    op.execute("ALTER TABLE dataset_publish_jobs ADD COLUMN IF NOT EXISTS published_bytes BIGINT NOT NULL DEFAULT 0 CHECK (published_bytes >= 0)")
    op.execute("ALTER TABLE dataset_publish_jobs ADD COLUMN IF NOT EXISTS last_batch_ms BIGINT NOT NULL DEFAULT 0 CHECK (last_batch_ms >= 0)")
    op.execute("ALTER TABLE dataset_publish_jobs DROP CONSTRAINT IF EXISTS dataset_publish_jobs_status_check")
    op.execute("ALTER TABLE dataset_publish_jobs ADD CONSTRAINT dataset_publish_jobs_status_check CHECK (status IN ('queued','publishing','published','failed','cancelled'))")


def downgrade():
    op.execute("ALTER TABLE dataset_publish_jobs DROP CONSTRAINT IF EXISTS dataset_publish_jobs_status_check")
    op.execute("ALTER TABLE dataset_publish_jobs ADD CONSTRAINT dataset_publish_jobs_status_check CHECK (status IN ('queued','publishing','published','failed'))")
    for column in ('last_batch_ms', 'published_bytes', 'total_publish_ms', 'last_batch_at', 'started_at', 'cancel_requested'):
        op.execute(f"ALTER TABLE dataset_publish_jobs DROP COLUMN IF EXISTS {column}")
