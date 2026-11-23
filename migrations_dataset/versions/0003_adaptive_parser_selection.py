"""Persist adaptive parser decisions and reproducible benchmark reports."""
from alembic import op

revision = "dataset_0003"
down_revision = "dataset_0002"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE datasets ADD COLUMN parser_policy TEXT NOT NULL DEFAULT 'runtime_first'")
    op.execute("ALTER TABLE datasets ADD COLUMN selected_parser TEXT")
    op.execute("ALTER TABLE datasets ADD COLUMN selected_parser_version TEXT")
    op.execute("ALTER TABLE datasets ADD COLUMN parser_benchmark JSONB")
    op.execute("ALTER TABLE datasets ADD COLUMN parser_ground_truth JSONB")
    op.execute("ALTER TABLE datasets ADD COLUMN parser_selected_at TIMESTAMPTZ")
    op.execute("ALTER TABLE datasets ADD COLUMN parser_seed INTEGER NOT NULL DEFAULT 42")
    op.execute("ALTER TABLE datasets ADD COLUMN parser_sample_size INTEGER NOT NULL DEFAULT 10000")
    op.execute("ALTER TABLE datasets ADD COLUMN parser_min_quality DOUBLE PRECISION NOT NULL DEFAULT 0.90")
    op.execute("ALTER TABLE datasets ADD COLUMN parser_sampling_strategy TEXT NOT NULL DEFAULT 'random'")


def downgrade():
    op.execute("ALTER TABLE datasets DROP COLUMN IF EXISTS parser_sampling_strategy")
    op.execute("ALTER TABLE datasets DROP COLUMN IF EXISTS parser_min_quality")
    op.execute("ALTER TABLE datasets DROP COLUMN IF EXISTS parser_sample_size")
    op.execute("ALTER TABLE datasets DROP COLUMN IF EXISTS parser_seed")
    op.execute("ALTER TABLE datasets DROP COLUMN IF EXISTS parser_selected_at")
    op.execute("ALTER TABLE datasets DROP COLUMN IF EXISTS parser_ground_truth")
    op.execute("ALTER TABLE datasets DROP COLUMN IF EXISTS parser_benchmark")
    op.execute("ALTER TABLE datasets DROP COLUMN IF EXISTS selected_parser_version")
    op.execute("ALTER TABLE datasets DROP COLUMN IF EXISTS selected_parser")
    op.execute("ALTER TABLE datasets DROP COLUMN IF EXISTS parser_policy")
