# LogIQ — Increment 19: OTLP Logs and LogHub Dataset Catalog

## Delivered

### 1. Standard OTLP/HTTP Logs ingestion

- `POST /v1/otlp/logs` accepts `application/json` OTLP `ExportLogsServiceRequest` payloads and `application/x-protobuf` payloads.
- Protobuf decoding uses the official generated messages supplied by `opentelemetry-proto`.
- Flattens `resourceLogs`, `scopeLogs`, and `logRecords` into the LogIQ event envelope.
- Maps resource and record attributes, service name, environment, timestamp, severity, trace ID, span ID, scope name/version, and body.
- Correctly maps OTLP severity ranges and protobuf enum names.
- Existing API-key authenticated JSON ingestion remains supported. The internal Collector route uses `LOGIQ_OTLP_INGEST_TOKEN`, requires `logiq.tenant_id`, validates the tenant against Identity, and validates a supplied `logiq.application_id` against that tenant.
- Collector logs pipeline forwards protobuf over HTTP to `collection:8000/v1/otlp/logs`, with bounded in-memory retry queue. The Collector still keeps a rotated local telemetry file as a separate copy.
- Metrics and traces received by the Collector remain on its debug pipeline; they are not yet ingested into LogIQ's log event/query model.

### 2. LogHub catalog and provenance

- Added `GET /v1/datasets/catalog/loghub` with curated entries, official Zenodo download URLs, line counts, raw sizes and labeled/unlabeled metadata.
- Dataset upload accepts `source_type=loghub` and a catalog `source_reference`.
- Added Dataset DB migration `dataset_0004` for `source_reference` and `source_metadata`.
- Dataset list/detail responses include the source provenance fields.
- Import is catalog-assisted/manual: download from the upstream link, extract the raw `.log`, `.txt` or `.csv`, then upload and set `source_type=loghub` and `source_reference=<catalog ID>`.

## Configuration

Set `LOGIQ_OTLP_INGEST_TOKEN` in `.env` to a unique random secret before running the Collector. The Compose fallback exists for local development only and must not be used in a shared or deployed environment.

Instrumented applications must attach a trusted `logiq.tenant_id` resource attribute. They may attach `logiq.application_id` when the application is registered in that tenant. Example resource attributes:

```text
service.name=checkout
deployment.environment.name=staging
logiq.tenant_id=<tenant UUID>
logiq.application_id=<registered application UUID>
```

The Collector listens on OTLP gRPC `4317` and OTLP HTTP `4318`; it exports logs to Collection over OTLP/HTTP protobuf. Collection itself is not a gRPC OTLP server.

## Validation

- 88 Python tests passed using a temporary import-only Kafka shim. The shim only satisfies imports; it does not simulate Kafka broker behavior.
- Added tests for OTLP JSON flattening, protobuf decoding, trace/span ID conversion, severity mapping, authenticated internal publishing and LogHub catalog metadata.
- Python `compileall` passed.
- Compose, Collector, Prometheus and alert YAML parsing passed.
- Grafana dashboard JSON parsing passed.
- Dataset Alembic offline SQL generation passed through `dataset_0004`.
- Live Docker Compose, Collector-to-Collection transport, Kafka broker publishing, and full dataset upload processing were not run in this environment.

## Explicit limitations

- LogHub is not automatically downloaded or decompressed by LogIQ. The catalog links to upstream downloads; users manually extract the raw log and upload it.
- Dataset upload remains capped at 50 MiB. Large corpora such as HDFS_v1 and BGL need a future streaming importer and should not be presented as directly uploadable today.
- OTLP metrics and traces are not yet persisted or queryable by LogIQ.
- The Collector retry queue is bounded in-memory, not a durable disk-backed queue. The rotated file exporter is a local telemetry copy, not an exactly-once delivery mechanism.
- Applications must be instrumented to send telemetry; automatic container stdout collection and service-wide SDK instrumentation remain future work.
- The shared OTLP token must be protected. Tenant resource attributes are only trustworthy when emitted by trusted instrumented workloads through the controlled Collector path.

## Upstream dataset reference

LogHub's catalog, dataset descriptions, size/line metadata, Zenodo download links, research-use note and citation guidance are published at:

- https://github.com/logpai/loghub/blob/master/README.md
- LogHub papers: https://arxiv.org/abs/2008.06448 and https://arxiv.org/abs/2308.10828
