# Increment 15 — Adaptive parser integration

## Implemented

- Added dataset-owned parser selection metadata and benchmark persistence (`dataset_0003`).
- Uploaded datasets can configure sampling strategy, sample size, seed, minimum-quality threshold and selection policy.
- Quality-constrained and multi-objective policies require caller-supplied ground-truth templates as a JSON array aligned with non-empty input lines.
- The durable dataset publisher benchmarks registered parser candidates before publishing the first Kafka batch and commits the report and selected parser in the Dataset database.
- The parser worker resolves the selected parser for each dataset and processing attempt. It refuses dataset events when selection metadata is missing or belongs to a stale attempt.
- Parser instances are cached per dataset/attempt in the worker process so stateful adapters can process ordered records as a stream. Non-dataset live application events continue to use the baseline parser.
- Added a tenant-authenticated endpoint to retrieve a dataset's persisted benchmark report.
- Added parser factory, ground-truth alignment and worker selection tests.

## Verification

- Python compilation passed.
- 60 tests passed using a temporary import shim for `kafka-python`, which is not installed in the execution environment.
- Live Kafka/PostgreSQL/MinIO processing and Docker startup were not run.

## Known limitations

- BaselineParser is the only parser guaranteed to be available from the pinned requirements. Drain3 remains optional and is discovered only when installed.
- Ground-truth policies require an explicitly supplied label array; no automatic labels are invented.
- Benchmarking currently reads the preserved raw artifact into memory. The upload limit remains 50 MiB.
- Stateful parser model state is held in worker memory; a worker restart resets that parser's learned state. Durable Drain3 state snapshots are a separate hardening task.
- Synthetic dataset generation now stores a raw artifact and uses the same durable publisher and adaptive parser-selection path as uploaded files.
