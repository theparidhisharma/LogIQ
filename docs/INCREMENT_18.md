# Increment 18 — Independent Self-Observability

## Objective

Make LogIQ's monitoring plane able to observe API and worker availability without relying on the Collection service to report its own failure.

## Implemented

- Added shared JSON log formatting with UTC timestamp, level, logger, service, message, exception details, and request ID when present.
- Added request-ID propagation: accept `x-request-id` or generate one, return it in the response, and attach it to log records through async-safe context.
- Improved API Prometheus instrumentation. HTTP metrics use FastAPI route templates rather than raw URL paths to avoid unbounded path-label cardinality; exceptions are counted as 500s.
- Added worker metrics endpoints to Kafka stage workers and the dataset publisher: processed messages/jobs, retries, failures/DLQ, processing duration (Kafka stage workers), and last heartbeat.
- Prometheus now scrapes all eight API services (including the gateway) and five worker processes. Static target names were checked against Compose service names.
- Added alert rules for Collection scrape failure, worker metrics endpoint failure, and sustained API 5xx rate. Prometheus evaluates these rules independently of Collection.
- Expanded the Grafana dashboard with API/worker availability, request rate, p95 latency, worker throughput, retries, and failures.
- Exposed OTLP gRPC/HTTP receiver ports and changed the Collector from debug-only export to debug plus a rotated, persistent file sink for OTLP logs, metrics, and traces.
- Added shell and PowerShell smoke checks, plus an opt-in outage simulation script that stops Collection briefly and verifies Prometheus observes `up=0` before restoring it.

## Independence model

Prometheus is a separate Compose service. It scrapes `collection:8000/metrics` directly over the Compose network. If Collection is stopped or crashes, Prometheus continues running and its target becomes `up=0`; the `LogIQCollectionUnavailable` rule then fires after 30 seconds. This check does not call Collection's logging or ingestion pipeline. Worker metrics are also exposed directly by worker processes, not sent through Collection.

## Verification

- Python compilation: passed.
- Full unit suite: **81 passed**. The isolated environment lacks `kafka-python`; tests were run with a temporary import-only Kafka shim. This validates unit behavior, not broker connectivity.
- Compose YAML parsed: 24 services.
- Prometheus, alert, OTEL YAML and Grafana dashboard JSON parsed successfully.
- All 13 Prometheus scrape targets map to services in Compose.
- Grafana dashboard contains 7 panels.
- ZIP archive integrity checked after packaging.

## Important limitations / not verified

- Docker Compose was not started in this environment. The outage simulation, live scrape, alert firing, Grafana rendering, Kafka worker metrics, and OTLP ingestion/file rotation were not runtime-tested.
- Alert rules are configured, but no Alertmanager or email/Slack notification receiver is configured. Rules can be inspected in Prometheus; delivery is a separate integration.
- Existing Python services emit structured JSON to stdout. They are **not yet automatically exporting their own logs/metrics/traces to OTLP**. The Collector accepts OTLP from instrumented clients and persists received telemetry, but it does not automatically tail Docker stdout logs.
- The persistent Collector file sink is not a substitute for a replicated telemetry backend or a tested durable queue. Disk sizing and retention need operational validation.
- Worker metrics are process-local and reset on restart. The scrape target's `up` is the primary process availability signal; heartbeat age is diagnostic and should not be treated as a definitive liveness check during idle periods.
- This increment does not add Kafka consumer lag, Redis queue depth, PostgreSQL pool saturation, MinIO health metrics, or host/container CPU and memory exporters.

## Run locally

```bash
docker compose up --build -d
# PowerShell
./scripts/check-self-observability.ps1
# Bash
./scripts/check-self-observability.sh
# Optional, briefly stops and restores Collection:
./scripts/simulate-collection-failure.sh
```

Collection is exposed on host port 8001 for local checks. Prometheus is at `http://localhost:9090`, Grafana at `http://localhost:3000`, and OTLP receivers at ports 4317/4318.
