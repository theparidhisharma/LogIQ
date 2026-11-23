"""Durable, restartable publication jobs for uploaded datasets."""
from alembic import op

revision = "dataset_0002"
down_revision = "dataset_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE dataset_publish_jobs (
        dataset_id TEXT PRIMARY KEY REFERENCES datasets(id) ON DELETE CASCADE,
        tenant_id TEXT NOT NULL,
        processing_attempt INTEGER NOT NULL DEFAULT 1,
        next_line_number BIGINT NOT NULL DEFAULT 1 CHECK (next_line_number >= 1),
        status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','publishing','published','failed')),
        publish_attempts INTEGER NOT NULL DEFAULT 0,
        next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        last_error TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX ix_dataset_publish_jobs_ready ON dataset_publish_jobs(status,next_attempt_at,created_at)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS dataset_publish_jobs")
