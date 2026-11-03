"""Helpers shared by the BDD steps (no steps here: nothing is registered in behave)."""

import time

WAIT_SECONDS = 15     # Settlement receives trades as messages (Kafka): the instruction appears within moments


def eventually(fn, what, timeout=WAIT_SECONDS):
    """Retries fn() until it returns a truthy value (eventual consistency between systems)."""
    deadline, last = time.time() + timeout, None
    while time.time() < deadline:
        last = fn()
        if last:
            return last
        time.sleep(0.3)
    raise AssertionError(f"After {timeout}s: {what} (last value: {last})")


def instruction(context):
    assert context.trade, "No trade was executed in this scenario"
    tid = context.trade["trade_id"]
    rows = eventually(lambda: context.api.get(f"/api/settlement/instructions?trade_id={tid}").json(),
                      f"Settlement did not receive trade {tid}")
    assert len(rows) == 1, f"Expected 1 instruction for {tid}, found {len(rows)}"
    return rows[0]
