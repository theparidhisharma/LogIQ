"""Store upstream source metadata for imported public datasets."""
from alembic import op
revision = 'dataset_0004'
down_revision = 'dataset_0003'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("ALTER TABLE datasets ADD COLUMN IF NOT EXISTS source_reference TEXT")
    op.execute("ALTER TABLE datasets ADD COLUMN IF NOT EXISTS source_metadata JSONB NOT NULL DEFAULT '{}'::jsonb")

def downgrade():
    op.execute("ALTER TABLE datasets DROP COLUMN IF EXISTS source_metadata")
    op.execute("ALTER TABLE datasets DROP COLUMN IF EXISTS source_reference")
