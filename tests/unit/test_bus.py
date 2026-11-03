"""Bus semantics (FileBus): in-order delivery, commit only after processing, redelivery on failures."""

import time

from app.bus import FileBus, MemoryBus, RetryableError


def _wait(cond, timeout=5):
    end = time.time() + timeout
    while time.time() < end and not cond():
        time.sleep(0.05)
    return cond()


def test_filebus_delivers_in_order(tmp_path):
    bus, got = FileBus(str(tmp_path / "bus.db")), []
    bus.start_consumer("t", "g1", got.append)
    for i in range(5):
        bus.publish("t", f"k{i}", {"n": i})
    assert _wait(lambda: len(got) == 5)
    assert [m["n"] for m in got] == [0, 1, 2, 3, 4]


def test_filebus_redelivers_after_temporary_failure(tmp_path):
    bus, got, failures = FileBus(str(tmp_path / "bus.db")), [], {"n": 2}

    def handler(msg):
        if failures["n"]:
            failures["n"] -= 1
            raise RetryableError("database down")
        got.append(msg)

    bus.start_consumer("t", "g1", handler)
    bus.publish("t", "k", {"n": 1})
    assert _wait(lambda: got == [{"n": 1}])          # delivered after two failures, successfully only once


def test_filebus_different_groups_receive_all_messages(tmp_path):
    bus, a, b = FileBus(str(tmp_path / "bus.db")), [], []
    bus.publish("t", "k", {"n": 1})
    bus.start_consumer("t", "ga", a.append)
    bus.start_consumer("t", "gb", b.append)
    assert _wait(lambda: a == [{"n": 1}] and b == [{"n": 1}])


def test_memorybus_synchronous_delivery_and_pause():
    bus, got = MemoryBus(), []
    bus.start_consumer("t", "g", got.append)
    bus.publish("t", "k", {"n": 1})
    bus.paused.add("t")
    bus.publish("t", "k", {"n": 2})
    assert got == [{"n": 1}] and len(bus.messages) == 2


def test_kafkabus_only_ready_after_partition_assignment(monkeypatch):
    """DEF-015: the consumer is ready only when Kafka assigns it the partition (not just when it connects)."""
    import threading
    import kafka
    from app.bus import KafkaBus

    assigned_now, release = threading.Event(), threading.Event()
    got = []

    class FakeMessage:
        topic, partition, offset, value = "trades.executed", 0, 0, b'{"n": 1}'

    class FakeConsumer:
        def __init__(self, *args, **kwargs):
            assert kwargs["session_timeout_ms"] == 6000 and kwargs["enable_auto_commit"] is False
            self.listener = None

        def subscribe(self, topics, listener=None):
            assert topics == ["trades.executed"]
            self.listener = listener

        def __iter__(self):
            assigned_now.wait(5)                       # the coordinator assigns the partition later
            self.listener.on_partitions_assigned([kafka.TopicPartition("trades.executed", 0)])
            yield FakeMessage()
            release.wait(5)                            # keep the consumer "alive" until the test ends

        def commit(self):
            pass

    monkeypatch.setattr(kafka, "KafkaConsumer", FakeConsumer)
    bus = KafkaBus("kafka:9092")
    bus.start_consumer("trades.executed", "settlement-service", got.append)
    assert _wait(lambda: True) and not bus.ready("trades.executed")     # connected, but no partition yet
    assigned_now.set()
    assert _wait(lambda: bus.ready("trades.executed"))
    assert _wait(lambda: got == [{"n": 1}])
    release.set()
