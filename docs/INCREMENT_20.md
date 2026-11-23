# LogIQ Increment 20 — Streaming Dataset Importer

## Goal

Remove the previous 50 MiB upload bottleneck and make LogHub-sized files practical without holding the full raw artifact in application memory.

## Implemented

- Dataset uploads are read from FastAPI's multipart spool file in bounded chunks.
- UTF-8 validation, SHA-256 calculation, byte counting and non-empty physical-line counting run incrementally.
- The seekable spool file is passed to MinIO `put_object` with a known length; the raw object remains immutable and tenant-scoped.
- Default maximum upload size is 5 GiB, configured by `DATASET_MAX_UPLOAD_BYTES` (bytes).
- Dataset publisher verifies the MinIO object's SHA-256 before parser selection.
- Parser benchmarking uses bounded-memory first-N, reservoir-random or severity-stratified samples rather than materializing all lines.
- Publishing reads MinIO object ranges and processes bounded line batches.
- Dataset publish jobs persist `next_byte_offset` alongside `next_line_number`, so each batch resumes from the last confirmed line instead of rescanning the entire file from byte zero.
- Retry resets both cursors to zero and replays the immutable raw artifact.
- Added Dataset DB migration `dataset_0005`.
- Added unit tests for UTF-8 validation, upload limits, checksum verification, bounded samples, line batching and byte-offset resume.

## Important implementation detail

The ASGI multipart parser spools uploaded file content to a temporary file (memory first, then disk depending on framework threshold). The Dataset service does not call `await file.read()` to construct one giant `bytes` object. It computes metadata in chunks and streams that file object to MinIO.

The publisher performs one full checksum pass and one full sampling pass when parser selection is first needed. Subsequent publishing batches use MinIO range reads from the persisted byte cursor. This avoids repeated full-file scans between batches.

## Limits / not yet verified

- The default 5 GiB limit is an application setting, not a tested production ingress/proxy limit. Reverse proxies, request timeouts, temporary disk capacity and MinIO multipart behavior must be configured for the target deployment.
- No real 1.47 GiB LogHub file was downloaded or imported in this environment.
- MinIO range reads, Kafka publishing and PostgreSQL cursor commits were unit-tested only at helper/configuration level; Docker end-to-end behavior remains unverified.
- Ground-truth template labels are still stored as a JSON array in Dataset PostgreSQL; very large labeled imports may need a separate streamed label artifact format.
- `DATASET_MAX_UPLOAD_BYTES` should be reduced if temporary disk or object-storage capacity is constrained.
- A crash after Kafka acknowledges a batch but before the byte cursor transaction commits can replay that batch. Deterministic event IDs and downstream idempotency protect the existing at-least-once design.

## Verification

See the Increment 20 audit and test results in the repository. No live throughput or memory benchmark is claimed.


## Local verification record

- Python test suite: 95 passed.
- Python compilation: passed.
- Dataset Alembic offline SQL generation through `dataset_0005`: passed.
- Compose YAML and OTel/Prometheus/Grafana YAML parsing: passed.
- Grafana dashboard JSON parsing: passed.
- Tests used a temporary Kafka import shim because `kafka-python` is not installed in this isolated test environment; the shim is not part of the repository and does not verify Kafka broker behavior.
