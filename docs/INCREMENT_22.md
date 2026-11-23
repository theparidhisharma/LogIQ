# LogIQ Increment 22 — Dataset throughput telemetry and cooperative cancellation

**Date:** 2026-11-22  
**Baseline:** Increment 21

## Implemented

### Per-dataset publication measurements

- Dataset publisher records cumulative acknowledged publication bytes, cumulative batch-processing milliseconds, the most recent batch duration, and batch timestamps in the Dataset-owned `dataset_publish_jobs` row.
- The measured interval covers MinIO range-read, line parsing/event construction, Kafka send, flush and per-record acknowledgement. It does not include parser benchmark time, downstream consumer processing, idle polling, or end-to-end dataset completion latency.
- `GET /v1/datasets/{dataset_id}/progress` now returns publisher cursor, byte/time counters, last-batch time/duration, publisher start time, and a derived average `publish_bytes_per_second` for the measured publisher interval.
- The metric is derived from observed counters; no target throughput or performance claim is asserted.

### Cooperative cancellation

- Added tenant-authenticated `POST /v1/datasets/{dataset_id}/cancel`.
- Cancellation is a durable request flag, not an unsafe force-kill. The publisher checks it while holding the job row lock before benchmarking and again before publishing each batch.
- A running batch is allowed to finish and be acknowledged. Cancellation takes effect at the next batch boundary; the job and dataset then enter `cancelled`.
- The original MinIO raw artifact is intentionally retained. Cancellation does not delete source data or attempt to retract already-published Kafka records.
- Terminal datasets/jobs reject cancellation with HTTP 409. Missing or cross-tenant datasets return 404.
- Explicit retry of failed jobs resets cancellation and publication counters; cancelled jobs are not implicitly retried.

### Concurrency and recovery semantics

- The existing `FOR UPDATE ... SKIP LOCKED` claim pattern remains in place. Separate publisher-worker replicas can claim different dataset jobs; the same dataset remains serialized by its job-row lock and byte cursor.
- Kafka acknowledgement still precedes cursor commit. If the process dies after acknowledgement and before the database transaction commits, the batch can replay; deterministic per-line event IDs and downstream idempotency remain the recovery mechanism.
- No same-dataset parallel partitioning was introduced because that would require independently durable partitions/cursors and ordered completion semantics.

### Migration

- Added Dataset migration `dataset_0006` with cancellation state, measured publication counters/timestamps, and a `cancelled` job status.

## Verification

| Check | Result | Qualification |
|---|---|---|
| Python tests | **104 passed** | Temporary import-only Kafka shim used because `kafka-python` is absent in this environment |
| Python compileall | Passed | Services, shared code, migrations and tests |
| Dataset Alembic offline SQL | Passed | Generated through `dataset_0006` |
| Docker Compose YAML | Passed | 24 services parsed |
| Monitoring YAML / Grafana JSON | No changed monitoring files | Existing config was not modified in this increment |
| Live PostgreSQL migration | Not run | No live database available |
| Live Kafka acknowledgement/cancellation race | Not run | Unit tests and source-level checks only |
| Docker startup / full E2E | Not run | Docker runtime unavailable |
| Large LogHub import / RSS profiling | Not run | No multi-GB dataset was downloaded or processed |

## Limitations / next work

- Throughput is publisher-stage byte throughput, not end-to-end records/sec or application ingestion throughput.
- `total_publish_ms` accumulates successful batch durations only; failed attempts and idle wait are excluded.
- Memory/RSS profiling and Kafka-consumer-lag-based backpressure are not implemented. No reliable lag signal is currently wired into this publisher, so the worker does not pretend to throttle on one.
- Multiple replicas may process independent datasets, but Compose currently declares one publisher worker by default. Same-dataset publication remains single-lane.
- Cancellation is cooperative and only checked between batches. It does not cancel an in-flight Kafka send or delete the preserved artifact.
- No physical deletion workflow was added; safe deletion still needs a durable tombstone/cleanup state machine and retryable MinIO cleanup.
- The acknowledged-send / DB-commit crash window still requires live infrastructure fault-injection testing.
