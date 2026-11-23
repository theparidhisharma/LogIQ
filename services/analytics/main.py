"""Tenant-scoped log search and analytics APIs.

All filters are parameterized. The only SQL fragments interpolated below are
fixed column names and date_trunc units selected from explicit allow-lists.
"""
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Query
from sqlalchemy import text
from shared.common import *
from shared.security import current_user

app = make_app('analytics')




def _time_filters(start_time: datetime | None, end_time: datetime | None):
    if start_time and start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time and end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)
    if start_time and end_time and start_time > end_time:
        raise HTTPException(422, 'start_time must be earlier than or equal to end_time')
    clauses, params = [], {}
    if start_time:
        clauses.append('timestamp >= :start_time')
        params['start_time'] = start_time
    if end_time:
        clauses.append('timestamp <= :end_time')
        params['end_time'] = end_time
    return clauses, params


@app.get('/v1/analytics/overview')
def overview(start_time: datetime | None = None, end_time: datetime | None = None,
            user=Depends(current_user)):
    time_clauses, time_params = _time_filters(start_time, end_time)
    event_where = ['tenant_id=:tenant', *time_clauses]
    params = {'tenant': user['tenant_id'], **time_params}
    with db().connect() as conn:
        row = conn.execute(text(f'''SELECT count(*) AS total,
            count(*) FILTER (WHERE severity IN ('ERROR','FATAL')) AS errors,
            count(DISTINCT application_id) AS applications,
            count(DISTINCT service_name) AS services
            FROM log_events WHERE {' AND '.join(event_where)}'''), params).mappings().one()
        anomaly_clauses = ['tenant_id=:tenant']
        anomaly_params = {'tenant': user['tenant_id']}
        if start_time:
            anomaly_clauses.append('created_at >= :start_time'); anomaly_params['start_time'] = time_params['start_time']
        if end_time:
            anomaly_clauses.append('created_at <= :end_time'); anomaly_params['end_time'] = time_params['end_time']
        anomalies_count = conn.execute(text('SELECT count(*) FROM anomalies WHERE ' + ' AND '.join(anomaly_clauses)), anomaly_params).scalar() or 0
        template_count = conn.execute(text('SELECT count(*) FROM template_registry WHERE tenant_id=:tenant'), {'tenant': user['tenant_id']}).scalar() or 0
    total, errors = int(row['total'] or 0), int(row['errors'] or 0)
    return {'total_events': total, 'error_events': errors,
            'error_rate': round(errors / total, 4) if total else 0,
            'active_applications': int(row['applications'] or 0),
            'active_services': int(row['services'] or 0),
            'anomalies': int(anomalies_count), 'known_templates': int(template_count),
            'start_time': start_time, 'end_time': end_time}


@app.get('/v1/logs')
def logs(service: str | None = None, severity: str | None = None, q: str | None = Query(None, max_length=500),
         application_id: str | None = None, environment: str | None = None,
         template_id: str | None = None, trace_id: str | None = None,
         request_id: str | None = None, source_type: str | None = None,
         dataset_id: str | None = None,
         start_time: datetime | None = None, end_time: datetime | None = None,
         limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0, le=1000000),
         before_timestamp: datetime | None = None, before_event_id: str | None = None,
         include_total: bool = True, user=Depends(current_user)):
    """Search tenant-owned logs. Cursor pagination is stable for deep result sets."""
    if bool(before_timestamp) != bool(before_event_id):
        raise HTTPException(422, 'before_timestamp and before_event_id must be supplied together')
    clauses = ['tenant_id=:tenant']
    params = {'tenant': user['tenant_id'], 'limit': limit, 'offset': offset}
    for value, column, key in [
        (service, 'service_name', 'service'),
        (severity.upper() if severity else None, 'severity', 'severity'),
        (application_id, 'application_id', 'application'),
        (environment, 'environment', 'environment'),
        (template_id, 'template_id', 'template'),
        (trace_id, 'trace_id', 'trace_id'),
        (request_id, 'request_id', 'request_id'),
        (source_type, 'source_type', 'source_type'),
        (dataset_id, 'dataset_id', 'dataset_id'),
    ]:
        if value:
            clauses.append(f'{column}=:{key}')
            params[key] = value
    if q:
        clauses.append('(message ILIKE :q OR raw_message ILIKE :q)')
        params['q'] = f'%{q}%'
    time_clauses, time_params = _time_filters(start_time, end_time)
    clauses.extend(time_clauses)
    params.update(time_params)
    if before_timestamp and before_event_id:
        if before_timestamp.tzinfo is None:
            before_timestamp = before_timestamp.replace(tzinfo=timezone.utc)
        clauses.append('(timestamp,event_id) < (:before_timestamp,:before_event_id)')
        params['before_timestamp'] = before_timestamp
        params['before_event_id'] = before_event_id
    where = ' WHERE ' + ' AND '.join(clauses)
    with db().connect() as conn:
        total = None
        if include_total and not before_timestamp:
            total = int(conn.execute(text('SELECT count(*) FROM log_events' + where), params).scalar() or 0)
        pagination_sql = '' if before_timestamp else ' OFFSET :offset'
        query = text("""SELECT event_id,application_id,service_name,environment,severity,message,raw_message,
            timestamp,received_at,template_id,template,trace_id,span_id,request_id,correlation_id,attributes,
            source_type,dataset_id
            FROM log_events""" + where + ' ORDER BY timestamp DESC,event_id DESC LIMIT :limit' + pagination_sql)
        rows = conn.execute(query, params | {'limit': limit + 1}).mappings().all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = None
    if has_more and rows:
        next_cursor = {'before_timestamp': rows[-1]['timestamp'], 'before_event_id': rows[-1]['event_id']}
    result = {'items': [dict(row) for row in rows], 'limit': limit, 'has_more': has_more,
              'next_cursor': next_cursor, 'pagination': 'cursor' if before_timestamp else 'offset'}
    if total is not None:
        result.update({'total': total, 'offset': offset})
    return result


@app.get('/v1/analytics/timeseries')
def timeseries(hours: int = Query(24, ge=1, le=720), interval: str = Query('hour'),
               service: str | None = None, application_id: str | None = None,
               user=Depends(current_user)):
    if interval not in {'minute', 'hour', 'day'}:
        raise HTTPException(422, 'interval must be minute, hour, or day')
    clauses = ['tenant_id=:tenant', 'timestamp >= now() - (:hours * interval \'1 hour\')']
    params = {'tenant': user['tenant_id'], 'hours': hours}
    if service:
        clauses.append('service_name=:service'); params['service'] = service
    if application_id:
        clauses.append('application_id=:application'); params['application'] = application_id
    # interval is selected from a strict allow-list above, never user-interpolated raw.
    query = f'''SELECT date_trunc('{interval}',timestamp) AS bucket,
        count(*) AS events,
        count(*) FILTER (WHERE severity IN ('ERROR','FATAL')) AS errors,
        count(*) FILTER (WHERE severity='WARN') AS warnings
        FROM log_events WHERE {' AND '.join(clauses)}
        GROUP BY 1 ORDER BY 1'''
    with db().connect() as conn:
        rows = conn.execute(text(query), params).mappings().all()
    return {'window_hours': hours, 'interval': interval, 'items': [dict(row) for row in rows]}


@app.get('/v1/analytics/severity-distribution')
def severity_distribution(hours: int = Query(24, ge=1, le=720),
                          service: str | None = None, user=Depends(current_user)):
    clauses = ['tenant_id=:tenant', 'timestamp >= now() - (:hours * interval \'1 hour\')']
    params = {'tenant': user['tenant_id'], 'hours': hours}
    if service:
        clauses.append('service_name=:service'); params['service'] = service
    with db().connect() as conn:
        rows = conn.execute(text('''SELECT severity,count(*) AS count FROM log_events WHERE ''' +
            ' AND '.join(clauses) + ' GROUP BY severity ORDER BY count DESC'), params).mappings().all()
    return {'window_hours': hours, 'items': [dict(row) for row in rows]}


@app.get('/v1/analytics/errors/by-service')
def errors_by_service(hours: int = Query(24, ge=1, le=720),
                      limit: int = Query(20, ge=1, le=100), user=Depends(current_user)):
    with db().connect() as conn:
        rows = conn.execute(text('''SELECT service_name,count(*) AS error_count,
            count(DISTINCT application_id) AS applications,
            max(timestamp) AS last_error
            FROM log_events WHERE tenant_id=:tenant
              AND severity IN ('ERROR','FATAL')
              AND timestamp >= now() - (:hours * interval '1 hour')
            GROUP BY service_name ORDER BY error_count DESC LIMIT :limit'''),
            {'tenant': user['tenant_id'], 'hours': hours, 'limit': limit}).mappings().all()
    return {'window_hours': hours, 'items': [dict(row) for row in rows]}


@app.get('/v1/analytics/template-trends')
def template_trends(hours: int = Query(24, ge=1, le=720),
                    service: str | None = None, application_id: str | None = None,
                    user=Depends(current_user)):
    filters = ['tenant_id=:tenant']
    params = {'tenant': user['tenant_id'], 'hours': hours}
    if service:
        filters.append('service_name=:service')
        params['service'] = service
    if application_id:
        filters.append('application_id=:application')
        params['application'] = application_id
    where = ' AND '.join(filters)
    query = text(f'''WITH event_activity AS (
          SELECT date_trunc('hour',timestamp) AS bucket,
                 count(*) AS event_count,
                 count(DISTINCT template_id) AS distinct_templates,
                 count(*) FILTER (WHERE severity IN ('ERROR','FATAL')) AS error_count
          FROM log_events
          WHERE {where} AND timestamp >= now() - (:hours * interval '1 hour')
          GROUP BY 1
        ), discoveries AS (
          SELECT date_trunc('hour',first_seen) AS bucket, count(*) AS templates_discovered
          FROM template_registry
          WHERE {where} AND first_seen >= now() - (:hours * interval '1 hour')
          GROUP BY 1
        )
        SELECT a.bucket,a.event_count,a.distinct_templates,a.error_count,
               COALESCE(d.templates_discovered,0) AS templates_discovered
        FROM event_activity a LEFT JOIN discoveries d USING(bucket)
        ORDER BY a.bucket''')
    with db().connect() as conn:
        rows = conn.execute(query, params).mappings().all()
    return {'window_hours': hours, 'items': [dict(row) for row in rows],
            'definitions': {'event_count': 'events ingested during the bucket',
                            'templates_discovered': 'templates first observed during the bucket',
                            'distinct_templates': 'distinct template IDs observed during the bucket'}}


@app.get('/v1/templates')
def templates(limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
              service: str | None = None, application_id: str | None = None,
              user=Depends(current_user)):
    clauses = ['tenant_id=:tenant']
    params = {'tenant': user['tenant_id'], 'n': limit, 'offset': offset}
    if service:
        clauses.append('service_name=:service'); params['service'] = service
    if application_id:
        clauses.append('application_id=:app'); params['app'] = application_id
    where = ' WHERE ' + ' AND '.join(clauses)
    with db().connect() as conn:
        total = conn.execute(text('SELECT count(*) FROM template_registry' + where), params).scalar() or 0
        rows = conn.execute(text('''SELECT application_id,service_name,template_id,template,frequency,first_seen,last_seen
            FROM template_registry''' + where +
            ' ORDER BY frequency DESC,last_seen DESC LIMIT :n OFFSET :offset'), params).mappings().all()
    return {'items': [dict(row) for row in rows], 'total': int(total), 'limit': limit, 'offset': offset}


@app.get('/v1/anomalies')
def anomalies(limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
              kind: str | None = None, severity: str | None = None, service: str | None = None,
              status: str | None = None, start_time: datetime | None = None, end_time: datetime | None = None,
              user=Depends(current_user)):
    clauses = ['tenant_id=:tenant']
    params = {'tenant': user['tenant_id'], 'n': limit, 'offset': offset}
    for value, column, key in [(kind, 'kind', 'kind'), (severity.lower() if severity else None, 'severity', 'severity'),
                               (service, 'service_name', 'service'), (status, 'status', 'status')]:
        if value:
            clauses.append(f'{column}=:{key}'); params[key] = value
    time_clauses, time_params = _time_filters(start_time, end_time)
    clauses.extend(c.replace('timestamp', 'created_at') for c in time_clauses); params.update(time_params)
    where = ' WHERE ' + ' AND '.join(clauses)
    with db().connect() as conn:
        total = conn.execute(text('SELECT count(*) FROM anomalies' + where), params).scalar() or 0
        rows = conn.execute(text('''SELECT id,kind,severity,service_name,description,created_at,sample,
                status,first_seen,last_seen,resolved_at,occurrence_count,rule_version
            FROM anomalies''' + where + ' ORDER BY last_seen DESC,id DESC LIMIT :n OFFSET :offset'), params).mappings().all()
    return {'items': [dict(row) for row in rows], 'total': int(total), 'limit': limit, 'offset': offset}



@app.patch('/v1/anomalies/{anomaly_id}/status')
def update_anomaly_status(anomaly_id: int, status: str = Query(...),
                          user=Depends(current_user)):
    """Tenant-scoped anomaly lifecycle transition."""
    normalized = status.strip().lower()
    if normalized not in {'open', 'acknowledged', 'resolved'}:
        raise HTTPException(422, "status must be open, acknowledged, or resolved")
    with db().begin() as conn:
        row = conn.execute(text("""UPDATE anomalies SET status=:status,
                resolved_at=CASE WHEN :status='resolved' THEN COALESCE(resolved_at,now())
                                 ELSE NULL END
            WHERE id=:id AND tenant_id=:tenant
            RETURNING id,status,first_seen,last_seen,resolved_at,occurrence_count"""), {
                "status": normalized, "id": anomaly_id, "tenant": user["tenant_id"],
            }).mappings().first()
    if row is None:
        raise HTTPException(404, "anomaly not found")
    return dict(row)


@app.get('/v1/logs/{event_id}')
def log_detail(event_id: str, user=Depends(current_user)):
    """Return one log event only when it belongs to the authenticated tenant."""
    with db().connect() as conn:
        row = conn.execute(text('''SELECT event_id,tenant_id,application_id,service_name,environment,
            severity,message,raw_message,timestamp,received_at,template_id,template,parameters,
            trace_id,span_id,request_id,correlation_id,attributes,source_type,dataset_id
            FROM log_events WHERE event_id=:event_id AND tenant_id=:tenant'''),
            {'event_id': event_id, 'tenant': user['tenant_id']}).mappings().first()
    if row is None:
        raise HTTPException(404, 'Log event not found')
    return dict(row)


@app.get('/v1/templates/{template_id}')
def template_detail(template_id: str, service: str | None = None,
                    application_id: str | None = None, user=Depends(current_user)):
    clauses = ['tenant_id=:tenant', 'template_id=:template_id']
    params = {'tenant': user['tenant_id'], 'template_id': template_id}
    if service:
        clauses.append('service_name=:service')
        params['service'] = service
    if application_id:
        clauses.append('application_id=:application')
        params['application'] = application_id
    where = ' AND '.join(clauses)
    with db().connect() as conn:
        rows = conn.execute(text('''SELECT application_id,service_name,template_id,template,
                frequency,first_seen,last_seen
            FROM template_registry WHERE ''' + where + ' ORDER BY frequency DESC'),
            params).mappings().all()
        if not rows:
            raise HTTPException(404, 'Template not found')
        parameter_rows = conn.execute(text('''SELECT p.key AS parameter_name,
                count(*) AS occurrences,count(DISTINCT p.value) AS distinct_values,
                (array_agg(DISTINCT p.value))[1:3] AS sample_values
            FROM log_events e
            CROSS JOIN LATERAL jsonb_each_text(
                CASE WHEN jsonb_typeof(e.parameters)='object' THEN e.parameters ELSE '{}'::jsonb END
            ) AS p
            WHERE e.tenant_id=:tenant AND e.template_id=:template_id
              AND (:service IS NULL OR e.service_name=:service)
              AND (:application IS NULL OR e.application_id=:application)
            GROUP BY p.key ORDER BY occurrences DESC,p.key'''), {
                'tenant': user['tenant_id'], 'template_id': template_id,
                'service': service, 'application': application_id,
            }).mappings().all()
    return {'template_id': template_id, 'instances': [dict(row) for row in rows],
            'parameters': [dict(row) for row in parameter_rows]}


@app.get('/v1/analytics/services')
def service_summary(hours: int = Query(24, ge=1, le=720),
                    application_id: str | None = None, user=Depends(current_user)):
    clauses = ['tenant_id=:tenant', "timestamp >= now() - (:hours * interval '1 hour')"]
    params = {'tenant': user['tenant_id'], 'hours': hours}
    if application_id:
        clauses.append('application_id=:application')
        params['application'] = application_id
    with db().connect() as conn:
        rows = conn.execute(text('''SELECT service_name,count(*) AS event_count,
                count(*) FILTER (WHERE severity IN ('ERROR','FATAL')) AS error_count,
                count(*) FILTER (WHERE severity='WARN') AS warning_count,
                count(DISTINCT application_id) AS application_count,
                max(timestamp) AS last_seen
            FROM log_events WHERE ''' + ' AND '.join(clauses) +
            ''' GROUP BY service_name ORDER BY error_count DESC,event_count DESC'''),
            params).mappings().all()
    items = []
    for row in rows:
        item = dict(row)
        total = int(item['event_count'] or 0)
        item['error_rate'] = round(int(item['error_count'] or 0) / total, 4) if total else 0
        items.append(item)
    return {'window_hours': hours, 'items': items}
