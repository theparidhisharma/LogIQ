from shared.dataset_utils import nonempty_line_chunks
PUBLISH_CHUNK_SIZE = 500


def test_line_chunking_preserves_original_line_numbers_and_order():
    content = 'first\n\nsecond\n third \n'
    chunks = list(nonempty_line_chunks(content, chunk_size=2))
    assert chunks == [[(1, 'first'), (3, 'second')], [(4, ' third ')]]


def test_line_chunking_never_exceeds_configured_size():
    content = '\n'.join(f'line-{i}' for i in range(1201))
    chunks = list(nonempty_line_chunks(content, chunk_size=500))
    assert [len(chunk) for chunk in chunks] == [500, 500, 201]
    flattened = [line for chunk in chunks for _, line in chunk]
    assert len(flattened) == 1201
    assert flattened[0] == 'line-0' and flattened[-1] == 'line-1200'


def test_default_publish_chunk_is_bounded():
    assert PUBLISH_CHUNK_SIZE == 500


def test_dataset_event_ids_are_stable_for_replay():
    from shared.dataset_utils import dataset_event_id
    assert dataset_event_id('dataset-123', 17) == dataset_event_id('dataset-123', 17)
    assert dataset_event_id('dataset-123', 17) != dataset_event_id('dataset-123', 18)
    assert dataset_event_id('dataset-123', 17) != dataset_event_id('dataset-456', 17)


def test_dataset_progress_is_bounded_by_line_count():
    from shared.dataset_utils import progress_percent
    assert progress_percent(0, 20) == 0.0
    assert progress_percent(5, 20) == 25.0
    assert progress_percent(20, 20) == 100.0
    assert progress_percent(25, 20) == 100.0
    assert progress_percent(-5, 20) == 0.0
    assert progress_percent(0, 0) == 100.0
