"""BDD steps for T+2 settlement and cross-system reconciliation."""

import os
import sys

from behave import step

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _helpers import eventually, instruction  # noqa: E402


@step('a trade of {qty:d} "{symbol}" at {price} EUR is executed')
def step_trade(context, qty, symbol, price):
    sell = context.api.post("/api/orders", {"symbol": symbol, "side": "SELL", "qty": qty, "price": float(price)})
    buy = context.api.post("/api/orders", {"symbol": symbol, "side": "BUY", "qty": qty, "price": float(price)})
    assert sell.status_code == 201 and buy.status_code == 201, f"Orders rejected: {sell.text} / {buy.text}"
    trades = buy.json()["trades"]
    assert len(trades) == 1, f"Expected 1 trade, got {trades}"
    context.trade = trades[0]
    instruction(context)                     # wait until Settlement receives the event


@step('a settlement instruction is created for "{day}" with status "{status}"')
def step_instruction_created(context, day, status):
    ins = instruction(context)
    assert (ins["intended_settlement_date"], ins["status"]) == (day, status), (
        f"Expected {day} / {status}, got {ins['intended_settlement_date']} / {ins['status']} "
        f"(traded on {ins['trade_date']})")


@step("the end of day is run")
def step_eod(context):
    r = context.api.post("/api/eod")
    assert r.status_code == 200, f"End of day failed: {r.text}"
    context.last_response = r


@step("the end of day is run {n:d} times")
def step_n_eod(context, n):
    for _ in range(n):
        step_eod(context)


@step('the instruction has status "{status}"')
def step_instruction_status(context, status):
    ins = instruction(context)
    assert ins["status"] == status, f"Expected {status}, got {ins['status']}"


@step('the instruction is settled on "{day}"')
def step_settled(context, day):
    ins = instruction(context)
    assert (ins["status"], ins["settled_on"]) == ("SETTLED", day), (
        f"Expected SETTLED on {day}, got {ins['status']} on {ins['settled_on']}")


@step("the instruction is put on hold")
def step_hold(context):
    r = context.api.post(f"/api/settlement/instructions/{instruction(context)['instruction_id']}/hold")
    assert r.status_code == 200, f"Hold refused: {r.text}"


@step("the instruction is released")
def step_release(context):
    r = context.api.post(f"/api/settlement/instructions/{instruction(context)['instruction_id']}/release")
    assert r.status_code == 200, f"Release refused: {r.text}"


@step('the business date becomes "{day}"')
@step('the business date is still "{day}"')
def step_business_date(context, day):
    current = context.api.get("/api/business-date").json()["business_date"]
    assert current == day, f"Expected business date {day}, got {current}"


@step('someone tries to set the business date to "{day}"')
def step_set_date(context, day):
    context.last_response = context.api.post("/api/business-date", {"date": day})


@step("the request is refused with status {code:d}")
def step_refused(context, code):
    assert context.last_response.status_code == code, (
        f"Expected HTTP {code}, got {context.last_response.status_code}: {context.last_response.text}")


@step("every trade has a settlement instruction")
@step("Trading and Settlement reconcile with no differences")
def step_reconciliation(context):
    r = eventually(lambda: (lambda x: x if x.get("ok") else None)(context.api.get("/api/reconciliation").json()),
                   "the cross-system reconciliation still shows differences")
    assert r["ok"], r


@step("the executed quantity of each order matches the trades")
def step_quantities(context):
    rows = context.api.query(
        "SELECT o.order_id, o.qty, o.remaining, COALESCE(SUM(t.qty), 0) AS executed "
        "FROM orders o LEFT JOIN trades t ON o.order_id IN (t.buy_order_id, t.sell_order_id) "
        "WHERE o.status <> 'REJECTED' "
        "GROUP BY o.order_id, o.qty, o.remaining "
        "HAVING o.qty - o.remaining <> COALESCE(SUM(t.qty), 0)")
    assert rows == [], f"Orders whose executed quantity does not match the trades: {rows}"
