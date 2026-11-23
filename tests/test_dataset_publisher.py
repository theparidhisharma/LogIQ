from shared.dataset_utils import dataset_event_id, nonempty_line_chunks, kafka_key_bytes, next_nonempty_lines


def test_kafka_key_serializer_accepts_application_ids_and_bytes():
    assert kafka_key_bytes("checkout-api") == b"checkout-api"
    assert kafka_key_bytes(b"dataset-1") == b"dataset-1"
    assert kafka_key_bytes(None) is None


def test_kafka_key_serializer_rejects_unexpected_types():
    try:
        kafka_key_bytes(42)
    except TypeError as exc:
        assert "str, bytes, or None" in str(exc)
    else:
        raise AssertionError("unexpected key type should be rejected")


def test_replaying_a_published_batch_keeps_event_ids_stable():
    dataset_id = "dataset-restart-test"
    first_pass = [dataset_event_id(dataset_id, n) for n in range(1, 501)]
    replay = [dataset_event_id(dataset_id, n) for n in range(1, 501)]
    assert first_pass == replay
    assert len(set(first_pass)) == 500


def test_publisher_cursor_uses_source_line_numbers_with_blank_lines():
    content = "one\n\ntwo\nthree\n"
    lines = [pair for chunk in nonempty_line_chunks(content, 2) for pair in chunk]
    assert lines == [(1, "one"), (3, "two"), (4, "three")]
    cursor = lines[1][0] + 1
    resumed = [line for line_no, line in lines if line_no >= cursor]
    assert resumed == ["three"]


def test_next_page_resumes_after_cursor_without_reordering_or_repeating():
    content = "a\n\nb\nc\nd\n"
    first = next_nonempty_lines(content, 1, 2)
    second = next_nonempty_lines(content, first[-1][0] + 1, 2)
    assert first == [(1, "a"), (3, "b")]
    assert second == [(4, "c"), (5, "d")]


def test_next_page_returns_short_final_batch():
    assert next_nonempty_lines("a\nb\n", 2, 500) == [(2, "b")]


def test_publication_throughput_uses_measured_bytes_and_elapsed_time():
    from shared.dataset_utils import publication_bytes_per_second
    assert publication_bytes_per_second(2_000, 1_000) == 2000.0
    assert publication_bytes_per_second(500, 0) == 0.0


def test_publication_throughput_rejects_invalid_counters():
    from shared.dataset_utils import publication_bytes_per_second
    import pytest
    with pytest.raises(ValueError):
        publication_bytes_per_second(-1, 100)
    with pytest.raises(ValueError):
        publication_bytes_per_second(100, -1)
