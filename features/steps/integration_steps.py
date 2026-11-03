"""BDD steps for integration between systems: contract, idempotency, dead letter queue, Settlement and T2S failures."""

import os
import sys

from behave import step

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.contracts import validate_trade_executed  # noqa: E402
from _helpers import eventually, instruction  # noqa: E402


def settlement_health(context):
    return context.api.get("/api/integration").json()["settlement"]


@step("the published event follows the TradeExecuted v1 contract")
def step_contract(context):
    tid = context.trade["trade_id"]
    ins = instruction(context)
    # The instruction is built from the event Settlement received, so its fields come from that event
    assert (ins["trade_id"], ins["qty"], ins["symbol"]) == (tid, context.trade["qty"], context.trade["symbol"])
    assert round(float(ins["amount"]), 2) == round(context.trade["qty"] * context.trade["price"], 2)
    assert len(ins["event_id"]) == 32


@step("the trade event is delivered again")
def step_replay(context):
    r = context.api.post(f"/api/integration/replay/{context.trade['trade_id']}")
    assert r.status_code == 200, r.text
    eventually(lambda: settlement_health(context)["consumer"]["duplicates"] >= 1,
               "Settlement did not receive the duplicate event")


@step("the trade still has a single settlement instruction")
def step_single(context):
    rows = context.api.get(f"/api/settlement/instructions?trade_id={context.trade['trade_id']}").json()
    assert len(rows) == 1, f"Expected 1 instruction, found {len(rows)}: {rows}"


@step("a message with quantity 0 and no event identifier is published")
def step_invalid(context):
    payload = {"event_type": "TradeExecuted", "schema_version": 1, "generation": 0,
               "trade": {"trade_id": "T99999", "symbol": "EDP", "qty": 0, "price": 4.5}}
    assert validate_trade_executed(payload), "the test message should be invalid"
    r = context.api.post("/api/integration/publish-raw", payload)
    assert r.status_code == 200, r.text


@step("the message appears in the Settlement rejected events")
def step_rejected(context):
    eventually(lambda: settlement_health(context)["consumer"]["rejected"] >= 1,
               "Settlement did not reject the invalid message")


@step("there are no settlement instructions")
def step_no_instructions(context):
    rows = context.api.get("/api/settlement/instructions").json()
    assert rows == [], f"No instruction was expected: {rows}"


@step("Settlement has stopped consuming events")
def step_pause(context):
    base = os.environ.get("SETTLEMENT_URL", "http://localhost:8001")
    r = context.api.session.post(f"{base}/api/consumer/pause", timeout=10)
    assert r.status_code == 200, r.text
    context.settlement_url = base


@step("Settlement starts consuming events again")
def step_resume(context):
    r = context.api.session.post(f"{context.settlement_url}/api/consumer/resume", timeout=10)
    assert r.status_code == 200, r.text


@step('a trade of {qty:d} "{symbol}" at {price} EUR is executed without waiting for Settlement')
def step_trade_no_wait(context, qty, symbol, price):
    for side in ("SELL", "BUY"):
        r = context.api.post("/api/orders", {"symbol": symbol, "side": side, "qty": qty, "price": float(price)})
        assert r.status_code == 201, r.text
    context.trade = r.json()["trades"][0]


@step("the reconciliation shows the trade missing in Settlement")
def step_missing(context):
    r = context.api.get("/api/reconciliation").json()
    assert context.trade["trade_id"] in r["missing_in_settlement"], r


@step('T2S rejects the instructions for "{symbol}"')
def step_t2s_rejects(context, symbol):
    r = context.api.post("/api/t2s/mode", {"mode": "reject_symbol", "symbol": symbol})
    assert r.status_code == 200, r.text


@step("T2S is unavailable")
def step_t2s_down(context):
    assert context.api.post("/api/t2s/mode", {"mode": "unavailable"}).status_code == 200


@step("T2S is back to normal")
def step_t2s_normal(context):
    assert context.api.post("/api/t2s/mode", {"mode": "normal"}).status_code == 200
