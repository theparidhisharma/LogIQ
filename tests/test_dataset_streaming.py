import hashlib
import io

import pytest

from shared.object_storage import inspect_upload_file, sample_raw_dataset, iter_raw_dataset_lines


def test_inspect_upload_file_counts_nonempty_lines_and_rewinds():
    payload = b"INFO one\\r\n\nERROR two\nWARN three"
    stream = io.BytesIO(payload)
    size, digest, lines = inspect_upload_file(stream, max_bytes=1024, chunk_size=3)
    assert size == len(payload)
    assert digest == hashlib.sha256(payload).hexdigest()
    assert lines == 3
    assert stream.tell() == 0


def test_inspect_upload_file_enforces_limit():
    with pytest.raises(ValueError, match="exceeds"):
        inspect_upload_file(io.BytesIO(b"12345"), max_bytes=4)


def test_inspect_upload_file_rejects_invalid_utf8():
    with pytest.raises(UnicodeDecodeError):
        inspect_upload_file(io.BytesIO(bytes([73, 78, 70, 79, 32, 255])), max_bytes=100)


class FakeResponse(io.BytesIO):
    def release_conn(self):
        pass


def test_streaming_sample_verifies_checksum_and_bounds_sample(monkeypatch):
    payload = b"INFO one\nERROR two\nWARN three\nINFO four\n"
    monkeypatch.setattr("shared.object_storage.open_raw_dataset", lambda _key, offset=0: FakeResponse(payload[offset:]))
    lines, indices, total = sample_raw_dataset(
        "object", hashlib.sha256(payload).hexdigest(), 2, "first_n", 7
    )
    assert lines == ["INFO one", "ERROR two"]
    assert indices == [0, 1]
    assert total == 4


def test_streaming_batch_reads_only_requested_nonempty_lines(monkeypatch):
    payload = b"INFO one\n\nERROR two\nWARN three\n"
    monkeypatch.setattr("shared.object_storage.open_raw_dataset", lambda _key, offset=0: FakeResponse(payload[offset:]))
    assert list(iter_raw_dataset_lines("object", start_line=2, limit=1, offset=9)) == [(3, "ERROR two", 20)]


def test_streaming_sample_rejects_checksum_mismatch(monkeypatch):
    monkeypatch.setattr("shared.object_storage.open_raw_dataset", lambda _key: FakeResponse(b"INFO one\n"))
    with pytest.raises(ValueError, match="checksum"):
        sample_raw_dataset("object", "wrong", 1, "first_n", 1)


def test_streaming_batch_resumes_from_byte_offset(monkeypatch):
    payload = b"INFO one\nERROR two\nWARN three\n"
    def get_object(_key, offset=0):
        return FakeResponse(payload[offset:])
    monkeypatch.setattr("shared.object_storage.open_raw_dataset", get_object)
    batch = list(iter_raw_dataset_lines("object", start_line=2, limit=1, offset=9))
    assert batch == [(2, "ERROR two", 19)]


def test_streaming_line_reader_handles_multibyte_and_crlf_across_chunks(monkeypatch):
    payload = "INFO café\r\nERROR two\n".encode("utf-8")

    class TinyReadResponse(FakeResponse):
        def read(self, size=-1):
            return super().read(2 if size < 0 or size > 2 else size)

    monkeypatch.setattr("shared.object_storage.open_raw_dataset",
                        lambda _key, offset=0: TinyReadResponse(payload[offset:]))
    rows = list(iter_raw_dataset_lines("object", limit=10))
    assert [(n, line) for n, line, _ in rows] == [(1, "INFO café"), (2, "ERROR two")]
    assert rows[-1][2] == len(payload)


def test_streaming_reader_preserves_cursor_across_blank_lines(monkeypatch):
    payload = b"one\n\ntwo\n"
    monkeypatch.setattr("shared.object_storage.open_raw_dataset",
                        lambda _key, offset=0: FakeResponse(payload[offset:]))
    first = list(iter_raw_dataset_lines("object", start_line=1, limit=1))
    second = list(iter_raw_dataset_lines("object", start_line=first[-1][0] + 1,
                                         limit=1, offset=first[-1][2]))
    assert first == [(1, "one", 4)]
    assert second == [(3, "two", 9)]
