# Increment 14 — Batch publication reliability

## Changes

1. Kafka producers serialize string keys as UTF-8 and preserve byte keys.
2. Uploaded datasets create a durable publication job in the same transaction as dataset metadata.
3. `dataset-publisher-worker` verifies the MinIO artifact checksum, publishes at most 500 log events per batch, and checkpoints its next source-line cursor.
4. Jobs resume from `queued` or `publishing` after a worker restart. A replay can resend the last batch if Kafka acknowledged it before the cursor commit; deterministic per-line event IDs and Intelligence's idempotent insert protect persistence from duplicates.
5. Explicit dataset retry resets the publisher cursor and increments the processing attempt.

## Runtime setup

The new `dataset_0002` migration is applied by the existing `migrate-dataset` service. Compose starts one `dataset-publisher-worker` replica. Do not scale this worker horizontally until a lease/claim-expiry mechanism is implemented.

## Validation

- 54 unit/static tests passed with a temporary Kafka import shim because `kafka-python` is unavailable in the build environment.
- Python compilation passed.
- Compose YAML parsed with 24 services.
- Dataset Alembic offline SQL generated successfully and includes the new table.
- Live Kafka, PostgreSQL, MinIO, Docker startup and crash/restart behavior remain unverified.

## Known limitations

The upload and publisher still read the full artifact into memory (bounded by the 50 MiB upload limit). Synthetic dataset publication is still synchronous. This increment improves restart-safe batch publication; it does not yet provide a fully transactional outbox or production-grade distributed publisher leasing.
