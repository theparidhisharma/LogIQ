"""MinIO-backed raw dataset artifact storage."""
import os
import time
from io import BytesIO
import hashlib

BUCKET = os.getenv('MINIO_BUCKET', 'logiq-raw-datasets')

def client():
    try:
        from minio import Minio
    except ImportError as exc:
        raise RuntimeError("MinIO SDK is not installed; install requirements.txt") from exc
    return Minio(os.getenv('MINIO_ENDPOINT', 'minio:9000'),
        access_key=os.getenv('MINIO_ACCESS_KEY', 'logiq'),
        secret_key=os.getenv('MINIO_SECRET_KEY', 'logiq-secret-change-me'),
        secure=os.getenv('MINIO_SECURE', 'false').lower() == 'true')

def ensure_bucket() -> None:
    # Compose starts the container before MinIO's API is necessarily ready.
    last_error = None
    for attempt in range(10):
        try:
            store = client()
            if not store.bucket_exists(BUCKET):
                store.make_bucket(BUCKET)
            return
        except Exception as exc:
            last_error = exc
            if attempt == 9:
                break
            time.sleep(min(1 + attempt, 5))
    raise RuntimeError("MinIO did not become ready for bucket access") from last_error

def put_raw_dataset(tenant_id: str, dataset_id: str, filename: str, raw: bytes, content_type: str) -> str:
    ensure_bucket()
    object_key = f'tenants/{tenant_id}/datasets/{dataset_id}/raw'
    client().put_object(BUCKET, object_key, BytesIO(raw), length=len(raw),
        content_type=content_type or 'application/octet-stream',
        metadata={'x-amz-meta-original-filename': filename[:200]})
    return object_key

def delete_raw_dataset(object_key: str) -> None:
    client().remove_object(BUCKET, object_key)


def get_raw_dataset(object_key: str) -> bytes:
    response = client().get_object(BUCKET, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def inspect_upload_file(fileobj, max_bytes: int, chunk_size: int = 1024 * 1024):
    """Validate UTF-8 and calculate byte size, SHA-256 and non-empty line count in bounded memory."""
    import codecs
    decoder = codecs.getincrementaldecoder("utf-8-sig")()
    digest = hashlib.sha256()
    total = lines = 0
    pending = ""
    fileobj.seek(0)
    while True:
        chunk = fileobj.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ValueError("upload exceeds configured size limit")
        digest.update(chunk)
        text = decoder.decode(chunk)
        combined = pending + text
        pieces = combined.split("\n")
        pending = pieces.pop()
        lines += sum(1 for line in pieces if line.rstrip("\r").strip())
    tail = decoder.decode(b"", final=True)
    pending += tail
    if pending.rstrip("\r").strip():
        lines += 1
    fileobj.seek(0)
    return total, digest.hexdigest(), lines


def put_raw_dataset_file(tenant_id: str, dataset_id: str, filename: str, fileobj, length: int, content_type: str) -> str:
    """Upload a seekable file object to MinIO without materializing it as bytes."""
    ensure_bucket()
    object_key = f"tenants/{tenant_id}/datasets/{dataset_id}/raw"
    fileobj.seek(0)
    client().put_object(BUCKET, object_key, fileobj, length=length,
        content_type=content_type or "application/octet-stream",
        metadata={"x-amz-meta-original-filename": filename[:200]})
    fileobj.seek(0)
    return object_key


def open_raw_dataset(object_key: str):
    """Return a MinIO streaming response; caller must close and release it."""
    return client().get_object(BUCKET, object_key)


def _iter_decoded_lines(response, chunk_size: int = 1024 * 1024):
    """Incrementally decode UTF-8 text lines from an HTTP response-like stream."""
    import codecs
    decoder = codecs.getincrementaldecoder("utf-8-sig")()
    pending = ""
    while True:
        chunk = response.read(chunk_size)
        if not chunk:
            break
        pieces = (pending + decoder.decode(chunk)).split("\n")
        pending = pieces.pop()
        for line in pieces:
            yield line.rstrip("\r")
    pending += decoder.decode(b"", final=True)
    if pending:
        yield pending.rstrip("\r")


def iter_raw_dataset_lines(object_key: str, start_line: int = 1, limit: int | None = None, offset: int = 0):
    """Yield (source line number, line, next byte offset) from a MinIO object range."""
    response = open_raw_dataset(object_key, offset=offset)
    byte_cursor = offset
    line_number = start_line
    emitted = 0
    pending = b""
    try:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            pieces = (pending + chunk).split(b"\n")
            pending = pieces.pop()
            consumed_in_chunk = 0
            for raw_line in pieces:
                consumed_in_chunk += len(raw_line) + 1
                end_offset = byte_cursor + consumed_in_chunk
                line = raw_line.rstrip(b"\r").decode("utf-8-sig" if line_number == 1 else "utf-8")
                current_line = line_number
                line_number += 1
                if line.strip():
                    yield current_line, line, end_offset
                    emitted += 1
                    if limit is not None and emitted >= limit:
                        return
            byte_cursor += consumed_in_chunk
        if pending:
            line = pending.rstrip(b"\r").decode("utf-8-sig" if line_number == 1 else "utf-8")
            if line.strip():
                yield line_number, line, byte_cursor + len(pending)
    finally:
        response.close()
        response.release_conn()


def sample_raw_dataset(object_key: str, expected_sha256: str, size: int, strategy: str, seed: int):
    """Verify the immutable artifact and construct a bounded-memory parser sample."""
    import hashlib, random
    from shared.common import parse_line
    response = open_raw_dataset(object_key)
    digest = hashlib.sha256()
    try:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk: break
            digest.update(chunk)
    finally:
        response.close()
        response.release_conn()
    if digest.hexdigest() != expected_sha256:
        raise ValueError("stored dataset artifact checksum mismatch")

    response = open_raw_dataset(object_key)
    rng = random.Random(seed)
    sample, buckets, bucket_counts, total = [], {}, {}, 0
    try:
        for number, line in enumerate(_iter_decoded_lines(response), start=1):
            if not line.strip(): continue
            total += 1
            item = (total - 1, line)
            if strategy == "first_n":
                if len(sample) < size: sample.append(item)
            elif strategy == "random":
                if len(sample) < size: sample.append(item)
                else:
                    index = rng.randrange(total)
                    if index < size: sample[index] = item
            elif strategy == "stratified":
                _, severity, _ = parse_line(line)
                bucket = buckets.setdefault(severity, [])
                bucket_counts[severity] = bucket_counts.get(severity, 0) + 1
                if len(bucket) < size: bucket.append(item)
                else:
                    index = rng.randrange(bucket_counts[severity])
                    if index < size: bucket[index] = item
            else:
                raise ValueError("unsupported sampling strategy")
    finally:
        response.close()
        response.release_conn()
    if strategy == "stratified":
        # Keep a balanced representation of the observed severity groups.
        sample = []
        ordered = [iter(values) for values in buckets.values()]
        while len(sample) < size and ordered:
            remaining = []
            for iterator in ordered:
                try:
                    sample.append(next(iterator))
                    remaining.append(iterator)
                except StopIteration:
                    pass
                if len(sample) >= size:
                    break
            ordered = remaining
    sample.sort(key=lambda item: item[0])
    return [line for _, line in sample], [number for number, _ in sample], total
