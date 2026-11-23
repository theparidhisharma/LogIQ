from fastapi import HTTPException, Request
from pydantic import BaseModel, Field
from typing import Any
from shared.common import *
from shared.common import identity_db
from shared.security import authenticate_api_key
from services.collection.otlp import decode_otlp_json, decode_otlp_protobuf
import hmac, os, logging
app=make_app('collection')

class LogBatch(BaseModel):
    logs:list[dict[str,Any]] = Field(min_length=1,max_length=5000)
@app.post('/v1/logs')
async def ingest(batch:LogBatch, request:Request):
    key_context = authenticate_api_key(request); p=producer(); futures=[]
    try:
        for item in batch.logs:
            msg=item.get('message') or item.get('body')
            if not msg: continue
            # dataset_id is server-assigned only; clients must not tag events with it.
            metadata = {k:v for k,v in item.items() if k not in {'message','tenant_id','dataset_id'}}
            metadata['tenant_id'] = key_context['tenant_id']
            if key_context.get('application_id'):
                metadata['application_id'] = key_context['application_id']
            elif metadata.get('application_id'):
                with identity_db().connect() as conn:
                    valid_app = conn.execute(text('SELECT 1 FROM applications WHERE id=:id AND tenant_id=:tenant'),
                                             {'id': metadata['application_id'], 'tenant': key_context['tenant_id']}).scalar()
                if not valid_app:
                    raise HTTPException(403, 'Application does not belong to this API key tenant')
            e=event(msg,**metadata)
            futures.append(p.send('logs.raw',e,key=e.get('application_id')))
        p.flush()
        for f in futures: f.get(timeout=15)   # count only broker-acknowledged records
        accepted=len(futures)
        return {'accepted':accepted,'rejected':len(batch.logs)-accepted,'topic':'logs.raw'}
    except HTTPException: raise
    except Exception as exc: raise HTTPException(503,f'Ingestion temporarily unavailable: {type(exc).__name__}')
@app.post('/v1/otlp/logs')
async def otlp(request:Request):
    """Accept the standard OTLP/HTTP Logs export endpoint (JSON or protobuf)."""
    content_type = request.headers.get('content-type', '').split(';', 1)[0].strip().lower()
    raw = await request.body()
    try:
        if content_type in {'application/x-protobuf', 'application/protobuf'}:
            records = decode_otlp_protobuf(raw)
        elif content_type in {'application/json', ''}:
            payload = await request.json()
            if 'resourceLogs' in payload:
                records = decode_otlp_json(payload)
            else:
                # Backward compatibility for the earlier LogIQ envelope.
                records = payload.get('logs', payload.get('records', []))
        else:
            raise HTTPException(415, 'OTLP Logs accepts application/json or application/x-protobuf')
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f'Invalid OTLP Logs payload: {type(exc).__name__}') from exc
    if not records:
        raise HTTPException(400, 'OTLP request contains no log records')

    # Collector-to-Collection traffic uses a separate shared secret. Tenant identity
    # must still be supplied as an OTLP resource attribute; it is never inferred.
    expected = os.getenv('LOGIQ_OTLP_INGEST_TOKEN', '')
    supplied = request.headers.get('x-logiq-otlp-token', '')
    if expected and hmac.compare_digest(expected, supplied):
        normalized = []
        for record in records:
            tenant_id = record.pop('tenant_id', None)
            if not tenant_id:
                raise HTTPException(422, 'OTLP resource must include logiq.tenant_id')
            record['tenant_id'] = tenant_id
            normalized.append(record)
        batch = LogBatch(logs=normalized)
        p = producer(); futures = []
        try:
            for item in batch.logs:
                message = item.get('message')
                if not message: continue
                tenant = item['tenant_id']
                with identity_db().connect() as conn:
                    valid_tenant = conn.execute(text('SELECT 1 FROM tenants WHERE id=:id'), {'id': tenant}).scalar()
                if not valid_tenant:
                    raise HTTPException(403, 'OTLP tenant does not exist')
                application_id = item.get('application_id')
                if application_id and application_id != 'unknown':
                    with identity_db().connect() as conn:
                        valid_application = conn.execute(text(
                            'SELECT 1 FROM applications WHERE id=:id AND tenant_id=:tenant'),
                            {'id': application_id, 'tenant': tenant}).scalar()
                    if not valid_application:
                        raise HTTPException(403, 'OTLP application does not belong to the supplied tenant')
                event_fields = {key: value for key, value in item.items() if key not in {'message', 'dataset_id'}}
                event_payload = event(message, **event_fields)
                futures.append(p.send('logs.raw', event_payload, key=event_payload.get('application_id')))
            p.flush()
            for f in futures: f.get(timeout=15)
            accepted = len(futures)
            return {'accepted': accepted, 'rejected': len(batch.logs)-accepted, 'topic': 'logs.raw', 'protocol': 'otlp'}
        except HTTPException:
            raise
        except Exception as exc:
            logging.getLogger(__name__).exception('OTLP publish failed')
            raise HTTPException(503, f'OTLP ingestion temporarily unavailable: {type(exc).__name__}') from exc
    # Existing API-key path remains supported for JSON/protobuf clients.
    context = authenticate_api_key(request)
    for record in records:
        record['tenant_id'] = context['tenant_id']
        if context.get('application_id'):
            record['application_id'] = context['application_id']
    return await ingest(LogBatch(logs=records), request)
