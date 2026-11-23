# LogIQ Kafka Event Contracts

## Dataset deletion request — `datasets.deletion_requested`

Version 1 payload:

```json
{
  "event_id": "dataset-deletion:<dataset-id>",
  "event_type": "dataset.deletion_requested",
  "schema_version": 1,
  "dataset_id": "<dataset-id>",
  "tenant_id": "<tenant-id>"
}
```

Producer: Dataset deletion outbox publisher. Message key: stable event ID. Delivery: at least once; the outbox row is marked published only after the Kafka future acknowledges the send. A send acknowledged by Kafka followed by a failed outbox update may be replayed with the same ID.

Consumer: Intelligence deletion worker, group `logiq-intelligence-dataset-deletion-v1`. It validates the version and required identifiers, performs tenant-scoped deletion and writes a receipt in the same Core DB transaction. A repeated event for the same dataset/tenant does not repeat deletion. A dataset ID associated with another tenant is rejected.

## Dataset deletion acknowledgement — `datasets.deletion_acknowledged`

Version 1 payload:

```json
{
  "event_id": "dataset-deletion-ack:<dataset-id>",
  "event_type": "dataset.deletion_acknowledged",
  "schema_version": 1,
  "dataset_id": "<dataset-id>",
  "tenant_id": "<tenant-id>",
  "service": "intelligence",
  "deleted_events": 123
}
```

Producer: Intelligence deletion worker, after the Core DB transaction commits. Consumer: Dataset acknowledgement worker, group `logiq-dataset-deletion-ack-v1`. It finalizes only a matching tenant-owned row with a recorded deletion request and `artifact_deleted_at`. Unmatchable or invalid acknowledgements are routed to `datasets.deletion_acknowledged.dlq`; the offset is committed only after successful DLQ publication.

## Data ownership and derived data

Analytics currently reads the Core `log_events` table, so it sees Intelligence's deletion directly. Template registry rows are aggregate across datasets and are recomputed from surviving log events. Event-specific error anomalies are removed when their sample identifies a deleted event ID. Aggregate anomalies do not yet have reliable dataset provenance and cannot all be safely attributed to one dataset; see `INCREMENT_24.md`.
