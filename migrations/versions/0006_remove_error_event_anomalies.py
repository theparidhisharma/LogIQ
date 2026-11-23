"""Remove per-event error anomalies; error volume is detected per time bucket instead.

Revision ID: 0006_remove_error_event_anomalies
Revises: 0005_dataset_deletion_receipts
"""
from alembic import op

revision = "0006_remove_error_events"
down_revision = "0005_dataset_deletion_receipts"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DELETE FROM anomalies WHERE kind='error_event'")


def downgrade():
    pass
