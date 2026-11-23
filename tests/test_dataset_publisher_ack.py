import pytest

from services.dataset.publisher_worker import publish_events_acknowledged


class Future:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.waited = False

    def get(self, timeout=None):
        self.waited = True
        if self.error:
            raise self.error
        return self.result


class FakeProducer:
    def __init__(self, futures):
        self.futures = iter(futures)
        self.sent = []
        self.flushed = False

    def send(self, topic, payload, key=None):
        self.sent.append((topic, payload, key))
        return next(self.futures)

    def flush(self, timeout=None):
        self.flushed = True


def test_publisher_waits_for_each_kafka_ack_before_cursor_can_advance():
    futures = [Future("ack-1"), Future("ack-2")]
    producer = FakeProducer(futures)
    count = publish_events_acknowledged(producer, [
        ("logs.raw", {"event_id": "1"}, "dataset"),
        ("logs.raw", {"event_id": "2"}, "dataset"),
    ])
    assert count == 2
    assert producer.flushed
    assert all(f.waited for f in futures)
    assert [item[2] for item in producer.sent] == ["dataset", "dataset"]


def test_kafka_record_failure_propagates_and_prevents_cursor_commit():
    futures = [Future("ack-1"), Future(error=TimeoutError("broker timeout"))]
    producer = FakeProducer(futures)
    with pytest.raises(TimeoutError, match="broker timeout"):
        publish_events_acknowledged(producer, [
            ("logs.raw", {"event_id": "1"}, "dataset"),
            ("logs.raw", {"event_id": "2"}, "dataset"),
        ])
    assert producer.flushed
    assert all(f.waited for f in futures)
