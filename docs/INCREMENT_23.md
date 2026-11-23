# LogIQ Increment 23 — Durable dataset artifact deletion

**Date:** 2026-11-22  
**Baseline:** Increment 22

## Implemented

### Tenant-scoped deletion request

- Added `DELETE /v1/datasets/{dataset_id}`.
- The API authenticates the caller and scopes lookup by both dataset ID and tenant ID.
- Deletion is idempotent: repeated requests return the existing `deletion_pending` or `deleted` state.
- The API does not synchronously remove MinIO data and does not erase the dataset row. It records a durable tombstone (`deletion_requested_at`) and changes status to `deleting`.
- The active publisher job receives `cancel_requested=TRUE`. The publisher's claim queries exclude datasets with a deletion request, and the progress consumer ignores subsequent notifications for them.
- The dataset row remains as a tombstone for auditability; no cross-service database cascade is introduced.

### Retryable MinIO cleanup worker

- Added `services.dataset.deletion_worker`, registered as `dataset-deletion-worker` in Compose.
- The worker claims one pending tombstone using `FOR UPDATE SKIP LOCKED`, deletes the MinIO raw object, and only then clears the object key/checksum/size and commits `deleted_at` plus status `deleted`.
- If MinIO deletion fails, the transaction records an attempt count and error type; the tombstone remains pending for retry.
- If MinIO deletion succeeds but the DB commit fails, the next pass repeats the object deletion and then commits the tombstone. Object deletion is treated as an idempotent operation.
- Migration `dataset_0007` adds deletion timestamps, retry count, error state and a partial queue index.

### Safety boundaries

- This is soft deletion of dataset metadata plus physical deletion of the raw artifact, not full erasure of all derived log events, templates, anomalies, or analytics data.
- Already-published Kafka events cannot be retracted. Downstream log records remain governed by their own service retention/deletion policy.
- Dataset IDs and progress history remain available as tombstones; raw artifact metadata is cleared after successful object deletion.
- No automated retention policy or tenant-wide purge endpoint is added.

## Verification

| Check | Result | Qualification |
|---|---|---|
| Python tests | **107 passed** | Temporary import-only Kafka shim used; no broker simulation |
| Python compileall | Passed | Services, shared code, migrations and tests |
| Dataset Alembic offline SQL | Passed | Generated through `dataset_0007` |
| Docker Compose YAML | Passed | 25 services parsed, including deletion worker |
| JSON configuration parse | Passed | Repository JSON files parsed |
| Live MinIO delete/retry | Not run | No MinIO runtime available |
| Live PostgreSQL lock/commit crash test | Not run | Fake transaction tests cover delete-then-commit failure/retry semantics only |
| Docker startup / full E2E | Not run | Docker runtime unavailable |

## Remaining work

- Run migration `dataset_0007` against a real existing Dataset database.
- Verify MinIO remove-object behavior and credentials against a live bucket.
- Fault-inject process termination after object deletion and before PostgreSQL commit.
- Define and implement derived-data retention across Core/Analytics/Intelligence before claiming complete dataset erasure.
- Add operational dashboards/alerts for deletion backlog age, attempts and failures.
