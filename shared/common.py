import os, json, time, uuid, logging, re
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from shared.observability import configure_json_logging, normalize_metric_path, request_id_context
from kafka import KafkaProducer, KafkaConsumer
from sqlalchemy import create_engine, text
from functools import lru_cache
from shared.dataset_utils import kafka_key_bytes

configure_json_logging()
SERVICE=os.getenv('SERVICE_NAME','logiq-service')
DATABASE_URL=os.getenv('DATABASE_URL','postgresql+psycopg://logiq_core:logiq-core-dev-only@postgres:5432/logiq_core')
IDENTITY_DATABASE_URL=os.getenv('IDENTITY_DATABASE_URL','postgresql+psycopg://logiq_identity:logiq-identity-dev-only@postgres:5432/logiq_identity')
DATASET_DATABASE_URL=os.getenv('DATASET_DATABASE_URL','postgresql+psycopg://logiq_dataset:logiq-dataset-dev-only@postgres:5432/logiq_dataset')
KAFKA=os.getenv('KAFKA_BOOTSTRAP_SERVERS','kafka:9092')
REQS=Counter('logiq_http_requests_total','HTTP requests',['service','method','path','status'])
LAT=Histogram('logiq_http_request_duration_seconds','HTTP request duration',['service'])

@lru_cache(maxsize=1)
def db(): return create_engine(DATABASE_URL,pool_pre_ping=True)
@lru_cache(maxsize=1)
def identity_db(): return create_engine(IDENTITY_DATABASE_URL,pool_pre_ping=True)
@lru_cache(maxsize=1)
def dataset_db(): return create_engine(DATASET_DATABASE_URL,pool_pre_ping=True)
_PRODUCER = None
_PRODUCER_LOCK = __import__('threading').Lock()
def producer():
    # One producer per process (kafka-python producers are thread-safe and own a sender thread).
    # kafka-python requires byte keys unless a key serializer is configured.
    global _PRODUCER
    with _PRODUCER_LOCK:
        if _PRODUCER is None:
            _PRODUCER = KafkaProducer(
                bootstrap_servers=KAFKA,
                value_serializer=lambda v: json.dumps(v, default=str).encode(),
                key_serializer=kafka_key_bytes,
                retries=5, acks="all",
            )
        return _PRODUCER
def send(topic, event, key=None):
    p = producer()
    p.send(topic, event, key=key).get(timeout=15)
    p.flush()
def event(message, **kw):
    now=datetime.now(timezone.utc).isoformat()
    return {'event_id':str(uuid.uuid4()),'schema_version':'1.0','tenant_id':kw.get('tenant_id','default'), 'application_id':kw.get('application_id','unknown'), 'service_name':kw.get('service_name','unknown'), 'environment':kw.get('environment','development'), 'source_type':kw.get('source_type','http'), 'source_name':kw.get('source_name','unknown'), 'timestamp':kw.get('timestamp',now), 'received_at':now, 'severity':str(kw.get('severity','INFO')).upper(), 'message':str(message), 'raw_message':str(message), 'trace_id':kw.get('trace_id'), 'span_id':kw.get('span_id'), 'request_id':kw.get('request_id'), 'correlation_id':kw.get('correlation_id'), 'attributes':kw.get('attributes',{}), 'sequence_number':kw.get('sequence_number'), 'dataset_id':kw.get('dataset_id')}

def make_app(name, database='core'):
    app=FastAPI(title=f'LogIQ {name.title()} Service',version='0.1.0')
    @app.middleware('http')
    async def metrics(request:Request, call_next):
        request_id = request.headers.get('x-request-id') or str(uuid.uuid4())
        request.state.request_id = request_id
        token = request_id_context.set(request_id)
        start = time.perf_counter()
        status = '500'
        try:
            response = await call_next(request)
            status = str(response.status_code)
            response.headers['x-request-id'] = request_id
            return response
        finally:
            route = request.scope.get('route')
            path = normalize_metric_path(route.path) if route is not None else 'unmatched'
            REQS.labels(name, request.method, path, status).inc()
            LAT.labels(name).observe(time.perf_counter() - start)
            request_id_context.reset(token)
    @app.get('/health')
    def health(): return {'status':'ok','service':name}
    @app.get('/ready')
    def ready():
        try:
            engine = {'core': db, 'identity': identity_db, 'dataset': dataset_db}.get(database, db)()
            with engine.connect() as c: c.execute(text('SELECT 1'))
            return {'status':'ready','service':name}
        except Exception as e: raise HTTPException(503,detail=f'database unavailable: {type(e).__name__}')
    @app.get('/metrics')
    def metrics_endpoint(): return Response(generate_latest(),media_type=CONTENT_TYPE_LATEST)
    return app


from shared.parsing import parse_line, template_for
