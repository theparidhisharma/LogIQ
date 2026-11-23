"""Move legacy shared dataset metadata out of the active core namespace.

The records are preserved as an archive; the Dataset service now owns the
active `datasets` table in its separate database.
"""
from alembic import op

revision = '0002_remove_shared_datasets'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    DO $$
    BEGIN
        IF to_regclass('public.datasets') IS NOT NULL
           AND to_regclass('public.datasets_legacy_archive') IS NULL THEN
            ALTER TABLE public.datasets RENAME TO datasets_legacy_archive;
        END IF;
    END
    $$;
    """)


def downgrade():
    op.execute("""
    DO $$
    BEGIN
        IF to_regclass('public.datasets_legacy_archive') IS NOT NULL
           AND to_regclass('public.datasets') IS NULL THEN
            ALTER TABLE public.datasets_legacy_archive RENAME TO datasets;
        END IF;
    END
    $$;
    """)
