"""Pure helpers for bounded dataset processing."""
from io import StringIO
def nonempty_line_chunks(content: str, chunk_size: int = 500):
    """Yield bounded chunks of (1-based source line number, line) pairs."""
    if chunk_size < 1:
        raise ValueError('chunk_size must be positive')
    chunk = []
    for line_number, line in enumerate(StringIO(content), start=1):
        line = line.rstrip("\r\n")
        if line.strip():
            chunk.append((line_number, line))
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
    if chunk:
        yield chunk


def dataset_event_id(dataset_id: str, line_number: int) -> str:
    """Stable idempotency key for a source line across replay attempts."""
    import uuid
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f'logiq:{dataset_id}:{line_number}'))


def progress_percent(processed: int, total: int) -> float:
    """Return bounded dataset completion percentage."""
    if total <= 0:
        return 100.0
    return round(min(max(processed, 0), total) * 100.0 / total, 2)


def kafka_key_bytes(key):
    """Normalize Kafka keys supplied as strings or bytes."""
    if key is None:
        return None
    if isinstance(key, bytes):
        return key
    if isinstance(key, str):
        return key.encode("utf-8")
    raise TypeError("Kafka message keys must be str, bytes, or None")


def next_nonempty_lines(content: str, start_line: int, limit: int):
    """Return the next bounded page of non-empty source lines at/after a cursor."""
    if start_line < 1 or limit < 1:
        raise ValueError("start_line and limit must be positive")
    result = []
    for chunk in nonempty_line_chunks(content, min(limit, 5000)):
        for line_number, line in chunk:
            if line_number >= start_line:
                result.append((line_number, line))
                if len(result) >= limit:
                    return result
    return result


def publication_bytes_per_second(published_bytes: int, elapsed_ms: int) -> float:
    """Compute measured publisher throughput; zero when no publish time is recorded."""
    if published_bytes < 0 or elapsed_ms < 0:
        raise ValueError("published_bytes and elapsed_ms must be non-negative")
    if elapsed_ms == 0:
        return 0.0
    return round(published_bytes * 1000.0 / elapsed_ms, 2)
