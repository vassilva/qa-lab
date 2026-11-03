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
