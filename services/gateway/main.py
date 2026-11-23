"""Thin HTTP gateway with method-aware routing and safe header forwarding."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response as PromResponse
import logging, time, uuid
import httpx
from shared.common import REQS, LAT
from shared.observability import configure_json_logging, normalize_metric_path, request_id_context

configure_json_logging()

app = FastAPI(title='LogIQ API Gateway', version='0.2.0')


@app.middleware('http')
async def gateway_metrics(request: Request, call_next):
    request_id = request.headers.get('x-request-id') or str(uuid.uuid4())
    token = request_id_context.set(request_id)
    started = time.perf_counter()
    status = '500'
    try:
        response = await call_next(request)
        status = str(response.status_code)
        response.headers['x-request-id'] = request_id
        return response
    finally:
        route = request.scope.get('route')
        path = normalize_metric_path(getattr(route, 'path', request.url.path))
        REQS.labels('gateway', request.method, path, status).inc()
        LAT.labels('gateway').observe(time.perf_counter() - started)
        request_id_context.reset(token)


@app.get('/metrics')
def gateway_metrics_endpoint():
    return PromResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

ROUTES = {
    '/v1/otlp': 'http://collection:8000',
    '/v1/datasets': 'http://dataset:8000',
    '/v1/parsers': 'http://parser:8000',
    '/v1/benchmarks': 'http://parser:8000',
    '/v1/analytics': 'http://analytics:8000',
    '/v1/templates': 'http://analytics:8000',
    '/v1/anomalies': 'http://analytics:8000',
    '/v1/api-keys': 'http://identity:8000',
    '/v1/identity': 'http://identity:8000',
    '/v1/auth': 'http://identity:8000',
    '/v1/applications': 'http://identity:8000',
    '/v1/users': 'http://identity:8000',
}


@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'gateway'}


@app.api_route('/{path:path}', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
async def proxy(path: str, request: Request):
    route = '/' + path
    if route == '/v1/logs':
        target = 'http://collection:8000' if request.method == 'POST' else 'http://analytics:8000'
    elif route.startswith('/v1/logs/'):
        target = 'http://analytics:8000'
    else:
        target = next((url for prefix, url in ROUTES.items() if route.startswith(prefix)), None)
    if not target:
        return JSONResponse({'detail': 'route not found'}, 404)
    headers = {key: value for key, value in request.headers.items()
               if key.lower() in ('content-type', 'x-api-key', 'authorization', 'x-request-id')}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            upstream = await client.request(request.method, target + route, params=request.query_params,
                                             content=await request.body(), headers=headers)
        content_type = upstream.headers.get('content-type', '')
        if 'application/json' in content_type:
            return JSONResponse(content=upstream.json(), status_code=upstream.status_code)
        return Response(content=upstream.content, status_code=upstream.status_code,
                        media_type=content_type or None)
    except httpx.TimeoutException:
        return JSONResponse({'detail': 'Upstream service timed out'}, 504)
    except httpx.HTTPError:
        return JSONResponse({'detail': 'Upstream service unavailable'}, 502)
