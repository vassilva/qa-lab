"""BDD steps for trading: Order Entry Gateway, Matching Engine and Market Data."""

from behave import step

SIDES = {"buy": "BUY", "sell": "SELL"}
BOOK_SIDES = {"bid": "bids", "ask": "asks"}


def _price(text):
    return None if text == "market" else float(text)


def submit(context, alias, side, qty, symbol, price):
    body = {"symbol": symbol, "side": SIDES[side], "qty": qty, "price": price}
    r = context.api.post("/api/orders", body)
    assert r.status_code in (201, 422), f"Unexpected response {r.status_code}: {r.text}"
    context.last_response = r
    context.orders[alias] = r.json()["order"]
    return r


def current_order(context, alias):
    assert alias in context.orders, f"Order '{alias}' was not created in this scenario"
    order_id = context.orders[alias]["order_id"]
    r = context.api.get(f"/api/orders/{order_id}")
    assert r.status_code == 200, f"Order {order_id} not found: {r.text}"
    return r.json()


# ---------------------------------------------------------------------- background
@step('a clean market with business date "{day}"')
def step_clean_market(context, day):
    r = context.api.post("/api/reset")
    assert r.status_code == 200, f"Could not reset the environment: {r.text}"
    r = context.api.post("/api/business-date", {"date": day})
    assert r.status_code == 200, f"Could not set the business date {day}: {r.text}"


# ---------------------------------------------------------------------- orders
@step('an existing order "{alias}" to {side} {qty:d} "{symbol}" at {price} EUR')
def step_existing_order(context, alias, side, qty, symbol, price):
    r = submit(context, alias, side, qty, symbol, _price(price))
    assert r.status_code == 201, f"Setup order '{alias}' was rejected: {r.text}"


@step('order "{alias}" to {side} {qty:d} "{symbol}" at {price} EUR is submitted')
def step_submit_order(context, alias, side, qty, symbol, price):
    submit(context, alias, side, qty, symbol, _price(price))


@step('order "{alias}" to {side} {qty:d} "{symbol}" at market is submitted')
def step_submit_market_order(context, alias, side, qty, symbol):
    submit(context, alias, side, qty, symbol, None)


@step('the participant tries to cancel order "{alias}"')
def step_cancel(context, alias):
    context.last_response = context.api.delete(f"/api/orders/{context.orders[alias]['order_id']}")


# ---------------------------------------------------------------------- checks
@step('order "{alias}" has status "{status}"')
def step_order_status(context, alias, status):
    order = current_order(context, alias)
    assert order["status"] == status, (
        f"Order {alias} ({order['order_id']}): expected {status}, got {order['status']} "
        f"(reason: {order.get('reject_reason')})")


@step('order "{alias}" has status "{status}" with {left:d} remaining')
def step_order_status_and_remaining(context, alias, status, left):
    order = current_order(context, alias)
    assert (order["status"], order["remaining"]) == (status, left), (
        f"Order {alias}: expected {status} with {left} remaining, "
        f"got {order['status']} with {order['remaining']}")


@step('order "{alias}" is rejected with reason "{reason}"')
def step_rejected(context, alias, reason):
    assert context.last_response.status_code == 422, (
        f"Expected HTTP 422, got {context.last_response.status_code}: {context.last_response.text}")
    order = current_order(context, alias)
    assert (order["status"], order["reject_reason"]) == ("REJECTED", reason), (
        f"Expected REJECTED / {reason}, got {order['status']} / {order['reject_reason']}")


@step("the cancellation is refused")
def step_cancel_refused(context):
    assert context.last_response.status_code == 409, (
        f"Expected HTTP 409, got {context.last_response.status_code}: {context.last_response.text}")


@step("there is {n:d} trade of {qty:d} shares at {price} EUR")
def step_one_trade(context, n, qty, price):
    trades = context.api.get("/api/trades").json()
    assert len(trades) == n, f"Expected {n} trade(s), got {len(trades)}: {trades}"
    last = trades[0]
    assert (last["qty"], last["price"]) == (qty, float(price)), (
        f"Expected {qty} at {price}, got {last['qty']} at {last['price']}")


@step("there are {n:d} trades")
def step_n_trades(context, n):
    trades = context.api.get("/api/trades").json()
    assert len(trades) == n, f"Expected {n} trades, got {len(trades)}"


@step("there are no trades")
def step_no_trades(context):
    trades = context.api.get("/api/trades").json()
    assert trades == [], f"No trade was expected: {trades}"


@step('the {book_side} side of "{symbol}" is empty')
def step_empty_book(context, book_side, symbol):
    book = context.api.get(f"/api/book/{symbol}").json()
    entries = book[BOOK_SIDES[book_side]]
    assert entries == [], f"The {book_side} side of {symbol} should be empty: {entries}"
