# Increment 17 — Analytics and Query Engine

## Delivered

### Log search
- Added filters for service, severity, application, environment, template, trace ID, request ID, source type and dataset ID.
- Added bounded query text input and a maximum page size of 500.
- Added stable keyset pagination using `(timestamp, event_id)` cursor ordering.
- Preserved offset pagination for compatibility, with a bounded offset.
- Added optional total-count calculation so cursor clients can avoid an expensive count query.
- Added event detail retrieval scoped by tenant.
- Gateway now forwards `/v1/logs/{event_id}` to Analytics while retaining POST `/v1/logs` ingestion routing to Collection.

### Template analytics
- Added template detail retrieval with per-parameter occurrence counts, distinct-value counts and up to three sample values.
- Corrected template trends: hourly event volume and error counts now come from `log_events`; newly discovered templates are counted by `first_seen`; distinct templates are measured from actual events.
- Added service summary analytics with event, warning and error counts, application counts, last-seen time and calculated error rate.

### Query performance
- Added core migration `0004_analytics_query_indexes` with tenant-first composite indexes for cursor search, service/application/template filtering, trace/request lookup and dataset lookup.
- Added tenant-scoped template frequency/service indexes.
- All SQL values remain bound parameters; interpolated SQL fragments are selected from fixed allow-lists or internal fixed column names.

## Verification
- Full Python suite: 78 passed in 0.72 seconds using a temporary Kafka import shim. This does not verify live broker behavior.
- Python compilation: passed.
- Compose YAML: parsed successfully; 24 services.
- Analytics FastAPI app import and OpenAPI generation: passed; 19 routes and 15 documented paths.
- Core, Identity and Dataset Alembic offline SQL generation: passed. Core and Identity use the existing core migration stream; this increment adds only a Core migration.
- Docker and live PostgreSQL query plans were not available, so index effectiveness and SQL execution plans are not yet measured.

## Architecture note
Dataset parser benchmark records remain owned by the Dataset database and are retrieved through Dataset APIs. Analytics does not directly query the Dataset database. This preserves the service ownership boundary.

## Remaining limitations
- Full-text `ILIKE '%term%'` search is not yet backed by trigram/full-text indexes; the new indexes optimize tenant/time and common exact filters, not arbitrary substring search.
- Offset pagination remains available for compatibility but cursor pagination is recommended for deep pages.
- Template parameter samples are returned as values from stored parameters; production deployments should apply configured redaction before persistence and consider suppressing samples for sensitive keys.
- Benchmark comparison and dataset processing reports remain in Dataset APIs, not cross-read by Analytics.
- Query plans, real database performance and multi-tenant integration need live PostgreSQL verification.
