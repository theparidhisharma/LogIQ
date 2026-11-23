"""Consume persisted-log notifications and maintain Dataset-owned job progress.

The Dataset service owns this database. Intelligence never updates dataset rows
or connects to this database directly; it publishes versioned Kafka events.
"""
import logging
from sqlalchemy import text
from shared.common import dataset_db
from shared.worker import run_stage

log = logging.getLogger('logiq.dataset.progress')


def transform(message: dict):
    event_type = message.get('event_type')
    dataset_id = message.get('dataset_id')
    tenant_id = message.get('tenant_id')
    event_id = message.get('event_id')
    attempt = message.get('processing_attempt', 1)
    if event_type not in {'log_persisted', 'dataset_processing_failed'}:
        return None
    if not dataset_id or not tenant_id or not event_id or not isinstance(attempt, int) or attempt < 1:
        raise ValueError('dataset progress event requires dataset_id, tenant_id and event_id')

    outcome = 'failed' if event_type == 'dataset_processing_failed' else 'processed'
    with dataset_db().begin() as conn:
        current_attempt = conn.execute(text("SELECT processing_attempt FROM datasets WHERE id=:dataset_id AND tenant_id=:tenant_id AND deletion_requested_at IS NULL FOR UPDATE"),
            {'dataset_id': dataset_id, 'tenant_id': tenant_id}).scalar_one_or_none()
        if current_attempt is None or int(current_attempt) != attempt:
            return None  # stale notification from a prior retry attempt
        recorded = conn.execute(text("""INSERT INTO dataset_progress_events
            (event_id,dataset_id,tenant_id,outcome)
            VALUES(:event_id,:dataset_id,:tenant_id,:outcome)
            ON CONFLICT(event_id) DO NOTHING RETURNING event_id"""), {
                'event_id': event_id, 'dataset_id': dataset_id,
                'tenant_id': tenant_id, 'outcome': outcome,
            }).scalar_one_or_none()
        if recorded is None:
            return None

        if outcome == 'failed':
            conn.execute(text("""UPDATE datasets SET
                failed_count=failed_count+1,
                status=CASE WHEN status='completed' THEN status ELSE 'failed' END,
                error_message=COALESCE(error_message,:error),
                completed_at=CASE WHEN processed_count+failed_count+1 >= line_count THEN now() ELSE completed_at END
                WHERE id=:dataset_id AND tenant_id=:tenant_id"""), {
                    'dataset_id': dataset_id, 'tenant_id': tenant_id,
                    'error': message.get('error', 'A processing stage exhausted retries'),
                })
        else:
            conn.execute(text("""UPDATE datasets SET
                started_at=COALESCE(started_at,now()),
                processed_count=processed_count+1,
                status=CASE
                    WHEN status='failed' THEN 'failed'
                    WHEN processed_count+1+failed_count >= line_count AND failed_count=0 THEN 'completed'
                    WHEN processed_count+1+failed_count >= line_count THEN 'failed'
                    WHEN status='queued' THEN 'processing'
                    ELSE status END,
                completed_at=CASE WHEN processed_count+1+failed_count >= line_count THEN now() ELSE completed_at END
                WHERE id=:dataset_id AND tenant_id=:tenant_id"""), {
                    'dataset_id': dataset_id, 'tenant_id': tenant_id,
                })
    return None


if __name__ == '__main__':
    run_stage(input_topic='logs.persisted', output_topic='datasets.progress.ack',
              group_id='logiq-dataset-progress-v1', transform=transform)
