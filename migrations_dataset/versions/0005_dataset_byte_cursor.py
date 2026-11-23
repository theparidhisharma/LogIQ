"""Persist byte offsets for efficient streaming dataset publication."""
from alembic import op

revision = "dataset_0005"
down_revision = "dataset_0004"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE dataset_publish_jobs ADD COLUMN IF NOT EXISTS next_byte_offset BIGINT NOT NULL DEFAULT 0")


def downgrade():
    op.execute("ALTER TABLE dataset_publish_jobs DROP COLUMN IF EXISTS next_byte_offset")
