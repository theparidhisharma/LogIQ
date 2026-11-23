"""Tenant-scoped dataset intake with durable MinIO source artifacts."""
from fastapi import UploadFile, File, Form, HTTPException, Request
from shared.common import *
from shared.common import dataset_db as db
from shared.security import authenticate_api_key
from shared.object_storage import put_raw_dataset_file, inspect_upload_file, delete_raw_dataset
from shared.dataset_utils import publication_bytes_per_second
import uuid, random, hashlib, json, os

app = make_app('dataset', database='dataset')
MAX_UPLOAD_BYTES = int(os.getenv('DATASET_MAX_UPLOAD_BYTES', str(5 * 1024 * 1024 * 1024)))

# LogHub metadata is deliberately a catalog, not a mirror: downloads and original
# research terms remain controlled by the upstream project.
LOGHUB_CATALOG = {
    'HDFS_v1': {'name': 'HDFS_v1', 'description': 'Hadoop Distributed File System log', 'labeled': True, 'lines': 11175629, 'raw_size': '1.47 GiB', 'download': 'https://zenodo.org/records/8196385/files/HDFS_v1.zip?download=1'},
    'Hadoop': {'name': 'Hadoop', 'description': 'Hadoop MapReduce job log', 'labeled': True, 'lines': 394308, 'raw_size': '48.61 MiB', 'download': 'https://zenodo.org/records/8196385/files/Hadoop.zip?download=1'},
    'OpenStack': {'name': 'OpenStack', 'description': 'OpenStack infrastructure log', 'labeled': True, 'lines': 207820, 'raw_size': '58.61 MiB', 'download': 'https://zenodo.org/records/8196385/files/OpenStack.tar.gz?download=1'},
    'BGL': {'name': 'BGL', 'description': 'Blue Gene/L supercomputer log', 'labeled': True, 'lines': 4747963, 'raw_size': '708.76 MiB', 'download': 'https://zenodo.org/records/8196385/files/BGL.zip?download=1'},
    'HPC': {'name': 'HPC', 'description': 'High performance cluster log', 'labeled': False, 'lines': 433489, 'raw_size': '32.00 MiB', 'download': 'https://zenodo.org/records/8196385/files/HPC.zip?download=1'},
    'Zookeeper': {'name': 'Zookeeper', 'description': 'ZooKeeper service log', 'labeled': False, 'lines': 74380, 'raw_size': '9.95 MiB', 'download': 'https://zenodo.org/records/8196385/files/Zookeeper.tar.gz?download=1'},
    'Linux': {'name': 'Linux', 'description': 'Linux system log', 'labeled': False, 'lines': 25567, 'raw_size': '2.25 MiB', 'download': 'https://zenodo.org/records/8196385/files/Linux.tar.gz?download=1'},
    'Mac': {'name': 'Mac', 'description': 'Mac OS log', 'labeled': False, 'lines': 117283, 'raw_size': '16.09 MiB', 'download': 'https://zenodo.org/records/8196385/files/Mac.tar.gz?download=1'},
    'Apache': {'name': 'Apache', 'description': 'Apache web server error log', 'labeled': False, 'lines': 56481, 'raw_size': '4.90 MiB', 'download': 'https://zenodo.org/records/8196385/files/Apache.tar.gz?download=1'},
    'Proxifier': {'name': 'Proxifier', 'description': 'Proxifier software log', 'labeled': False, 'lines': 21329, 'raw_size': '2.42 MiB', 'download': 'https://zenodo.org/records/8196385/files/Proxifier.tar.gz?download=1'},
    'HealthApp': {'name': 'HealthApp', 'description': 'Health app log', 'labeled': False, 'lines': 253395, 'raw_size': '22.44 MiB', 'download': 'https://zenodo.org/records/8196385/files/HealthApp.tar.gz?download=1'},
}

@app.get('/v1/datasets/catalog/loghub')
def loghub_catalog():
    return {'source': 'LogHub', 'repository': 'https://github.com/logpai/loghub',
            'terms_note': 'LogHub states datasets are freely available for research/academic work; review upstream terms and cite the LogHub paper before use.',
            'import_workflow': 'Download the upstream archive, extract the raw .log/.txt/.csv file, then upload it with source_type=loghub and source_reference=<catalog ID>. The uploads stream from the spooled multipart file to MinIO; default maximum is 5 GiB (configurable with DATASET_MAX_UPLOAD_BYTES).',
            'items': list(LOGHUB_CATALOG.values())}

PUBLISH_CHUNK_SIZE = 500

@app.post('/v1/datasets/upload')
def upload(request: Request, file: UploadFile = File(...),
                 parser_policy: str = Form('runtime_first'),
                 parser_sample_size: int = Form(10000),
                 parser_min_quality: float = Form(0.90),
                 parser_seed: int = Form(42),
                 parser_sampling_strategy: str = Form('random'),
                 ground_truth_templates: str | None = Form(None),
                 source_type: str = Form('upload'),
                 source_reference: str | None = Form(None)):
    key = authenticate_api_key(request)
    if source_type not in {'upload', 'loghub'}:
        raise HTTPException(422, 'source_type must be upload or loghub')
    if source_type == 'loghub' and source_reference not in LOGHUB_CATALOG:
        raise HTTPException(422, 'source_reference must be a known LogHub catalog ID')
    if source_type == 'upload' and source_reference:
        raise HTTPException(422, 'source_reference is only valid for LogHub imports')
    if parser_policy not in {'runtime_first', 'quality_constrained', 'multi_objective'}:
        raise HTTPException(422, 'Unsupported parser_policy')
    if parser_sampling_strategy not in {'first_n', 'random', 'stratified'}:
        raise HTTPException(422, 'Unsupported parser_sampling_strategy')
    if parser_policy in {'quality_constrained', 'multi_objective'} and not ground_truth_templates:
        raise HTTPException(422, 'This parser policy requires ground_truth_templates as a JSON array aligned with non-empty log lines')
    parsed_ground_truth = None
    if ground_truth_templates is not None:
        try:
            parsed_ground_truth = json.loads(ground_truth_templates)
            if not isinstance(parsed_ground_truth, list) or not all(isinstance(item, str) for item in parsed_ground_truth):
                raise ValueError('expected an array of strings')
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, 'ground_truth_templates must be a JSON array of strings') from exc
    if not 0 <= parser_min_quality <= 1:
        raise HTTPException(422, 'parser_min_quality must be between 0 and 1')
    if not 1 <= parser_sample_size <= 10000:
        raise HTTPException(422, 'parser_sample_size must be between 1 and 10000')
    if not 0 <= parser_seed <= 2147483647:
        raise HTTPException(422, 'parser_seed must be a non-negative 32-bit integer')
    if not file.filename or not file.filename.lower().endswith(('.log', '.txt', '.csv')):
        raise HTTPException(415, 'Supported formats: .log, .txt, .csv')
    try:
        byte_size, digest, line_count = inspect_upload_file(file.file, MAX_UPLOAD_BYTES)
    except ValueError as exc:
        if 'upload exceeds' in str(exc):
            raise HTTPException(413, f'Maximum upload size is {MAX_UPLOAD_BYTES} bytes') from exc
        raise HTTPException(400, 'File must be UTF-8 encoded') from exc
    except UnicodeDecodeError as exc:
        raise HTTPException(400, 'File must be UTF-8 encoded') from exc
    did = str(uuid.uuid4())
    if parsed_ground_truth is not None and len(parsed_ground_truth) != line_count:
        raise HTTPException(422, f'ground_truth_templates must contain exactly {line_count} labels for non-empty log lines')
    object_key = None
    try:
        object_key = put_raw_dataset_file(key['tenant_id'], did, file.filename, file.file, byte_size, file.content_type or 'text/plain')
        # Dataset metadata and its durable publication job commit atomically.
        with db().begin() as conn:
            conn.execute(text('''INSERT INTO datasets
                (id,tenant_id,name,source_type,source_reference,source_metadata,status,line_count,object_key,byte_size,sha256,content_type,parser_policy,parser_sample_size,parser_min_quality,parser_seed,parser_sampling_strategy,parser_ground_truth)
                VALUES(:id,:tenant,:name,:source_type,:source_reference,CAST(:source_metadata AS jsonb),:status,:count,:object_key,:size,:sha256,:content_type,:parser_policy,:sample_size,:min_quality,:seed,:sampling_strategy,CAST(:ground_truth AS jsonb))'''),
                {'id': did, 'tenant': key['tenant_id'], 'name': file.filename, 'source_type': source_type,
                 'source_reference': source_reference, 'source_metadata': json.dumps(LOGHUB_CATALOG.get(source_reference, {})),
                 'status': 'queued' if line_count else 'completed', 'count': line_count,
                 'object_key': object_key, 'size': byte_size, 'sha256': digest,
                 'content_type': file.content_type or 'text/plain', 'parser_policy': parser_policy,
                 'sample_size': parser_sample_size, 'min_quality': parser_min_quality, 'seed': parser_seed,
                 'sampling_strategy': parser_sampling_strategy,
                 'ground_truth': json.dumps(parsed_ground_truth) if parsed_ground_truth is not None else None})
            if line_count:
                conn.execute(text("INSERT INTO dataset_publish_jobs (dataset_id,tenant_id,processing_attempt,next_line_number,status) VALUES (:id,:tenant,1,1,'queued')"),
                    {'id': did, 'tenant': key['tenant_id']})
            else:
                conn.execute(text("UPDATE datasets SET completed_at=now() WHERE id=:id"), {'id': did})
    except Exception as exc:
        if object_key:
            try:
                delete_raw_dataset(object_key)
            except Exception:
                pass
        raise HTTPException(503, f'Raw dataset storage or job creation unavailable: {type(exc).__name__}') from exc

    return {'dataset_id': did, 'filename': file.filename, 'lines_queued': 0,
            'lines_to_publish': line_count, 'bytes_stored': byte_size, 'sha256': digest,
            'status': 'queued' if line_count else 'completed', 'raw_artifact_preserved': True,
            'publication': 'durable_background_job', 'parser_policy': parser_policy,
            'parser_selection': 'pending_until_publisher_benchmark',
            'source_type': source_type, 'source_reference': source_reference}

@app.get('/v1/datasets')
def list_datasets(request: Request):
    key = authenticate_api_key(request)
    with db().connect() as conn:
        rows = conn.execute(text('''SELECT id,name,source_type,source_reference,source_metadata,status,line_count,processed_count,failed_count,byte_size,sha256,created_at,started_at,completed_at,error_message,parser_policy,selected_parser,selected_parser_version,parser_selected_at,deletion_requested_at,artifact_deleted_at,deleted_at
            FROM datasets WHERE tenant_id=:tenant ORDER BY created_at DESC'''), {'tenant': key['tenant_id']}).mappings().all()
    return {'items': [dict(row) for row in rows]}

@app.get('/v1/datasets/{dataset_id}')
def dataset_detail(dataset_id: str, request: Request):
    key = authenticate_api_key(request)
    with db().connect() as conn:
        row = conn.execute(text('''SELECT id,name,source_type,source_reference,source_metadata,status,line_count,processed_count,failed_count,byte_size,sha256,content_type,created_at,started_at,completed_at,error_message,parser_policy,selected_parser,selected_parser_version,parser_selected_at,deletion_requested_at,artifact_deleted_at,deleted_at
            FROM datasets WHERE id=:id AND tenant_id=:tenant'''), {'id': dataset_id, 'tenant': key['tenant_id']}).mappings().first()
    if not row:
        raise HTTPException(404, 'Dataset not found')
    return dict(row)

@app.get('/v1/datasets/{dataset_id}/benchmark')
def dataset_benchmark(dataset_id: str, request: Request):
    key = authenticate_api_key(request)
    with db().connect() as conn:
        row = conn.execute(text("""SELECT parser_policy,selected_parser,selected_parser_version,
            parser_benchmark,parser_selected_at FROM datasets
            WHERE id=:id AND tenant_id=:tenant"""),
            {'id': dataset_id, 'tenant': key['tenant_id']}).mappings().first()
    if not row:
        raise HTTPException(404, 'Dataset not found')
    if not row['selected_parser']:
        return {'dataset_id': dataset_id, 'status': 'pending'}
    return {'dataset_id': dataset_id, 'status': 'selected', 'policy': row['parser_policy'],
            'selected_parser': row['selected_parser'],
            'selected_parser_version': row['selected_parser_version'],
            'selected_at': row['parser_selected_at'], 'benchmark': row['parser_benchmark']}


@app.get('/v1/datasets/{dataset_id}/progress')
def dataset_progress(dataset_id: str, request: Request):
    key = authenticate_api_key(request)
    with db().connect() as conn:
        row = conn.execute(text("""SELECT d.id,d.status,d.line_count,d.processed_count,d.failed_count,
            CASE WHEN d.line_count=0 THEN 100.0 ELSE ROUND(d.processed_count*100.0/d.line_count,2) END AS progress_percent,
            d.started_at,d.completed_at,d.error_message,j.next_line_number,j.published_bytes,j.total_publish_ms,j.last_batch_ms,
            j.started_at AS publishing_started_at,j.last_batch_at
            FROM datasets d LEFT JOIN dataset_publish_jobs j ON j.dataset_id=d.id
            WHERE d.id=:id AND d.tenant_id=:tenant"""),
            {'id': dataset_id, 'tenant': key['tenant_id']}).mappings().first()
    if not row:
        raise HTTPException(404, 'Dataset not found')
    result = dict(row)
    result['publish_bytes_per_second'] = publication_bytes_per_second(int(result.get('published_bytes') or 0), int(result.get('total_publish_ms') or 0))
    return result


@app.post('/v1/datasets/{dataset_id}/retry')
def retry_dataset(dataset_id: str, request: Request):
    key = authenticate_api_key(request)
    with db().begin() as conn:
        row = conn.execute(text("""SELECT id,name,object_key,line_count,status,parser_policy,selected_parser
            FROM datasets WHERE id=:id AND tenant_id=:tenant FOR UPDATE"""),
            {'id': dataset_id, 'tenant': key['tenant_id']}).mappings().first()
        if not row:
            raise HTTPException(404, 'Dataset not found')
        if row['status'] != 'failed':
            raise HTTPException(409, f"Dataset cannot be retried from status {row['status']}")
        if not row['object_key']:
            raise HTTPException(409, 'This dataset has no preserved raw artifact to replay')
        conn.execute(text("DELETE FROM dataset_progress_events WHERE dataset_id=:id AND tenant_id=:tenant"),
            {'id': dataset_id, 'tenant': key['tenant_id']})
        attempt = conn.execute(text("""UPDATE datasets SET status='queued',processed_count=0,failed_count=0,
            processing_attempt=processing_attempt+1,started_at=NULL,completed_at=NULL,error_message=NULL
            WHERE id=:id AND tenant_id=:tenant RETURNING processing_attempt"""),
            {'id': dataset_id, 'tenant': key['tenant_id']}).scalar_one()
        conn.execute(text("""INSERT INTO dataset_publish_jobs
            (dataset_id,tenant_id,processing_attempt,next_line_number,next_byte_offset,status,publish_attempts,next_attempt_at,last_error)
            VALUES(:id,:tenant,:attempt,1,0,'queued',0,now(),NULL)
            ON CONFLICT(dataset_id) DO UPDATE SET
                tenant_id=EXCLUDED.tenant_id,
                processing_attempt=EXCLUDED.processing_attempt,
                next_line_number=1,next_byte_offset=0,status='queued',publish_attempts=0,
                cancel_requested=FALSE,started_at=NULL,last_batch_at=NULL,total_publish_ms=0,
                published_bytes=0,last_batch_ms=0,next_attempt_at=now(),last_error=NULL,updated_at=now()"""),
            {'id': dataset_id, 'tenant': key['tenant_id'], 'attempt': attempt})
    return {'dataset_id': dataset_id, 'lines_queued': 0, 'lines_to_publish': int(row['line_count']),
            'status': 'queued', 'replayed_from_verified_artifact': True,
            'publication': 'durable_background_job', 'parser_policy': row['parser_policy'],
            'parser_selection': 'previous_benchmark_reused' if row['selected_parser'] else 'pending_until_publisher_benchmark'}


@app.post('/v1/datasets/{dataset_id}/cancel')
def cancel_dataset(dataset_id: str, request: Request):
    """Request cooperative cancellation at the next publisher batch boundary."""
    key = authenticate_api_key(request)
    with db().begin() as conn:
        row = conn.execute(text("""SELECT d.status,j.status AS job_status
            FROM datasets d JOIN dataset_publish_jobs j ON j.dataset_id=d.id
            WHERE d.id=:id AND d.tenant_id=:tenant FOR UPDATE OF j"""),
            {'id': dataset_id, 'tenant': key['tenant_id']}).mappings().first()
        if not row:
            raise HTTPException(404, 'Dataset not found')
        if row['status'] in {'completed', 'failed', 'cancelled', 'deleting', 'deleted'} or row['job_status'] in {'published', 'failed', 'cancelled'}:
            raise HTTPException(409, f"Dataset cannot be cancelled from status {row['status']}")
        conn.execute(text("UPDATE dataset_publish_jobs SET cancel_requested=TRUE,updated_at=now() WHERE dataset_id=:id"), {'id': dataset_id})
    return {'dataset_id': dataset_id, 'status': 'cancellation_requested',
            'effective_at': 'next_publisher_batch_boundary', 'raw_artifact_preserved': True}



@app.delete('/v1/datasets/{dataset_id}')
def delete_dataset(dataset_id: str, request: Request):
    """Request durable deletion; the cleanup worker removes the MinIO object."""
    key = authenticate_api_key(request)
    with db().begin() as conn:
        row = conn.execute(text("""SELECT id,status,deleted_at,deletion_requested_at
            FROM datasets WHERE id=:id AND tenant_id=:tenant FOR UPDATE"""),
            {'id': dataset_id, 'tenant': key['tenant_id']}).mappings().first()
        if not row:
            raise HTTPException(404, 'Dataset not found')
        if row['deleted_at'] is not None:
            return {'dataset_id': dataset_id, 'status': 'deleted', 'artifact_deleted': True}
        if row['deletion_requested_at'] is not None:
            return {'dataset_id': dataset_id, 'status': 'deletion_pending', 'artifact_deleted': False}
        conn.execute(text("""UPDATE datasets SET status='deleting',deletion_requested_at=now(),
            deletion_error=NULL,completed_at=now() WHERE id=:id"""), {'id': dataset_id})
        conn.execute(text("""UPDATE dataset_publish_jobs SET cancel_requested=TRUE,updated_at=now()
            WHERE dataset_id=:id"""), {'id': dataset_id})
    return {'dataset_id': dataset_id, 'status': 'deletion_pending',
            'artifact_deleted': False, 'cleanup': 'durable_background_worker'}

@app.post('/v1/datasets/synthetic')
def synthetic(request: Request, count: int = 1000, services: int = 4):
    """Generate a raw synthetic log artifact and send it through the normal adaptive pipeline."""
    key = authenticate_api_key(request)
    if count < 1 or count > 100000:
        raise HTTPException(400, 'count must be between 1 and 100000')
    did = str(uuid.uuid4())
    names = [f'service-{i + 1}' for i in range(max(1, min(services, 30)))]
    from datetime import datetime, timedelta, timezone
    start_time = datetime.now(timezone.utc) - timedelta(seconds=count)
    lines = []
    for index in range(count):
        severity = random.choices(['INFO', 'WARN', 'ERROR'], [0.82, 0.12, 0.06])[0]
        code = random.choice([200, 200, 200, 404, 500, 503])
        service = random.choice(names)
        timestamp = (start_time + timedelta(seconds=index)).isoformat()
        lines.append(f'{timestamp} {severity} service={service} request completed status={code} latency_ms={random.randint(2, 1800)}')
    raw = ('\n'.join(lines) + '\n').encode('utf-8')
    digest = hashlib.sha256(raw).hexdigest()
    object_key = None
    try:
        object_key = put_raw_dataset(key['tenant_id'], did, f'synthetic-{count}.log', raw, 'text/plain')
        with db().begin() as conn:
            conn.execute(text("""INSERT INTO datasets
                (id,tenant_id,name,source_type,status,line_count,object_key,byte_size,sha256,
                 content_type,parser_policy,parser_sample_size,parser_min_quality,parser_seed,parser_sampling_strategy)
                VALUES(:id,:tenant,:name,'synthetic','queued',:count,:object_key,:size,:sha256,
                       'text/plain','runtime_first',10000,0.90,42,'random')"""),
                {'id': did, 'tenant': key['tenant_id'], 'name': f'Synthetic {count} events',
                 'count': count, 'object_key': object_key, 'size': len(raw), 'sha256': digest})
            conn.execute(text("""INSERT INTO dataset_publish_jobs
                (dataset_id,tenant_id,processing_attempt,next_line_number,status)
                VALUES(:id,:tenant,1,1,'queued')"""),
                {'id': did, 'tenant': key['tenant_id']})
    except Exception as exc:
        if object_key:
            try:
                delete_raw_dataset(object_key)
            except Exception:
                pass
        raise HTTPException(503, f'Synthetic dataset could not be stored or queued: {type(exc).__name__}') from exc
    return {'dataset_id': did, 'lines_queued': 0, 'lines_to_publish': count,
            'status': 'queued', 'raw_artifact_preserved': True,
            'publication': 'durable_background_job',
            'parser_selection': 'pending_until_publisher_benchmark'}

