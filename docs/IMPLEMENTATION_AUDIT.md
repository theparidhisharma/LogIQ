# LogIQ implementation audit

**Audit date:** 2026-11-20  
**Audited artifact:** `LogIQ-development.zip` before Increment 14; Increment 14 changes are recorded below  
**Specification:** supplied `Pasted text.txt`  
**Purpose:** establish the verified baseline before Increment 14. This is a source/configuration audit plus local static checks; it is not a live Docker deployment test.

## Executive verdict

The repository is a meaningful early-stage event-driven log-processing foundation. It contains independent FastAPI processes, a Kafka worker chain, PostgreSQL persistence, MinIO-backed raw dataset storage, tenant-aware authentication, a parser benchmark API, initial template/anomaly records, a React dashboard, and Prometheus/Grafana configuration.

It does **not** yet satisfy the original product specification. The largest functional gap is that parser benchmarking is disconnected from dataset processing: the benchmark endpoint compares available adapters, but the actual parser worker always instantiates `BaselineParser`. The largest product gaps after that are full OTLP/collector ingestion, public dataset imports, a complete intelligence pipeline, independent self-observability, and an end-to-end tested deployment.

No claim of production readiness, full OTLP support, AI anomaly detection, parser adaptivity, or measured scale is justified by the current source.

## Verified baseline checks

| Check | Result | Evidence / limitation |
|---|---|---|
| Python tests (baseline) | **47 passed** | Before Increment 14; 1.21s in the original audit environment |
| Python syntax compilation | **Passed** | `python -m compileall -q services shared migrations migrations_dataset tests` |
| Compose YAML parse (baseline) | **Passed** | 23 services parsed before Increment 14 |
| Monitoring YAML parse | **Passed** | Prometheus, OTel Collector and Grafana provisioning YAML parsed |
| Alembic SQL generation | **Passed** | Core, Identity and Dataset configs each generated offline SQL |
| ZIP integrity | **Passed** | `unzip -t` reported no errors |
| Docker Compose runtime | **Not verified** | Docker CLI is not installed in this environment |
| Frontend build | **Not verified** | `frontend/node_modules` is absent; `npm run build` fails because React/Vite dependencies are not installed, so this is not yet evidence of a source-code build defect |
| Live Kafka/PostgreSQL/MinIO integration | **Not verified** | No infrastructure runtime available in this environment |
| E2E/load/failure-isolation tests | **Missing** | No dedicated integration, E2E or load-test suites in the repository |

## Requirement-by-requirement status

Status meanings: **Implemented** = source path exists and is meaningfully implemented; **Partial** = some functionality exists but the requirement is not complete; **Missing** = no implementation found; **Unverified** = cannot be established without running external infrastructure.

| Original requirement | Status | Findings |
|---|---|---|
| API gateway | Partial | `services/gateway/main.py` proxies a limited set of routes and has `/health`. It does not implement rate limiting, centralized auth enforcement, request validation, request-ID generation/propagation, or comprehensive routing. |
| HTTP JSON collection | Partial | `services/collection/main.py` accepts batches, authenticates API keys and publishes to `logs.raw`. Payload validation is loose and body-size/rate controls are absent. Static issue to verify/fix: Collection passes `application_id` as a string Kafka message key, while its `KafkaProducer` has no key serializer; kafka-python expects byte-like keys by default. |
| Full OTLP Logs | Missing | `/v1/otlp/logs` accepts a custom JSON `logs`/`records` envelope. It does not decode OTLP protobuf or the standard OTLP JSON `resourceLogs/scopeLogs/logRecords` shape. |
| Collector-forwarded ingestion | Missing | `infrastructure/otel/collector.yaml` receives OTLP but exports only to `debug`; no exporter forwards to Collection or another durable LogIQ path. Collector ports are not exposed to the host in Compose. |
| Fluent Bit integration | Missing | No Fluent Bit configuration or service is present. |
| Dataset file upload | Partial | `.log`, `.txt`, `.csv` accepted, UTF-8 checked, raw object stored in MinIO with SHA-256 metadata, and events published in chunks. The multipart spool file is validated in bounded chunks and streamed to MinIO; default upload cap is 5 GiB. The publisher uses bounded samples and a persisted MinIO byte-offset cursor. CSV is treated as line-oriented text rather than parsed according to a documented CSV schema. |
| Public LogHub catalog/import | Missing | No catalog, verified download/import mechanism, licence metadata, or HDFS/Hadoop/OpenStack/BGL entries found. |
| Synthetic datasets | Partial | Synthetic events are generated and published, but scenario configuration is limited; deterministic seeds, timestamps, controlled anomaly patterns and repeatability controls are absent. |
| Live ingestion | Partial | HTTP JSON ingestion exists. Collector/OTLP and file-tail sources are not connected. |
| Common event contract | Partial | `shared/common.py:event()` constructs many required fields. There is no strict shared schema/version compatibility validator. Some fields (for example `schema_version`, `source_name`, and `sequence_number`) are not persisted by the Intelligence insert statement. |
| Preprocessing | Partial | `services/preprocessing/worker.py` provides basic line parsing/normalization. Multiline reconstruction, configurable normalization, robust timestamp formats, structured extraction, redaction and malformed-record policy are incomplete. |
| Parser adapters | Partial | Baseline token-mask parser exists. Drain3 adapter is conditional on package installation, but `drain3` is not in `requirements.txt` and is not installed by the Docker image. PIPLUP is correctly not claimed as implemented. |
| Parser benchmark | Partial | `services/parser/engine.py` implements sample strategies, fresh instances, runtime/throughput/tracemalloc memory, failures and optional exact-template accuracy. It benchmarks only installed adapters (currently likely baseline only in the declared image). Results are returned by API but not persisted as reproducible benchmark records. |
| Adaptive parser selection | **Missing in processing path** | `services/parser/worker.py:transform()` always creates `BaselineParser()`. It does not load a dataset benchmark, chosen policy, or selected parser configuration. Full-dataset processing is therefore not adaptive. |
| Template mining | Partial | Stable token-mask templates and basic frequency/first-seen/last-seen registry exist. Parameter extraction is simplistic; template discovery is not a separately owned service/data pipeline. |
| Anomaly detection | Partial | Worker records new-template, error-event and simple error-burst anomalies. Rolling mean, z-score, IQR, rare-template and prior-window detector functions exist but are not connected to a production aggregation/streaming workflow. Severity distribution shifts and anomaly lifecycle are missing. |
| Analytics/query | Partial | Several tenant-filtered SQL-backed endpoints exist for overview, logs, timeseries, severity, service errors, template trends, templates and anomalies. Search is limited; trace/correlation exploration, advanced filters and analytics-owned read models are missing. Analytics reads `logiq_core` tables owned/written by other services. |
| Identity/authentication | Partial | Registration, login, JWT, admin/member roles, tenant-scoped applications and hashed API keys with expiry/revocation exist. Full policy/RBAC coverage, audit trail, session lifecycle and production secret handling need hardening. |
| Kafka architecture | Partial | Current path uses `logs.raw -> logs.preprocessed -> logs.parsed -> logs.persisted`, stage-specific DLQs, manual commits and bounded retries. The wider documented topic/event catalogue, schema registry/compatibility, transactional outbox and robust event delivery are absent. |
| Database ownership | Partial | Identity and Dataset have separate DB URLs/roles; Collection, Preprocessing, Parser, Intelligence and Analytics still use `logiq_core`. **Identity migration configuration points to the same `migrations/` stream as Core**, so Identity's migration creates unrelated core tables and runs the Core dataset-archive migration in the Identity DB. It needs a dedicated Identity migration stream. |
| Self-observability | Partial | App HTTP request/latency metrics, `/health`, `/ready`, `/metrics`, Prometheus scrape config and Grafana provisioning exist. Worker health/metrics, Kafka lag, queue depth, processing throughput, CPU/memory, container log collection and independent buffering/retry are missing. |
| Independent failure plane | Missing | OTel Collector exports to debug only. No verified test demonstrates monitoring continues to capture failures when Collection is unavailable. |
| Frontend | Partial | Current pages include Overview, Live Log Explorer, Applications, Datasets, Templates, Anomalies, Service Health and Settings. Parser Benchmark and System Monitoring pages are absent. Worker status is explicitly “Not exposed”; service states marked “Routed” are not live health checks. |
| Security | Partial | JWT/API key auth, tenant scoping and upload restrictions exist. Rate limiting, CORS policy review, secret enforcement, log redaction, retention/deletion, audit logging and comprehensive cross-tenant negative tests remain open. `shared/security.py` has a development fallback JWT secret if the environment variable is omitted. |
| Scale/performance | Missing evidence | Dataset upload is buffered in memory; no load tests, throughput measurements, concurrency tests, Kafka lag tests or million-record validation are present. |
| Developer experience | Partial | Compose, shared Dockerfile, env example, migrations, sample logs and README exist. There are no per-service Dockerfiles/dependency manifests, and full Compose startup has not been verified. |
| Automated validation | Partial | 47 tests are present, predominantly unit-level. No dedicated `tests/integration`, `tests/end-to-end`, or `tests/load` coverage exists. |

## Critical findings to address first

### P0 — Adaptive parsing is not connected to dataset processing

- Benchmark API: `services/parser/main.py` and `services/parser/engine.py`.
- Actual pipeline parser: `services/parser/worker.py`.
- The worker always creates `BaselineParser()` for each message.
- Benchmark results are not persisted or referenced by the dataset job.
- There is no full-dataset processing run using the selected parser.

**Consequence:** LogIQ currently has a parser benchmark endpoint, not an adaptive parser pipeline. This is the first major product gap to close after batch reliability is audited.

### P0 — Collection Kafka key type mismatch

- Fixed in Increment 14: `shared/common.py:producer()` now configures a key serializer through `shared.dataset_utils.kafka_key_bytes`.
- String application IDs become UTF-8 bytes; byte keys remain unchanged; unsupported key types fail clearly.
- A unit test covers the key conversion contract.

**Remaining verification:** actual publication against a live kafka-python producer and Kafka broker has not been run in this environment.

### P0 — Identity and Core share a migration history

- `alembic_identity.ini` uses `script_location = migrations`.
- That migration stream creates users/tenants but also datasets, log_events, anomalies and template_registry; its second migration archives the `datasets` table.

**Consequence:** The Identity database is not cleanly owned by Identity despite having its own connection and role. Create `migrations_identity/` with identity-only schema and an explicit safe migration plan for existing volumes.

### P1 — Dataset upload and publisher are not fully streaming

- Upload validation and hashing are incremental; the multipart spool file is streamed to MinIO (default 5 GiB cap).
- The publisher reads the preserved artifact into memory, but only publishes bounded batches of up to 500 events.

**Consequence:** Memory is bounded by the upload cap, not by a streaming design. Before claiming million-line-scale file ingestion, implement streaming upload, incremental checksum/line counting and MinIO range/stream reads.

### P1 — Self-observability is configured but not independent end-to-end

- OTel Collector exporters are debug-only.
- Prometheus scrapes API metrics, not worker/Kafka/host/resource metrics.
- No collector-to-LogIQ forwarding or container log tailing is configured.

**Consequence:** Prometheus/Grafana presence must not be represented as completed self-observability.

### P1 — Dataset publication durability (improved in Increment 14)

- Upload now commits Dataset metadata and a Dataset-owned `dataset_publish_jobs` row in one PostgreSQL transaction after preserving the MinIO artifact.
- `dataset-publisher-worker` publishes bounded batches and checkpoints the next source line. It resumes jobs left queued or publishing after restart.
- Retry resets the durable job and increments the processing attempt. Stable per-line event IDs allow downstream deduplication if Kafka accepted a batch but the checkpoint transaction did not commit.

**Remaining limitation:** this is a durable job/checkpoint pattern, not a fully transactional Kafka/PostgreSQL outbox. The publisher currently assumes one replica; multi-replica lease ownership and live crash/replay tests remain outstanding.

### P1 — Event contract is not preserved end-to-end

- `shared/common.py:event()` contains `schema_version`, `source_name`, `sequence_number` and correlation metadata.
- The `log_events` schema/Intelligence insert omits some contract fields, including `schema_version`, `source_name` and `sequence_number`.

**Consequence:** Complete the schema and migrations before adding downstream analytics that rely on those fields.

## Existing capabilities worth preserving

- MinIO raw artifact storage, SHA-256 checksum and tenant-scoped object key.
- Dataset retry verifies the raw artifact checksum and increments `processing_attempt`.
- Dataset progress is updated by a separate Dataset-owned progress worker, not directly by Intelligence.
- Kafka stage runner uses manual commits, bounded retries, DLQ routing and idempotent event persistence.
- Tenant-scoped API key authentication and tenant filters in Collection, Dataset and Analytics.
- Parser benchmark does not invent quality scores when ground truth is absent.
- Anomaly detector primitives are pure functions with unit tests and can be wired into a real detector workflow.

## Prioritized remediation plan

The sequence below is the recommended execution order. Do not split more databases or add more services until the batch workflow and parser selection are real.

| Increment | Scope | Acceptance gate |
|---|---|---|
| 13 | Audit baseline (this document) | Source-backed status and P0/P1 defects recorded |
| 14 | Batch pipeline reliability + Collection Kafka key fix + dataset durable publication | Real upload reaches persisted logs; all stage counts reconcile; retry/restart is idempotent; no whole-file unbounded buffering |
| 15 | Adaptive parser execution | Benchmark candidates on same sample; persist run; select by policy; selected parser processes complete dataset; report actual parser/version/config |
| 16 | Intelligence completion | Detectors execute on real events/windows and persist evidence-backed anomaly records |
| 17 | Analytics completion | Queries return real tenant-scoped results with pagination/time filters and no cross-service DB reads after read-model migration |
| 18 | Independent self-observability foundation | Prometheus independently detects Collection/API/worker target outages; API and worker metrics are exposed; JSON logs and OTLP file sink configured |
| 19 | Full telemetry ingestion + public dataset import | Standard OTLP payload and Collector-forwarded events reach the same processing pipeline; verified LogHub catalog/import metadata |
| 20 | Service-owned persistence + outbox/contracts | Each service has isolated migrations/credentials; no cross-service SQL; durable event publication and idempotent consumers |
| 21 | Frontend completion | Parser Benchmark and System Monitoring pages; all metrics from real APIs; clear loading/error/empty states |
| 22 | Security hardening | Tenant isolation negative tests, rate limiting, secret enforcement, redaction, retention/deletion, audit trail |
| 23 | Scale and deployment verification | 100K and 1M workload results; full Docker build/start; E2E and failure tests; reproducible setup docs |

## Explicitly unverified

- Docker image builds and actual Compose startup.
- Kafka topic creation, producer behavior and worker consumption against a live broker.
- PostgreSQL migrations against a clean database and an existing development volume.
- MinIO upload/replay against a live MinIO instance.
- Frontend build after dependency installation.
- End-to-end dataset-to-dashboard workflow.
- Live application ingestion.
- Live Collection outage simulation and alert firing in a running Compose stack.
- 100K/1M throughput, memory and recovery behavior.

These are not marked complete until tested in a runtime environment.


## Increment 14 implementation record (2026-11-20)

### Implemented

- Added Kafka key serialization for both string and byte keys; Collection's application-ID key no longer relies on kafka-python's default byte-only behavior.
- Added Dataset migration `dataset_0002` with `dataset_publish_jobs`, including processing attempt, next source-line cursor, retry state, timestamps and error information.
- Dataset upload now preserves the raw artifact in MinIO and atomically commits the dataset row plus its durable publication job. The HTTP request no longer publishes the entire dataset to Kafka.
- Added `dataset-publisher-worker`, registered in Compose. It verifies the raw artifact SHA-256, publishes at most 500 records per batch, flushes Kafka, then checkpoints the next source line.
- Added retry handling with bounded exponential delay and a maximum number of consecutive publication attempts. Failed jobs mark the dataset failed and remain eligible for explicit replay through the existing retry endpoint.
- Dataset retry resets the durable publisher cursor and increments `processing_attempt`; stale progress events remain filtered by attempt number.
- Deterministic per-line event IDs support deduplication if a batch is replayed after a crash between Kafka acknowledgement and database checkpoint commit. The Intelligence persistence worker already uses `ON CONFLICT(event_id) DO NOTHING`.
- Added pure tests for Kafka key conversion, stable replay IDs, cursor paging with blank lines, and migration/Compose registration.

### Increment 14 validation

| Check | Result | Qualification |
|---|---|---|
| Python tests | **54 passed** | Run with a temporary import-only Kafka shim because `kafka-python` is not installed in this execution environment; no broker behavior is simulated or claimed |
| Python compileall | Passed | `shared`, `services`, `migrations_dataset`, and `tests` |
| Compose YAML | Passed | 24 services; publisher worker present |
| Dataset Alembic SQL | Passed | Offline SQL includes `dataset_0002` and `dataset_publish_jobs` |
| Live Kafka/PostgreSQL/MinIO | Not verified | Infrastructure unavailable |
| Docker Compose startup | Not verified | Docker CLI unavailable |

### Remaining Increment 14 limitations

- Upload uses a multipart spool file and streams to MinIO; publisher processing uses bounded samples and resumable byte-range reads.
- Publisher reads the raw artifact into memory before slicing it into 500-event Kafka batches.
- The publisher is configured as one replica; multi-replica leasing/claim expiry is not implemented.
- Kafka acknowledgement and PostgreSQL cursor commit are not one atomic transaction. Replay is made safe through deterministic event IDs and downstream idempotency, but the live crash-window behavior still needs integration testing.
- Synthetic dataset publishing was moved to the durable publisher workflow in Increment 15.


## Increment 15 update — Adaptive parser pipeline

The uploaded-dataset path now benchmarks registered parsers before its first Kafka batch, persists the benchmark report and selected parser/version in the Dataset database, and has the parser worker use that selection for the dataset's processing attempt. Upload requests can configure sampling and policy; quality-dependent policies require aligned user-supplied ground truth. The parser service exposes a tenant-authenticated benchmark-report endpoint. Synthetic datasets now share this durable adaptive path; live application events still use BaselineParser.

This closes the prior benchmark-to-worker disconnect for uploaded datasets at the code level. It does not yet establish production readiness: Kafka/PostgreSQL/MinIO end-to-end execution was not available, Drain3 is optional, stateful parser state is not durable across worker restarts, and live application events do not yet have an adaptive parser policy.


## Increment 15 update — adaptive parser integration

The subsequent Increment 15 artifact connected dataset publisher benchmarking to persisted parser selection and parser-worker lookup for dataset events. Its separate increment notes list the exact changes and known runtime limitations. Live broker execution was not verified.

## Increment 16 update — intelligence completion

Increment 16 adds active event-time statistical checks for rolling volume, z-score and IQR outliers, error-volume spikes, severity-distribution shifts, and population-qualified rare templates. It adds anomaly lifecycle metadata and tenant-scoped status updates.

**Increment 16 verification:** 71 Python tests passed in 0.66 seconds using a temporary Kafka import shim; intelligence-specific tests passed 15/15; core Alembic offline SQL generation reached `0003_anomaly_lifecycle`; Python compilation passed. The shim means these results do not verify a live Kafka broker. Docker and full service integration remain unverified.

**Remaining intelligence gaps:** statistical evaluation currently queries PostgreSQL per newly persisted event and should move to efficient windowed aggregates before scale testing; late-arrival/watermark handling is not implemented; automatic anomaly resolution is not implemented; frontend anomaly lifecycle controls are not yet wired; the detectors are deterministic statistical heuristics, not AI.


## Increment 17 update — Analytics and query engine

Added tenant-scoped log search filters (service, severity, application, environment, template, trace, request, source, dataset and time), stable keyset pagination, optional total counts, event detail retrieval, template parameter drill-down, service summaries and corrected hourly template/event trends. Gateway routes log detail requests to Analytics. Core migration `0004_analytics_query_indexes` adds tenant-first indexes for the common query paths.

**Increment 17 verification:** 78 tests passed in 0.72 seconds using a temporary Kafka import shim; Python compilation and Compose YAML parsing passed; Analytics FastAPI import/OpenAPI generation passed; Core, Identity and Dataset Alembic offline SQL generation passed. This does not constitute live PostgreSQL query-plan, Kafka, Docker or E2E verification.

**Remaining Analytics limitations:** substring search still uses `ILIKE` without trigram/full-text indexing; offset pagination remains for compatibility; benchmark and dataset records remain in the Dataset DB and must be queried through Dataset APIs; parameter sample values require appropriate redaction policy; actual query performance requires PostgreSQL `EXPLAIN ANALYZE` on representative data.


## Increment 18 update — Independent self-observability foundation

Added JSON stdout logging with request-ID context, request-ID response propagation, normalized API metric path labels, Prometheus metrics for API request count/latency, and process-local metrics endpoints for Kafka stage workers and the dataset publisher. Prometheus now scrapes the gateway, all seven internal APIs, and five workers; rules detect Collection scrape failure, worker metrics endpoint failure, and sustained API 5xx rates. Grafana's provisioned dashboard now includes API/worker availability, request rate, p95 latency, throughput, retries, and failures. The OTLP Collector accepts OTLP gRPC/HTTP and writes received telemetry to a rotated persistent file as well as debug output. Smoke-test and optional Collection-outage simulation scripts are included.

**Increment 18 verification:** 81 Python tests passed using a temporary import-only Kafka shim; Python compilation passed; Compose (24 services), Prometheus, alert, OTEL and dashboard configs parsed; all 13 Prometheus scrape targets match Compose service names; gateway OpenAPI generation passed. Docker/Compose was not available, so live scraping, alert firing, OTLP file export and the outage simulation were not run.

**Remaining self-observability gaps:** Python services do not yet automatically export stdout logs, metrics or traces over OTLP; the Collector only receives OTLP from instrumented clients. No Alertmanager notification route is configured. Kafka consumer lag, Redis queue depth, PostgreSQL pool health, MinIO health and host/container resource exporters remain absent. Worker metrics are process-local. This increment establishes independent scrape-based detection in configuration, not a runtime-verified failure plane.


## Increment 19 — OTLP Logs and public dataset catalog

Collection accepts OTLP/HTTP Logs in protobuf and standard OTLP JSON. The OTel Collector forwards OTLP logs to Collection using a shared internal token; tenant attribution is required through the `logiq.tenant_id` resource attribute and validated against Identity storage. Resource attributes, log attributes, scope metadata, severity, timestamp, trace ID and span ID are mapped into the shared LogIQ event schema. OTLP metrics/traces remain debug-only and are not yet routed into LogIQ analytics. The Collector retry queue is bounded in-memory; the rotated file exporter is an independent local copy, not a durable delivery queue.

Dataset API exposes a LogHub catalog sourced from the upstream `logpai/loghub` README and stores source reference/metadata when users upload extracted raw files with `source_type=loghub`. This is catalog-assisted manual import, not automated downloading/decompression. The default 5 GiB application limit makes the listed HDFS_v1 and BGL raw files size-eligible, subject to available spool disk, proxy limits, timeouts and MinIO capacity. Upstream LogHub says datasets are available for research/academic work and asks users to cite its papers; users must review current terms before use. Source: https://github.com/logpai/loghub/blob/master/README.md

**Increment 19 verification:** 88 Python tests passed using a temporary import-only Kafka shim; OTLP JSON and protobuf decoding, trace/span ID conversion, severity mapping, token-authenticated internal publishing, and catalog metadata have unit coverage. Python compileall, Compose/OTel/Prometheus YAML parsing, Grafana JSON parsing and Dataset Alembic offline SQL generation passed. Live Collector-to-Collection delivery, real Kafka publication, Docker startup and frontend integration were not run.

**Remaining gaps:** no automated LogHub archive fetch/decompression, no streaming uploads for large datasets, no OTLP metrics/traces ingestion into LogIQ's event/query model, no service auto-instrumentation, and no disk-backed Collector retry queue. Tenant resource attributes must be injected by trusted instrumented applications; the shared token alone does not make client-supplied tenant attributes trustworthy if the token is exposed.


## Increment 20 update — streaming dataset ingestion

The previous 50 MiB in-memory upload limitation has been addressed in code. Dataset uploads now validate UTF-8, calculate SHA-256 and count non-empty lines incrementally from the multipart spool file, then pass the seekable file to MinIO. The default application limit is 5 GiB (`DATASET_MAX_UPLOAD_BYTES`). The publisher verifies the raw object's checksum, samples only a bounded number of lines for parser selection, and streams bounded publication batches from MinIO range reads. Dataset DB migration `dataset_0005` adds a persistent byte-offset cursor so later batches resume without rescanning earlier bytes.

This is code-level implementation, not a verified 5 GiB production upload claim. No real large LogHub archive, Docker Compose runtime, MinIO range-read integration, Kafka end-to-end flow or throughput/memory benchmark was executed in this environment. Proxy request limits, timeouts and spool-disk sizing remain deployment concerns. Large ground-truth label arrays remain a separate scaling limitation.


Increment 20 verification record: 95 Python tests passed; Python compilation passed; Dataset Alembic offline SQL generation through `dataset_0005` passed; Compose/OTel/Prometheus/Grafana YAML and Grafana dashboard JSON parsed successfully. Tests used a temporary Kafka import shim because `kafka-python` is absent in the isolated environment. No Docker, live PostgreSQL, MinIO, Kafka or large-file runtime test was run.


## Increment 21 update — publisher delivery and retry correctness

The dataset publisher now waits for Kafka send futures to report successful delivery for every event in a bounded batch before advancing the durable MinIO byte cursor. The configured batch size is validated to 1–5,000. A Kafka failure leaves the cursor unadvanced and enters the existing retry/backoff path; a crash after broker acknowledgement but before the cursor transaction commits can still replay records, protected by deterministic event IDs and downstream idempotency.

Dataset retry is now a single Dataset DB transaction: lock the tenant-owned dataset row, clear prior-attempt progress ledger entries, increment the attempt, reset dataset counters/state, and reset the publisher job's line and byte cursors. This closes the previous split-transaction window.

Added tests cover Kafka future acknowledgement/failure semantics and streaming line/cursor behavior across small reads, UTF-8 multibyte characters, CRLF, LF and blank lines. No live Kafka/PostgreSQL/MinIO or Docker crash-recovery test was run; batch concurrency within one dataset remains serialized.


## Increment 22 update — publisher measurements and cancellation

Dataset publication now persists acknowledged batch bytes and elapsed milliseconds, plus first/last batch timestamps and last-batch duration. The tenant-scoped dataset progress endpoint exposes these counters and a derived average publisher-stage bytes/second. The measured interval includes MinIO range reads, event construction and Kafka acknowledgement; it excludes parser benchmarking, downstream persistence, idle time and end-to-end completion. It is an observed operational metric, not a benchmark claim.

Added cooperative cancellation through `POST /v1/datasets/{dataset_id}/cancel`. The API sets a durable request flag under tenant ownership; the publisher observes it before benchmark work or at the next batch boundary, then marks the job and dataset cancelled. An in-flight acknowledged batch is not forcefully interrupted, already-published events are not retracted, and the raw MinIO artifact is retained. Retry resets the cancellation flag and telemetry counters. `dataset_0006` adds the persisted fields and cancelled job state.

The existing row-lock plus `SKIP LOCKED` claim pattern allows separate publisher replicas to work on different dataset jobs; one dataset remains serialized. Compose still runs one replica by default. No same-dataset parallel partitioning, Kafka-lag backpressure, RSS profiling, or artifact deletion was introduced.

**Increment 22 verification:** 103 tests passed using a temporary import-only Kafka shim; compileall passed; Dataset Alembic offline SQL generation reached `dataset_0006`; Compose YAML parsed with 24 services. Live PostgreSQL/Kafka/MinIO/Docker, cancellation race fault injection, large LogHub import, throughput and RSS measurements were not run.


## Increment 23 — Durable dataset artifact deletion

Added tenant-scoped `DELETE /v1/datasets/{dataset_id}` as an idempotent durable deletion request. The API marks the dataset `deleting`, records a tombstone timestamp and requests publisher cancellation. Publisher claims exclude deletion-requested datasets; the progress consumer ignores late progress events. A separate `dataset-deletion-worker` claims tombstones with `FOR UPDATE SKIP LOCKED`, removes the MinIO raw artifact, then clears object metadata and marks the retained dataset row `deleted`. MinIO errors remain retryable; a crash after object deletion but before DB commit repeats the idempotent delete on the next pass. Dataset migration `dataset_0007` adds deletion state and a partial queue index.

**Increment 23 verification:** 107 Python tests passed with a temporary import-only Kafka shim; compileall passed; Dataset Alembic offline SQL generated through `dataset_0007`; Compose parsed with 25 services; JSON configuration files parsed. Unit tests simulate MinIO failure and a DB commit failure after object deletion. No live MinIO/PostgreSQL/Docker integration or actual process-kill fault injection was run.

**Important deletion boundary:** this increment physically deletes the preserved raw MinIO artifact but retains a dataset tombstone and does not delete already-published log events or derived intelligence/analytics records. Full cross-service data erasure and retention orchestration remain unimplemented.


## Increment 24 — Cross-service dataset erasure protocol

Increment 24 upgrades Increment 23's raw-artifact tombstone into an asynchronous erasure protocol. Dataset artifact cleanup now writes a stable `dataset.deletion_requested` record to a Dataset-owned outbox after MinIO deletion. The outbox publisher waits for Kafka acknowledgement before marking publication complete. Intelligence consumes the command, deletes tenant/dataset-scoped persisted log events, recomputes aggregate template registry frequencies and time bounds from surviving events, removes event-specific error anomalies that can be tied to deleted event IDs, and records an idempotency receipt in Core DB. Intelligence then publishes `dataset.deletion_acknowledged`; Dataset finalizes its tombstone only after validating that acknowledgement. Analytics currently queries the same Core log-event read model, so it observes the deletion without a second consumer.

Migrations: Dataset `dataset_0008` adds artifact deletion timestamp and outbox; Core `0005_dataset_deletion_receipts` adds the Intelligence idempotency ledger. New Compose workers: `intelligence-deletion-worker` and `dataset-deletion-ack-worker`.

**Increment 24 verification:** 111 Python tests passed with a temporary import-only Kafka shim; compileall passed; Dataset and Core Alembic offline SQL generated through their new heads; Compose YAML parsed. Live Kafka, PostgreSQL, MinIO, Docker and full cross-service failure injection remain unverified.

**Remaining erasure limitation:** aggregate anomalies do not yet carry reliable dataset provenance. Event-specific error anomalies are removed where their sample contains the deleted event ID, but aggregate anomaly records may remain influenced by deleted dataset events. Do not claim complete erasure of all derived anomaly evidence until provenance/recomputation is implemented.
