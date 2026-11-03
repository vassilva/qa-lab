"""
Integration tests Trading ↔ Settlement ↔ T2S and contract tests (TradeExecuted v1).
They run in the same process, with the in-memory bus; the behaviour is the same as with Kafka.
"""

import copy
import json

import pytest

from app.contracts import validate_trade_executed


def _trade(client, symbol="EDP", qty=100, price=4.50):
    client.post("/api/orders", json={"symbol": symbol, "side": "SELL", "qty": qty, "price": price})
    r = client.post("/api/orders", json={"symbol": symbol, "side": "BUY", "qty": qty, "price": price})
    return r.get_json()["trades"][0]


def _instructions(client, **filters):
    qs = "&".join(f"{k}={v}" for k, v in filters.items())
    return client.get("/api/settlement/instructions" + (f"?{qs}" if qs else "")).get_json()


def _published_event(services, trade_id):
    server = services[0]
    with server.lock:
        ev = server.database.outbox_event_for_trade(trade_id)
        server.database.rollback()
    return json.loads(ev["payload"])


# ---------------------------------------------------------------------- contract
def test_published_event_follows_the_contract(client, services):
    trade = _trade(client)
    event = _published_event(services, trade["trade_id"])
    assert validate_trade_executed(event) == []
    assert event["trade"] == {k: trade[k] for k in event["trade"]}


@pytest.mark.parametrize("mutate, error", [
    (lambda e: e.pop("event_id"), "missing required field: event_id"),
    (lambda e: e["trade"].update(qty=0), "$.trade.qty: 0 < minimum 1"),
    (lambda e: e["trade"].update(price="4.50"), "$.trade.price: expected type number"),
    (lambda e: e["trade"].update(trade_date="06/11/2026"), "$.trade.trade_date"),
    (lambda e: e.update(schema_version=2), "$.schema_version: expected 1"),
    (lambda e: e["trade"].update(isin="PTEDP0AM0009"), "field not in contract: isin"),
])
def test_contract_rejects_invalid_events(client, services, mutate, error):
    event = copy.deepcopy(_published_event(services, _trade(client)["trade_id"]))
    mutate(event)
    assert any(error in e for e in validate_trade_executed(event))


# ---------------------------------------------------------------------- consumer
def test_duplicate_event_does_not_create_second_instruction(client):
    trade = _trade(client)
    assert client.post(f"/api/integration/replay/{trade['trade_id']}").status_code == 200
    assert len(_instructions(client, trade_id=trade["trade_id"])) == 1


def test_invalid_message_goes_to_dead_letter_queue(client, services):
    r = client.post("/api/integration/publish-raw", json={"event_type": "TradeExecuted", "trade": {"qty": -1}})
    assert r.get_json()["contract_errors"]
    rejected = services[1].app.test_client().get("/api/rejected-events").get_json()
    assert len(rejected) == 1 and "event_id" in rejected[0]["reason"]
    assert _instructions(client) == []


def test_event_from_previous_generation_is_ignored(client, services):
    event = copy.deepcopy(_published_event(services, _trade(client)["trade_id"]))
    client.post("/api/reset")                               # new environment generation
    client.post("/api/business-date", json={"date": "2026-11-02"})
    client.post("/api/integration/publish-raw", json=event)  # old event still "in transit"
    assert _instructions(client) == []


def test_settlement_unavailable_trade_stays_in_outbox_and_is_delivered_later(client, services):
    server, settlement_client = services[0], services[1].app.test_client()
    settlement_client.post("/api/consumer/pause")
    trade = _trade(client)                                   # Trading keeps trading
    assert client.get("/health").get_json()["outbox_pending"] == 1
    assert client.get("/api/reconciliation").get_json()["missing_in_settlement"] == [trade["trade_id"]]
    settlement_client.post("/api/consumer/resume")
    server.publish_pending()                                 # the publisher retries
    assert client.get("/api/reconciliation").get_json()["ok"] is True
    assert client.get("/health").get_json()["outbox_pending"] == 0


# ---------------------------------------------------------------------- T2S
def _eod_until_due(client, n=3):
    return [client.post("/api/eod").get_json() for _ in range(n)]


def test_t2s_rejects_and_instruction_is_recycled(client):
    _trade(client)                                           # traded 2/11, settles 4/11
    client.post("/api/t2s/mode", json={"mode": "reject_symbol", "symbol": "EDP"})
    last = _eod_until_due(client)[-1]
    assert (last["settled"], last["failed"]) == (0, 1)
    [ins] = _instructions(client)
    assert ins["status"] == "FAILED" and "Insufficient securities" in ins["fail_reason"]
    client.post("/api/t2s/mode", json={"mode": "normal"})
    assert client.post("/api/eod").get_json()["settled"] == 1
    assert _instructions(client)[0]["attempts"] == 2


def test_t2s_unavailable_nothing_settles_and_recovers_next_day(client):
    _trade(client)
    client.post("/api/t2s/mode", json={"mode": "unavailable"})
    last = _eod_until_due(client)[-1]
    assert last["settled"] == 0 and last["t2s"].startswith("unavailable")
    client.post("/api/t2s/mode", json={"mode": "normal"})
    assert client.post("/api/eod").get_json()["settled"] == 1


def test_t2s_only_rejects_the_given_symbol(client):
    _trade(client, "EDP")
    _trade(client, "GALP", price=15.20)
    client.post("/api/t2s/mode", json={"mode": "reject_symbol", "symbol": "EDP"})
    _eod_until_due(client)
    states = {i["symbol"]: i["status"] for i in _instructions(client)}
    assert states == {"EDP": "FAILED", "GALP": "SETTLED"}


def test_invalid_simulator_mode(client):
    assert client.post("/api/t2s/mode", json={"mode": "explode"}).status_code == 400


def test_reconciliation_detects_amount_difference(client, services):
    trade = _trade(client)
    st = services[1]
    with st.lock:
        st.database.execute("UPDATE settlement_instructions SET amount = 999 WHERE trade_id = ?", (trade["trade_id"],))
        st.database.commit()
    r = client.get("/api/reconciliation").get_json()
    assert r["ok"] is False and r["mismatched"][0]["trade_id"] == trade["trade_id"]
