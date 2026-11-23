"""Indexes for tenant-scoped analytics and stable cursor pagination.

Revision ID: 0004_analytics_query_indexes
Revises: 0003_anomaly_lifecycle
"""
from alembic import op

revision = "0004_analytics_query_indexes"
down_revision = "0003_anomaly_lifecycle"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE INDEX IF NOT EXISTS ix_log_events_tenant_cursor ON log_events(tenant_id,timestamp DESC,event_id DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_log_events_tenant_service_cursor ON log_events(tenant_id,service_name,timestamp DESC,event_id DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_log_events_tenant_app_cursor ON log_events(tenant_id,application_id,timestamp DESC,event_id DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_log_events_tenant_template_cursor ON log_events(tenant_id,template_id,timestamp DESC,event_id DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_log_events_tenant_trace ON log_events(tenant_id,trace_id) WHERE trace_id IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_log_events_tenant_request ON log_events(tenant_id,request_id) WHERE request_id IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_log_events_tenant_dataset ON log_events(tenant_id,dataset_id,timestamp DESC) WHERE dataset_id IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_template_registry_tenant_frequency ON template_registry(tenant_id,frequency DESC,last_seen DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_template_registry_tenant_service ON template_registry(tenant_id,service_name,application_id)")


def downgrade():
    for name in (
        "ix_template_registry_tenant_service",
        "ix_template_registry_tenant_frequency",
        "ix_log_events_tenant_dataset",
        "ix_log_events_tenant_request",
        "ix_log_events_tenant_trace",
        "ix_log_events_tenant_template_cursor",
        "ix_log_events_tenant_app_cursor",
        "ix_log_events_tenant_service_cursor",
        "ix_log_events_tenant_cursor",
    ):
        op.execute(f"DROP INDEX IF EXISTS {name}")
