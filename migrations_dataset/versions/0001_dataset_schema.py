"""Dataset service-owned persistence schema."""
from alembic import op

revision = 'dataset_0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE datasets (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        name TEXT NOT NULL,
        source_type TEXT NOT NULL,
        status TEXT NOT NULL,
        line_count BIGINT NOT NULL DEFAULT 0 CHECK (line_count >= 0),
        processed_count BIGINT NOT NULL DEFAULT 0 CHECK (processed_count >= 0),
        failed_count BIGINT NOT NULL DEFAULT 0 CHECK (failed_count >= 0),
        processing_attempt INTEGER NOT NULL DEFAULT 1 CHECK (processing_attempt >= 1),
        object_key TEXT,
        byte_size BIGINT,
        sha256 TEXT,
        content_type TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        started_at TIMESTAMPTZ,
        completed_at TIMESTAMPTZ,
        error_message TEXT
    )
    """)
    op.execute("CREATE INDEX ix_datasets_tenant_created ON datasets(tenant_id, created_at DESC)")
    op.execute("CREATE INDEX ix_datasets_tenant_status ON datasets(tenant_id, status, created_at DESC)")
    op.execute("""
    CREATE TABLE dataset_progress_events (
        event_id TEXT PRIMARY KEY,
        dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
        tenant_id TEXT NOT NULL,
        outcome TEXT NOT NULL CHECK (outcome IN ('processed','failed')),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX ix_dataset_progress_dataset ON dataset_progress_events(dataset_id, created_at)")


def downgrade():
    op.execute('DROP TABLE IF EXISTS dataset_progress_events')
    op.execute('DROP TABLE IF EXISTS datasets')
