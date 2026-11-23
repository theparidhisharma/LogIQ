# LogIQ — Centralized Observability & Intelligent Log Analytics

A runnable local development foundation implementing a real Kafka-backed log path, independent FastAPI services, PostgreSQL persistence, a React dashboard, and Prometheus/Grafana monitoring.

> **Scope honesty:** This is a working development vertical slice, not yet a production-complete implementation of every requirement in the supplied specification. The limitations are listed below. No benchmark gains or AI claims are fabricated.

## Quick start (Windows / Docker Desktop)

1. Install Docker Desktop and Git.
2. Extract/clone this repository and open the `logiq` folder.
3. Copy `.env.example` to `.env`.
4. Run `docker compose up --build -d`.
5. Open:
   - Dashboard: http://localhost:5173 (React frontend)
   - Grafana: http://localhost:3000 (admin / admin)
   - Prometheus: http://localhost:9090
   - MinIO console: http://localhost:9001 (logiq / logiq-secret-change-me)
   - Worker API docs: http://localhost:8002/docs, http://localhost:8003/docs, and http://localhost:8004/docs.

The frontend is built and served by the Compose `frontend` container at http://localhost:5173.

## Ingest a sample log

Create a workspace in the dashboard or follow the PowerShell registration and API-key steps in [Identity, authentication and tenant isolation](#identity-authentication-and-tenant-isolation-development-increment-5). Then send logs using the generated API key. Log ingestion no longer accepts a shared hardcoded development key.

## Process Kafka stages

The worker APIs are exposed locally for development. Process each stage in order:

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8002/internal/process-once?limit=1000"
Invoke-RestMethod -Method Post -Uri "http://localhost:8003/internal/process-once?limit=1000"
Invoke-RestMethod -Method Post -Uri "http://localhost:8004/internal/process-once?limit=1000"
```

Repeat while each response reports processed records. Production deployment should replace manual polling with continuously supervised consumers.

## Service map

| Service | Responsibility | Container |
|---|---|---|
| Gateway | Single routing entry point | `gateway` |
| Collection | HTTP and OTLP/HTTP Logs (JSON + protobuf) ingestion to Kafka | `collection` |
| Dataset | `.log`, `.txt`, `.csv` upload, LogHub catalog/import metadata and synthetic generation | `dataset` |
| Preprocessing | Normalize raw Kafka events | `preprocessing` |
| Parser | Baseline template extraction | `parser` |
| Intelligence | Persist parsed events and error anomalies | `intelligence` |
| Analytics | Overview, logs, templates and anomalies | `analytics` |
| Identity | Ingestion key generation | `identity` |

## API endpoints

- `POST /v1/auth/register` / `POST /v1/auth/login` — tenant registration and JWT login.
- `GET /v1/auth/me` — current account.
- `POST /v1/applications` / `GET /v1/applications` — tenant-scoped application management (admin creates).
- `POST /v1/api-keys` / `GET /v1/api-keys` / `DELETE /v1/api-keys/{id}` — generate, list metadata, and revoke ingestion keys (admin only).
- `POST /v1/users` — provision a tenant member (admin only).
- `POST /v1/logs` — JSON batch ingestion (requires a generated `x-api-key`).
- `POST /v1/otlp/logs` — standard OTLP/HTTP Logs JSON or protobuf payloads; collector-to-Collection calls use `x-logiq-otlp-token` and require `logiq.tenant_id` resource attribute. API-key ingestion remains supported.
- `GET /v1/datasets/catalog/loghub` — curated public LogHub catalog with upstream Zenodo download links.
- `POST /v1/datasets/upload` — set `source_type=loghub` and `source_reference` to preserve upstream dataset provenance after downloading/extracting the raw log file.
- `POST /v1/datasets/upload` — multipart file upload (requires a generated `x-api-key`).
- `POST /v1/datasets/synthetic?count=1000&services=4` — synthetic data generation.
- `GET /v1/analytics/overview`
- `GET /v1/logs?service=api&severity=ERROR&q=timeout`
- `GET /v1/templates`
- `GET /v1/anomalies`
- `GET /v1/datasets` / `GET /v1/datasets/{dataset_id}` — tenant-scoped dataset metadata.

## Tests

```powershell
python -m pip install -r requirements.txt pytest
python -m pytest -q
```

## Current implementation status and production gaps

- The continuously running Kafka workers are implemented for raw -> preprocessed -> parsed -> persisted processing, with bounded retries, DLQ routing, manual commits and idempotent event persistence.
- The parser benchmark supports deterministic `first_n`, `random`, and severity-stratified sampling; `runtime_first`, `quality_constrained`, and `multi_objective` selection policies; and optional exact-template accuracy when aligned ground-truth labels are supplied.
- The baseline token-masking parser is available. Drain3 is an optional adapter and is only benchmarked if the package is installed in the image. PIPLUP remains intentionally unavailable until its actual API and license are verified.
- Statistical detector functions now include rolling means, z-score outliers, IQR outliers, rare-template identification and prior-window error spikes. They are unit-tested but are not yet connected to a scheduled aggregation pipeline or dashboard.
- PostgreSQL ownership is partially separated: Identity and Dataset have dedicated databases and roles; Collection, Preprocessing, Parser, Intelligence and Analytics still use `logiq_core`.
- Identity service now supports tenant registration, password login, signed JWT sessions, admin/member roles, tenant-scoped applications, hashed ingestion API keys, expiry and revocation. The frontend has a basic register/sign-in flow.
- Collection now decodes standard OTLP/HTTP Logs JSON and protobuf, including resource/scope attributes, timestamps, severity and trace/span IDs. OTLP/gRPC terminates at the Collector, which forwards logs over OTLP/HTTP protobuf to Collection; OTLP metrics and traces remain on the Collector debug pipeline. This is not a full OTLP/gRPC server inside Collection.
- Raw `.log`, `.txt`, and `.csv` uploads are stored as immutable MinIO objects under tenant-scoped keys before Kafka publishing. Dataset metadata records byte size, SHA-256 digest, content type and object key; API responses do not expose the internal object key. Publishing is chunked and flushes every 500 events. Uploads are validated and hashed in bounded chunks, then streamed from the multipart spool file to MinIO; the default maximum is 5 GiB (`DATASET_MAX_UPLOAD_BYTES`).
- OTel Collector forwards OTLP logs to Collection and retains a rotated local telemetry file; its retry queue is bounded in-memory, not a durable disk queue. Services still need SDK instrumentation or a container log receiver to emit their own telemetry automatically.
- Dashboard pages beyond the overview are not yet implemented; dashboard is a connected shell with live analytics and recent log/anomaly data.
- Tenant filters are enforced in collection, dataset and analytics paths. Identity and Dataset now have separate PostgreSQL databases; remaining core services still share `logiq_core`. TLS, production secrets management, rate limiting, retention scheduling, audit trail and load-tested throughput claims remain open.
- A full Docker deployment and end-to-end integration run have not yet been verified in this environment.

## Security note

Change all development credentials before sharing or deploying. Never send real secrets or sensitive production logs to this local development stack.

## Continuous processing workers (development increment)

The raw -> preprocessed -> parsed -> persisted pipeline now has dedicated long-running Kafka worker containers:

- `preprocessing-worker`: validates messages, extracts timestamp/severity, preserves `raw_message`, and emits `logs.preprocessed`.
- `parser-worker`: extracts templates and parameters and emits `logs.parsed`.
- `intelligence-worker`: idempotently persists parsed events and error-event anomalies.

Workers use manual Kafka offset commits. A message is acknowledged only after its next-stage publish/persistence succeeds. After bounded retries, failed records are written to a stage-specific dead-letter topic (for example `logs.raw.dlq`) before the offset is committed. Delivery is at-least-once; consumers and persistence operations therefore use idempotency keys.

The parser service also exposes:

- `GET /v1/parsers` — lists adapters that are actually available in the running image.
- `POST /v1/benchmarks` — benchmarks the same deterministic sample with fresh parser instances and reports runtime, throughput, peak traced memory, template count and failures. It explicitly does not claim parsing quality without ground-truth labels.

Run the test suite with `pytest`. This increment does not yet complete the full specification: service-owned databases, Drain3 installation and evaluation, PIPLUP verification, full anomaly algorithms, and end-to-end Docker execution remain open work.

## Adaptive parser benchmarking (development increment 3)

`POST /v1/benchmarks` accepts `lines`, `seed`, `sample_size`, `sampling_strategy`, `selection_policy`, `min_quality`, and optional `ground_truth_templates`. Example request:

```json
{
  "lines": ["INFO request 10 completed", "ERROR request 11 failed"],
  "seed": 42,
  "sample_size": 2,
  "sampling_strategy": "stratified",
  "selection_policy": "runtime_first"
}
```

For `quality_constrained` or `multi_objective`, provide `ground_truth_templates` with one expected template per input line. The benchmark selects on the same sampled indices for every parser. It does not treat template count as a quality metric.

Statistical detector primitives live in `services/intelligence/detectors.py`. They are pure functions with unit tests; they do not yet create persisted anomaly records automatically.


## Identity, authentication and tenant isolation (development increment 5)

The Identity service now provides: 

- `POST /v1/auth/register`: create a tenant and its first admin account.
- `POST /v1/auth/login`: verify a password and issue a signed HS256 JWT (one-hour default lifetime).
- `GET /v1/auth/me`: validate the session against the current user record.
- `POST /v1/users`: admin-provision a member in the same tenant.
- `POST/GET /v1/applications`: create/list tenant-owned applications.
- `POST/GET /v1/api-keys` and `DELETE /v1/api-keys/{id}`: create, list metadata for, and revoke API keys. Raw key material is returned only once; only a SHA-256 digest (with optional pepper) is stored.

Passwords use salted PBKDF2-HMAC-SHA256 (310,000 iterations) and a minimum 12-character policy. JWT signatures use HMAC-SHA256 and are checked for issuer, expiry and signature. Analytics endpoints require a valid user JWT. Collection and dataset endpoints require a non-revoked, non-expired ingestion key. Tenant IDs are derived from the authenticated identity/key rather than trusted from request payloads. Analytics queries and dataset listing are tenant-filtered. Application-bound keys cannot submit logs under another application.

### First-time setup (PowerShell)

Copy `.env.example` to `.env`, then replace `LOGIQ_JWT_SECRET` and `LOGIQ_API_KEY_PEPPER` with different, unique random secrets before using real data. Restart the stack after changing them. Changing the pepper invalidates previously issued API keys; issue replacement keys. The default development fallback secret is not suitable for deployment.

Register an admin account through the gateway:

```powershell
$account = @{ email = 'admin@example.com'; password = 'use-a-long-unique-password'; tenant_name = 'Engineering' } | ConvertTo-Json
$session = Invoke-RestMethod -Method Post -Uri http://localhost:8080/v1/auth/register -ContentType 'application/json' -Body $account
$jwt = $session.access_token
$headers = @{ Authorization = "Bearer $jwt" }

# Optional: register an application, then bind an API key to its returned id.
$appBody = @{ name = 'RetargetIQ'; environment = 'development' } | ConvertTo-Json
$app = Invoke-RestMethod -Method Post -Uri http://localhost:8080/v1/applications -Headers $headers -ContentType 'application/json' -Body $appBody
$keyBody = @{ label = 'RetargetIQ ingestion'; application_id = $app.id } | ConvertTo-Json
$key = Invoke-RestMethod -Method Post -Uri http://localhost:8080/v1/api-keys -Headers $headers -ContentType 'application/json' -Body $keyBody

# Send logs with the returned key. Store it securely; it is not retrievable later.
$logBody = @{ logs = @(@{ message = 'ERROR inventory database connection failed'; service_name = 'inventory'; severity = 'ERROR' }) } | ConvertTo-Json -Depth 6
Invoke-RestMethod -Method Post -Uri http://localhost:8080/v1/logs -Headers @{ 'x-api-key' = $key.api_key } -ContentType 'application/json' -Body $logBody
```

The dashboard now shows a sign-in/create-workspace screen and sends its JWT with analytics requests. It stores the session token in browser local storage; for production, replace this development approach with secure, httpOnly cookie sessions and CSRF protections. Account recovery, email verification, refresh tokens, audit logging, invitations, rate limiting and TLS are not implemented.

Security implementation tests cover password hashing, password policy, JWT validation/expiry/tampering and API-key material. These are unit tests, not a substitute for live database, gateway and multi-tenant integration tests.


## Durable raw dataset storage (development increment 6)

The dataset service now writes the exact uploaded bytes to MinIO before publishing normalized log events to Kafka. The object key is tenant-scoped (`tenants/{tenant_id}/datasets/{dataset_id}/raw`) and remains internal; dataset metadata stores its SHA-256 checksum, byte size and content type. The dataset list/detail APIs expose metadata only. Kafka publishing is flushed in bounded batches of 500 records, and a failed publish marks the dataset `failed` while retaining the original artifact for later recovery.

MinIO is configured through `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` and `MINIO_BUCKET` in `.env`. The dataset service waits for the MinIO container to start and creates the bucket on first upload. Do not reuse development credentials in deployment. Synthetic data generation also publishes in bounded batches, but generated synthetic events are not stored as raw MinIO artifacts in this increment.

The upload path now streams validation, hashing and MinIO storage in bounded chunks. The publisher verifies the immutable object checksum, samples parsers in bounded memory, and resumes batches using a persisted byte-offset cursor. A real MinIO/Kafka end-to-end run and throughput profiling on multi-gigabyte files remain pending. Dataset deletion, signed download URLs, retention cleanup, MinIO integration tests and end-to-end Kafka recovery are still pending.

## Dataset processing lifecycle (development increment 7)

Dataset records now track `queued`, `processing`, `completed`, and `failed` states, expected line count, persisted event count, failed-message count, start/completion timestamps, and a sanitized failure summary. The intelligence persistence worker publishes a `log_persisted` Kafka notification after its core database transaction. A Dataset-owned progress consumer deduplicates these notifications and updates `processed_count`; stage messages that exhaust retries publish a failure notification after entering the DLQ. Dataset state is no longer updated by direct SQL from Intelligence or generic workers.

New endpoints:

- `GET /v1/datasets/{dataset_id}/progress` — tenant-scoped status, processed/expected counts, percentage and timestamps.
- `POST /v1/datasets/{dataset_id}/retry` — replay a failed upload from its preserved MinIO artifact after verifying its SHA-256 checksum.

Upload line events now use deterministic event IDs derived from dataset ID and source line number. Replaying a partially processed upload therefore reuses the same IDs; already persisted rows are ignored idempotently and only missing lines increase the progress counter. Retry is intentionally limited to failed datasets with a preserved raw artifact. Synthetic datasets and failed uploads without a MinIO object cannot use this replay endpoint.

Multipart uploads are spooled by the ASGI server and streamed to MinIO; set `DATASET_MAX_UPLOAD_BYTES` to tune the byte limit. Progress completion is based on events successfully persisted by the final intelligence worker, not merely messages accepted by Kafka. A real Kafka/PostgreSQL/MinIO end-to-end lifecycle test and Docker runtime verification are still required.


## Analytics & query APIs (increment 8)

All analytics endpoints require a workspace JWT and scope every query to the
authenticated tenant. Log search supports service, application, severity,
template, text, and timestamp filters with total counts and pagination.

- `GET /v1/logs?severity=ERROR&start_time=2026-01-01T00:00:00Z&limit=100&offset=0`
- `GET /v1/analytics/timeseries?hours=24&interval=hour`
- `GET /v1/analytics/severity-distribution?hours=24`
- `GET /v1/analytics/errors/by-service?hours=24`
- `GET /v1/analytics/overview?start_time=...&end_time=...`
- `GET /v1/anomalies?kind=error_event&limit=100&offset=0`
- `GET /v1/templates?service=api&limit=100&offset=0`

Timestamp filters accept ISO-8601 values. `start_time` must not be later than
`end_time`. Time-series interval is restricted to `minute`, `hour`, or `day`.
Indexes are created for common tenant/time and tenant/dimension query patterns.

## Functional observability dashboard (development increment 9)

The React dashboard now has working navigation and API-backed pages for Overview, Live Log Explorer, Applications, Datasets, Templates, Anomalies, Service Health and Settings. The overview uses the analytics time-series and severity-distribution APIs; log search supports text, severity and service filters with pagination; applications can be created; template and anomaly records are browsable; and Settings supports one-time ingestion-key creation, listing and revocation for admins.

Dataset upload, synthetic generation, listing and failed-dataset replay use the dataset service's API-key authentication. The dashboard stores the one-time ingestion secret in `sessionStorage` for the current browser tab only (not `localStorage`), and users can remove it from Settings. Create an ingestion key in Settings before using dataset operations. Dataset routes are authenticated by API key; analytics routes use the JWT session.

The Service Health page deliberately distinguishes the gateway's checked `/health` endpoint from services that are only known to be routed. It does not present configured routes as proof that containers or Kafka workers are healthy. The frontend dependency installation/build could not be completed in the current environment because `npm install` timed out; Python tests do not validate the TypeScript bundle. Docker and live browser/API integration remain to be verified.


## Versioned database migrations (development increment 10)

Schema creation is now managed by Alembic rather than application startup hooks.
The `migrate` Compose service runs `alembic upgrade head` after PostgreSQL is
healthy; API services and workers wait for that one-shot migration job to exit
successfully before starting. This prevents multiple replicas racing to create
or alter the same tables during startup. The initial migration creates the
current development schema and includes additive `IF NOT EXISTS` changes to
adopt databases previously bootstrapped by the development `ensure_tables()`
helper.

For local development outside Compose, run the migration command before
starting any service:

```powershell
$env:DATABASE_URL = 'postgresql+psycopg://logiq_core:logiq-core-dev-only@localhost:5432/logiq_core'
alembic upgrade head
$env:DATABASE_URL = 'postgresql+psycopg://logiq_identity:logiq-identity-dev-only@localhost:5432/logiq_identity'
alembic -c alembic_identity.ini upgrade head
```

To inspect the current migration revision, run `alembic current`; to see
revision history, run `alembic history`. A downgrade of the initial migration
drops the LogIQ tables and is destructive. Back up the database before any
manual downgrade or migration operation.

Increment 11 introduced a separate Identity database. Increment 12 adds a separate Dataset database and its own Alembic migration stream; the remaining core services still share `logiq_core`.


## Database ownership — Increment 11

The development Compose topology provisions three separate PostgreSQL databases:

- `logiq_identity` is owned by Identity and uses the `logiq_identity` role. User, tenant, application and API-key operations run against this database.
- `logiq_dataset` is owned by Dataset and uses the `logiq_dataset` role. Dataset metadata, processing counters and progress-event idempotency records live here.
- `logiq_core` remains shared by Collection, Preprocessing, Parser, Intelligence and Analytics for log events, templates and anomalies.

Each database has a migration gate before its owning service starts. Dataset has a dedicated Alembic script location and migration service. The historical shared migration stream now drops the old `datasets` table from `logiq_core` after creating it in the initial revision. Existing local volumes require manual provisioning of the new `logiq_dataset` role/database because PostgreSQL init scripts run only on first initialization.

The bootstrap passwords in `infrastructure/postgres/init-databases.sh` are development-only. Change them, the matching Compose connection strings, and `POSTGRES_ADMIN_PASSWORD` together before using the stack outside a local development environment. PostgreSQL initialization scripts run only when the data volume is first created. For an existing local volume, back up data and recreate the volume or provision the roles/databases manually; do not delete a volume containing data you need.


## Dataset service database isolation (development increment 12)

Dataset metadata now lives in the dedicated `logiq_dataset` database, owned by the `logiq_dataset` PostgreSQL role. `dataset` and `dataset-progress-worker` connect to this database; other services do not receive its connection string. A separate `migrate-dataset` one-shot Compose service applies `migrations_dataset/` before Dataset API and progress-worker startup. The shared core migration removes the legacy `datasets` table from `logiq_core`.

Cross-service progress is event-driven: after Intelligence commits a parsed log event to `logiq_core`, it publishes a `log_persisted` message to `logs.persisted`. The Dataset progress worker consumes that topic and updates Dataset-owned counters. When a processing stage exhausts retries, the generic worker first routes the original record to its DLQ and then publishes a `dataset_processing_failed` notification. The Dataset worker deduplicates both outcomes using `dataset_progress_events.event_id`; the Intelligence and generic worker code no longer executes SQL against the Dataset database.

Each dataset has a `processing_attempt`. Retry increments the attempt, clears the previous attempt's progress ledger, and replays the preserved MinIO artifact. Notifications from older attempts are ignored, preventing delayed Kafka messages from corrupting current retry progress. Duplicate persisted-log notifications are safe because the Dataset progress ledger is idempotent.

For local development outside Compose, run the Dataset migration with:

```powershell
$env:DATASET_DATABASE_URL = 'postgresql+psycopg://logiq_dataset:logiq-dataset-dev-only@localhost:5432/logiq_dataset'
alembic -c alembic_dataset.ini upgrade head
```

The database bootstrap script provisions `logiq_dataset` only when the PostgreSQL data volume is first initialized. On an existing development volume, set `$env:DATASET_DB_PASSWORD` to the password in your `DATASET_DATABASE_URL`, then run `./scripts/provision-dataset-db.ps1` from PowerShell before starting the new Dataset service. This script only creates the missing role/database and does not remove existing data. Do not remove a volume containing data you need. The Kafka-to-PostgreSQL progress path has unit/architecture coverage but still requires a live Compose integration test; Docker runtime remains unverified in this environment.

## Current source audit

See [docs/IMPLEMENTATION_AUDIT.md](docs/IMPLEMENTATION_AUDIT.md) for the source-backed requirement matrix, verified checks, critical defects, unverified runtime claims, and the prioritized remediation sequence. The audit distinguishes implemented, partial, missing, and unverified capabilities.


### Dataset publication reliability (Increment 14)

Uploaded datasets are now persisted as MinIO artifacts plus durable Dataset-owned publication jobs. The API returns after storing the artifact and job; `dataset-publisher-worker` publishes bounded batches to Kafka and checkpoints the next source line. If the worker stops, it resumes from the last committed cursor. A crash after Kafka acknowledgement but before the cursor commit can replay a batch, so deterministic per-line event IDs are used and the Intelligence persistence consumer deduplicates by `event_id`. Run one publisher-worker replica unless distributed lease ownership is added.

Kafka producers now serialize string message keys as UTF-8 bytes, fixing the Collection API's application-ID key path. Dataset retry resets the durable publication job and replays the verified raw artifact.


## Latest development increment

- [Increment 15 — Adaptive parser integration](docs/INCREMENT_15.md)


## Recent implementation increments

- [Increment 14: durable dataset publication](docs/INCREMENT_14.md)
- [Increment 15: adaptive parser integration](docs/INCREMENT_15.md)
- [Increment 16: intelligence and anomaly lifecycle](docs/INCREMENT_16.md)
- [Implementation audit](docs/IMPLEMENTATION_AUDIT.md)
- [Increment 17: Analytics and query engine](docs/INCREMENT_17.md)\n

## Increment 18 — Independent Self-Observability

See [Increment 18 implementation notes](docs/INCREMENT_18.md) for JSON logs, API/worker Prometheus metrics, Collection outage alerting, Grafana panels, OTLP collector persistence, and smoke-test scripts.


## OpenTelemetry Logs and public LogHub datasets (development increment 19)

The Collection service now accepts the standard OTLP/HTTP Logs request shape in JSON and protobuf (`application/x-protobuf`). It flattens `resourceLogs` / `scopeLogs` / `logRecords` into LogIQ events, retaining service/environment resource attributes, log attributes, event timestamp, severity, trace ID and span ID. The OTel Collector's logs pipeline forwards protobuf over HTTP to `/v1/otlp/logs`; metrics and traces are not yet ingested into the LogIQ event pipeline. Collector-to-Collection requests use `LOGIQ_OTLP_INGEST_TOKEN` and must carry `logiq.tenant_id` as a resource attribute. Configure the same secret in `.env` for local Compose use and replace the development fallback before deployment.

The Dataset API exposes `GET /v1/datasets/catalog/loghub` with official LogHub metadata and Zenodo links. To import, download the upstream archive, extract the raw `.log`/`.txt`/`.csv`, and upload it with `source_type=loghub` plus `source_reference` matching a catalog ID. Provenance is stored with dataset metadata. This is a catalog-assisted manual import, not an automated archive downloader; the default upload cap is 5 GiB, configurable through `DATASET_MAX_UPLOAD_BYTES`; the importer streams the raw file rather than loading it all into process memory. Review LogHub's research/academic-use terms and citation guidance at https://github.com/logpai/loghub before use.

See [Increment 19 notes](docs/INCREMENT_19.md) and [implementation audit](docs/IMPLEMENTATION_AUDIT.md).


## Streaming dataset importer (development increment 20)

See [Increment 20 implementation notes](docs/INCREMENT_20.md) for bounded-memory upload validation, MinIO streaming, parser sampling and resumable byte-offset publishing. Default upload limit: 5 GiB (`DATASET_MAX_UPLOAD_BYTES`).


## Dataset publisher reliability (development increment 21)

See [Increment 21 implementation notes](docs/INCREMENT_21.md) for Kafka per-record acknowledgements before cursor commits, bounded batch configuration and atomic retry reset.


## Dataset publisher measurements and cancellation (development increment 22)

The Dataset progress endpoint now exposes measured publisher-stage bytes, elapsed batch time, last-batch duration and derived average bytes/second. `POST /v1/datasets/{dataset_id}/cancel` requests cooperative cancellation at a batch boundary while preserving the raw MinIO artifact. See [Increment 22 notes](docs/INCREMENT_22.md) for exact measurement scope, recovery behavior and runtime limitations.
- [Increment 22: publisher throughput telemetry and cooperative cancellation](docs/INCREMENT_22.md)

### Dataset artifact deletion

`DELETE /v1/datasets/{dataset_id}` requests tenant-scoped deletion. The Dataset API records a durable tombstone; the `dataset-deletion-worker` removes the MinIO raw artifact and only then marks the retained dataset record `deleted`. Failed object deletions are retried. This currently deletes the raw artifact only: already-published logs and derived records in other services are not erased by this endpoint.

### Dataset deletion lifecycle

Dataset deletion is asynchronous. `DELETE /v1/datasets/{dataset_id}` requests deletion; the Dataset worker removes the raw MinIO object and writes a durable outbox command. Intelligence removes dataset-scoped persisted log events and recomputes aggregate template statistics, then acknowledges. Dataset marks the tombstone `deleted` only after the acknowledgement. Poll `GET /v1/datasets/{dataset_id}` while the state is `deleting`. Aggregate anomaly provenance is not yet complete; see `docs/INCREMENT_24.md`.
