"""Persist parsed events and run evidence-backed template/statistical intelligence."""
import json
import logging
import math
from datetime import datetime, timezone

from sqlalchemy import text

from shared.common import db
from shared.worker import run_stage
from services.intelligence.detectors import (
    error_burst_triggered,
    latest_count_outliers,
    rare_template_ids,
    severity_distribution_shift,
)

logging.basicConfig(level=logging.INFO)


def _record_anomaly(conn, *, dedupe_key, kind, severity, service, description, sample, increment=1):
    conn.execute(text("""INSERT INTO anomalies(
            tenant_id,kind,severity,service_name,description,sample,dedupe_key,
            status,first_seen,last_seen,occurrence_count,rule_version)
        VALUES(:tenant,:kind,:severity,:service,:description,CAST(:sample AS jsonb),:dedupe_key,
               'open',now(),now(),1,'1')
        ON CONFLICT(dedupe_key) WHERE dedupe_key IS NOT NULL DO UPDATE SET
            last_seen=now(), occurrence_count=anomalies.occurrence_count+:increment,
            sample=EXCLUDED.sample, description=EXCLUDED.description
        """), {
        "tenant": sample.get("tenant_id", "default"), "kind": kind, "severity": severity,
        "service": service, "description": description, "sample": json.dumps(sample),
        "dedupe_key": dedupe_key, "increment": increment,
    })


def _detect_time_series(conn, event):
    """Inspect twelve five-minute event-time buckets for a tenant/service."""
    tenant = event.get("tenant_id") or "default"
    service = event.get("service_name") or "unknown"
    try:
        timestamp = datetime.fromisoformat(str(event.get("timestamp") or "").replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        timestamp = datetime.now(timezone.utc)
    current_epoch = math.floor(timestamp.timestamp() / 300) * 300
    start_epoch, end_epoch = current_epoch - 11 * 300, current_epoch + 300
    rows = conn.execute(text("""SELECT
          floor(extract(epoch FROM timestamp)/300)::bigint AS bucket,
          count(*) AS total,
          count(*) FILTER (WHERE upper(coalesce(severity,'')) IN ('ERROR','FATAL')) AS errors
        FROM log_events
        WHERE tenant_id=:tenant AND service_name=:service
          AND timestamp >= to_timestamp(:start) AND timestamp < to_timestamp(:end)
        GROUP BY 1 ORDER BY 1"""), {
            "tenant": tenant, "service": service,
            "start": start_epoch, "end": end_epoch,
        }).mappings().all()
    by_bucket = {int(r["bucket"]): r for r in rows}
    buckets = [int((start_epoch + i * 300) // 300) for i in range(12)]
    totals = [int(by_bucket.get(b, {}).get("total", 0)) for b in buckets]
    errors = [int(by_bucket.get(b, {}).get("errors", 0)) for b in buckets]
    bucket_id = int(current_epoch // 300)

    for metric, values in (("log_volume", totals), ("error_volume", errors)):
        reasons = latest_count_outliers(values)
        if reasons:
            baseline = sum(values[:-1]) / max(1, len(values) - 1)
            kind = "log_volume_spike" if metric == "log_volume" else "error_frequency_spike"
            _record_anomaly(conn, increment=0,
                dedupe_key=f"{kind}:{tenant}:{service}:{bucket_id}",
                kind=kind, severity="high" if metric == "error_volume" else "medium",
                service=service,
                description=(f"{metric.replace('_', ' ')} reached {values[-1]} in the current "
                             f"five-minute bucket; prior-bucket mean was {baseline:.2f}."),
                sample={"tenant_id": tenant, "service_name": service, "metric": metric,
                        "current_5m": values[-1], "prior_55m_buckets": values[:-1],
                        "prior_mean": baseline, "detectors": reasons, "bucket_epoch": bucket_id})

    # Keep the simple volume floor to avoid flagging tiny but statistically unusual counts.
    recent_errors, prior_errors = errors[-1], sum(errors[:-1])
    if error_burst_triggered(recent_errors, prior_errors):
        _record_anomaly(conn, increment=0,
            dedupe_key=f"error_burst:{tenant}:{service}:{bucket_id}",
            kind="error_frequency_spike", severity="high", service=service,
            description=f"{recent_errors} ERROR/FATAL events in 5 minutes; preceding 55-minute baseline was {prior_errors}.",
            sample={"tenant_id": tenant, "service_name": service,
                    "recent_5m": recent_errors, "prior_55m": prior_errors,
                    "threshold_multiplier": 3, "bucket_epoch": bucket_id})

    severity_rows = conn.execute(text("""SELECT
          CASE WHEN timestamp >= to_timestamp(:current_start) THEN 'recent' ELSE 'baseline' END AS period,
          upper(coalesce(severity,'UNKNOWN')) AS severity, count(*) AS amount
        FROM log_events
        WHERE tenant_id=:tenant AND service_name=:service
          AND timestamp >= to_timestamp(:start) AND timestamp < to_timestamp(:end)
        GROUP BY 1,2"""), {
            "tenant": tenant, "service": service, "start": start_epoch,
            "end": end_epoch, "current_start": current_epoch,
        }).mappings().all()
    recent, baseline = {}, {}
    for row in severity_rows:
        target = recent if row["period"] == "recent" else baseline
        target[row["severity"]] = int(row["amount"])
    shift = severity_distribution_shift(recent, baseline)
    if shift is not None:
        _record_anomaly(conn, increment=0,
            dedupe_key=f"severity_shift:{tenant}:{service}:{bucket_id}",
            kind="severity_distribution_shift", severity="medium", service=service,
            description=f"Severity mix changed materially (total-variation distance {shift:.2f}).",
            sample={"tenant_id": tenant, "service_name": service, "recent": recent,
                    "baseline": baseline, "total_variation_distance": shift,
                    "threshold": 0.35, "bucket_epoch": bucket_id})


def _detect_rare_template(conn, event, frequency):
    template_id = event.get("template_id")
    if not template_id or frequency > 2:
        return
    tenant = event.get("tenant_id") or "default"
    app = event.get("application_id") or "unknown"
    service = event.get("service_name") or "unknown"
    population = conn.execute(text("""SELECT
        (SELECT count(*) FROM log_events WHERE tenant_id=:tenant AND application_id=:app
          AND service_name=:service) AS event_count,
        (SELECT count(*) FROM template_registry WHERE tenant_id=:tenant AND application_id=:app
          AND service_name=:service) AS template_count"""), {
            "tenant": tenant, "app": app, "service": service,
        }).mappings().one()
    if int(population["event_count"] or 0) < 100 or int(population["template_count"] or 0) < 5:
        return
    if template_id in rare_template_ids({template_id: int(frequency)}, minimum_count=3):
        _record_anomaly(conn,
            dedupe_key=f"rare_template:{tenant}:{app}:{service}:{template_id}",
            kind="rare_template", severity="low", service=service,
            description=f"Rare log template observed only {frequency} times in a population of {population['event_count']} events.",
            sample={"tenant_id": tenant, "application_id": app, "service_name": service,
                    "template_id": template_id, "template": event.get("template"),
                    "template_frequency": int(frequency),
                    "population_events": int(population["event_count"]),
                    "population_templates": int(population["template_count"])})


def transform(event):
    if not event.get("event_id") or not event.get("message"):
        raise ValueError("parsed event requires event_id and message")

    engine = db()
    with engine.begin() as conn:
        inserted = conn.execute(text("""INSERT INTO log_events(
            event_id,tenant_id,application_id,service_name,environment,timestamp,received_at,
            severity,message,raw_message,trace_id,span_id,request_id,correlation_id,
            template_id,template,parameters,attributes,source_type,dataset_id)
            VALUES(:event_id,:tenant_id,:application_id,:service_name,:environment,:timestamp,
            :received_at,:severity,:message,:raw_message,:trace_id,:span_id,:request_id,
            :correlation_id,:template_id,:template,CAST(:parameters AS jsonb),
            CAST(:attributes AS jsonb),:source_type,:dataset_id)
            ON CONFLICT(event_id) DO NOTHING RETURNING event_id"""), {
                **event,
                "parameters": json.dumps(event.get("parameters", {})),
                "attributes": json.dumps(event.get("attributes", {})),
            }).scalar_one_or_none()

        # Retries still emit the persisted notification, but never mutate intelligence twice.
        if inserted is not None:
            if event.get("template_id") and event.get("template"):
                registry = conn.execute(text("""INSERT INTO template_registry(
                    tenant_id,application_id,service_name,template_id,template,frequency,first_seen,last_seen)
                    VALUES(:tenant,:app,:service,:template_id,:template,1,
                           COALESCE(CAST(:timestamp AS timestamptz),now()),
                           COALESCE(CAST(:timestamp AS timestamptz),now()))
                    ON CONFLICT(tenant_id,application_id,service_name,template_id)
                    DO UPDATE SET frequency=template_registry.frequency+1,
                                  last_seen=GREATEST(template_registry.last_seen,EXCLUDED.last_seen),
                                  template=EXCLUDED.template
                    RETURNING frequency,first_seen,last_seen"""), {
                        "tenant": event.get("tenant_id") or "default",
                        "app": event.get("application_id") or "unknown",
                        "service": event.get("service_name") or "unknown",
                        "template_id": event["template_id"], "template": event["template"],
                        "timestamp": event.get("timestamp"),
                    }).mappings().one()
                if int(registry["frequency"]) == 1:
                    _record_anomaly(conn,
                        dedupe_key=(f"new_template:{event.get('tenant_id','default')}:"
                                    f"{event.get('application_id','unknown')}:{event.get('service_name','unknown')}:"
                                    f"{event['template_id']}"),
                        kind="new_template", severity="low", service=event.get("service_name"),
                        description=f"First observed log template in {event.get('service_name') or 'unknown service'}.",
                        sample={"tenant_id": event.get("tenant_id", "default"),
                                "application_id": event.get("application_id", "unknown"),
                                "template_id": event["template_id"], "template": event["template"]})
                _detect_rare_template(conn, event, int(registry["frequency"]))

            _detect_time_series(conn, event)

    persisted = dict(event)
    persisted["event_type"] = "log_persisted"
    return persisted


if __name__ == "__main__":
    run_stage(input_topic="logs.parsed", output_topic="logs.persisted",
              group_id="logiq-intelligence-v1", transform=transform)
