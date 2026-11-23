"""Add durable, retryable raw-artifact deletion tombstones."""
from alembic import op

revision = "dataset_0007"
down_revision = "dataset_0006"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE datasets ADD COLUMN IF NOT EXISTS deletion_requested_at TIMESTAMPTZ")
    op.execute("ALTER TABLE datasets ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ")
    op.execute("ALTER TABLE datasets ADD COLUMN IF NOT EXISTS deletion_attempts INTEGER NOT NULL DEFAULT 0 CHECK (deletion_attempts >= 0)")
    op.execute("ALTER TABLE datasets ADD COLUMN IF NOT EXISTS deletion_error TEXT")
    op.execute("CREATE INDEX IF NOT EXISTS ix_datasets_deletion_queue ON datasets(deletion_requested_at, created_at) WHERE deletion_requested_at IS NOT NULL AND deleted_at IS NULL")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_datasets_deletion_queue")
    for column in ("deletion_error", "deletion_attempts", "deleted_at", "deletion_requested_at"):
        op.execute(f"ALTER TABLE datasets DROP COLUMN IF EXISTS {column}")
