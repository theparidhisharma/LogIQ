# LogIQ — Increment 24: Cross-Service Dataset Erasure Protocol

## Scope

Increment 23 removed the raw MinIO object but did not erase published log events or derived records. Increment 24 introduces a durable, versioned Kafka command and acknowledgement so the Dataset service only finalizes its tombstone after Intelligence confirms erasure.

## Protocol

1. `DELETE /v1/datasets/{dataset_id}` records `deletion_requested_at`, marks the dataset `deleting`, and requests publisher cancellation.
2. Dataset deletion worker removes the MinIO object. In the same Dataset DB transaction it clears raw-object metadata, records `artifact_deleted_at`, and inserts a stable `dataset.deletion_requested` event into `dataset_deletion_outbox`.
3. The outbox publisher sends the event to `datasets.deletion_requested` with `acks=all` through the shared Kafka producer. It marks the row published only after broker acknowledgement. If it crashes after broker acknowledgement but before marking the row, it republishes the same event ID.
4. Intelligence consumes with a dedicated consumer group. In one Core DB transaction it deletes tenant-and-dataset-scoped `log_events`, recomputes aggregate template frequencies/timestamps from surviving logs, removes event-specific error anomalies whose samples identify deleted event IDs, and writes `dataset_deletion_receipts` for idempotency.
5. Intelligence publishes `dataset.deletion_acknowledged` only after the Core transaction commits. If acknowledgement publication fails, Kafka redelivery observes the receipt and republishes the acknowledgement.
6. Dataset acknowledgement worker validates the service identity and only marks the retained tombstone `deleted` when both the deletion request and `artifact_deleted_at` are present.

## Service ownership clarification

Analytics currently queries the Core `log_events` read model; it does not own a separate persisted copy of dataset log rows. Deleting those rows in Intelligence's Core persistence therefore removes them from Analytics queries without adding a second competing delete consumer. This is a current architectural fact, not a claim that Analytics has a fully independent database.

## Migrations and code

- Dataset DB `dataset_0008`: `artifact_deleted_at`, durable deletion outbox and pending-event index.
- Core DB `0005_dataset_deletion_receipts`: idempotency ledger for Intelligence deletion commands.
- `services/dataset/deletion_worker.py`: MinIO cleanup plus durable outbox publication.
- `services/intelligence/deletion_worker.py`: command validation, tenant-scoped deletion, template aggregate recomputation, receipt ledger and acknowledgement.
- `services/dataset/deletion_ack_worker.py`: validates acknowledgement and finalizes tombstone.
- Compose registers both new worker processes.
- Dataset list/detail include deletion lifecycle timestamps.

## Delivery semantics

At-least-once command and acknowledgement delivery. Stable event IDs and the Core receipt table make repeated commands safe. The Dataset outbox is the durable publication source. A broker acknowledgement followed by a Dataset DB failure can produce a duplicate command; the Intelligence receipt prevents repeating the destructive operation. A Core commit followed by an acknowledgement publish failure causes redelivery and acknowledgement replay.

## Validation

- 111 Python tests passed using a temporary import-only Kafka shim; the shim does not emulate a broker.
- Python compileall passed.
- Dataset migration offline SQL generated through `dataset_0008`.
- Core migration offline SQL generated through `0005_dataset_deletion_receipts`.
- Compose YAML parsed successfully.
- Protocol contract and acknowledgement validation tests added.

## Explicit limitations

- Live Kafka/PostgreSQL/MinIO and Docker Compose were not available; the full multi-service protocol has not been exercised against running infrastructure.
- The `anomalies` table contains aggregate anomaly records without a complete dataset provenance column. This increment removes event-specific error anomalies that can be tied to deleted event IDs, but it does not claim to perfectly rebuild or erase every aggregate anomaly that may have been influenced by a dataset. A future schema change should persist dataset provenance or recompute aggregate anomalies from surviving events.
- Template registry is tenant/application/service/template aggregate data. Frequencies and time bounds are recomputed from surviving `log_events`; template rows with no remaining events are removed.
- Kafka topic creation currently relies on the existing broker auto-create configuration.
- This is an asynchronous erasure workflow. The API initially returns `deletion_pending`; clients should poll dataset detail until status is `deleted`.
