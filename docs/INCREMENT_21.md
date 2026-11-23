# LogIQ Increment 21 — Dataset Publisher Reliability

## Goal

Make dataset publication safer under Kafka delivery failures and concurrent retry requests. This increment focuses on correctness at the boundary between Kafka acknowledgements and the durable MinIO byte cursor.

## Implemented

### 1. Per-record Kafka acknowledgement before cursor advancement

The dataset publisher now collects the Kafka send futures for a bounded batch, flushes the producer, and calls `get()` on every future. The durable `next_line_number` and `next_byte_offset` are updated only after every record future reports successful delivery.

If a future raises a broker/timeout error, the database transaction rolls back and the job enters the existing retry/backoff path. A crash after Kafka acknowledgement but before the cursor commit can still replay the batch; deterministic dataset event IDs and downstream idempotency remain the protection against duplicates.

### 2. Bounded publisher batch configuration

`DATASET_PUBLISH_BATCH_SIZE` is validated at process startup and must be between 1 and 5,000. This prevents accidental unbounded batch configuration and keeps the number of in-flight send futures bounded by a known limit. The default remains 500.

### 3. Atomic dataset retry reset

The retry endpoint previously updated the dataset attempt/progress in one transaction and reset the publisher job in a second transaction. A process crash between those commits could leave a queued dataset paired with an old failed publisher job.

The endpoint now performs the tenant-scoped row lock, progress-event cleanup, attempt increment, dataset reset, and publisher-job cursor/status reset in one Dataset DB transaction. Both cursors reset together (`next_line_number=1`, `next_byte_offset=0`).

### 4. Additional streaming cursor regression coverage

Added tests for:
- UTF-8 multibyte characters split across small reads.
- CRLF and LF line endings.
- Blank lines between published lines.
- Byte-offset continuation without repeating the prior line.
- Cursor preservation through empty source lines.

## Verification

- Python test suite: 99 passed.
- Python compilation: passed.
- Dataset Alembic offline SQL generation through `dataset_0005`: passed.
- Compose and observability configuration parsing: carried forward from Increment 20.

Tests use a temporary Kafka import shim because `kafka-python` is not installed in this isolated environment. The acknowledgement helper is unit-tested with fake producer futures; no real Kafka broker was exercised.

## Remaining limits

- The delivery acknowledgement and retry behavior have not been verified against a live Kafka broker.
- Crash-window recovery has not been tested with Docker/PostgreSQL/Kafka running together.
- At-least-once replay remains intentional; downstream idempotency is required.
- A single publisher job remains serialized by its Dataset DB row lock. This increment does not introduce parallel batches for one dataset, which would require partitioned cursors and ordering semantics.
- Dataset cancellation/deletion and live throughput/memory profiling remain future work.

## Local validation record

- `pytest -q`: 99 passed.
- `compileall`: passed.
- Dataset Alembic offline SQL generation to `head` (`dataset_0005`): passed.
- Docker Compose YAML: parsed successfully (24 services).
- OTel Collector, Prometheus, alert rules YAML and Grafana dashboard JSON: parsed successfully.
- Test execution used a temporary Kafka import shim; this does not simulate broker acknowledgements. The helper's future/ack contract was unit-tested with fake futures.
