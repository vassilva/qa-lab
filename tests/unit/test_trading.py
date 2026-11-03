"""Order Entry Gateway and Matching Engine tested in isolation (standalone), with no database."""

import pytest

from app.gateway import OrderEntryGateway
from app.matching_engine import MatchingEngine

REFS = {"EDP": 4.50}


@pytest.fixture
def oeg():
    return OrderEntryGateway(MatchingEngine(lambda: "2026-11-02"), REFS)


@pytest.mark.parametrize("qty, status", [(0, "REJECTED"), (1, "NEW"), (10_000, "NEW"), (10_001, "REJECTED")])
def test_quantity_limits(oeg, qty, status):
    assert oeg.submit("EDP", "BUY", qty, 4.50).status == status


@pytest.mark.parametrize("price, reason", [
    (4.505, "Price not on tick size"),
    (4.96, "Price outside price bands"),
    (4.04, "Price outside price bands"),
    (0, "Invalid price"),
])
def test_price_rejections(oeg, price, reason):
    order = oeg.submit("EDP", "BUY", 100, price)
    assert (order.status, order.reject_reason) == ("REJECTED", reason)


@pytest.mark.parametrize("price", [4.05, 4.95])
def test_price_band_limits_are_accepted(oeg, price):
    assert oeg.submit("EDP", "BUY", 100, price).status == "NEW"


def test_unknown_symbol(oeg):
    assert oeg.submit("XPTO", "BUY", 100, 4.50).reject_reason == "Unknown symbol"


def test_trade_at_resting_order_price(oeg):
    oeg.submit("EDP", "SELL", 100, 4.50)
    buy = oeg.submit("EDP", "BUY", 100, 4.55)
    trade = oeg.engine.trades[-1]
    assert buy.status == "FILLED"
    assert (trade.qty, trade.price, trade.trade_date) == (100, 4.50, "2026-11-02")


def test_partial_fill(oeg):
    sell = oeg.submit("EDP", "SELL", 100, 4.50)
    oeg.submit("EDP", "BUY", 40, 4.50)
    assert (sell.status, sell.remaining) == ("PARTIALLY_FILLED", 60)
    assert oeg.engine.book("EDP")["asks"][0]["remaining"] == 60


def test_time_priority(oeg):
    first = oeg.submit("EDP", "BUY", 100, 4.48)
    second = oeg.submit("EDP", "BUY", 100, 4.48)
    oeg.submit("EDP", "SELL", 100, 4.48)
    assert (first.status, second.status) == ("FILLED", "NEW")


def test_price_priority(oeg):
    cheap = oeg.submit("EDP", "SELL", 100, 4.52)
    best = oeg.submit("EDP", "SELL", 100, 4.51)
    oeg.submit("EDP", "BUY", 100, 4.55)
    assert (best.status, cheap.status) == ("FILLED", "NEW")


def test_market_order_without_counterparty_is_cancelled(oeg):
    order = oeg.submit("EDP", "BUY", 100, None)
    assert order.status == "CANCELLED"
    assert oeg.engine.book("EDP")["bids"] == []


def test_filled_order_cannot_be_cancelled(oeg):
    sell = oeg.submit("EDP", "SELL", 100, 4.50)
    oeg.submit("EDP", "BUY", 100, 4.50)
    assert oeg.cancel(sell.order_id) is False


def test_state_restore(oeg):
    oeg.submit("EDP", "SELL", 100, 4.50)
    oeg.submit("EDP", "BUY", 40, 4.50)
    old = oeg.engine
    new = MatchingEngine(lambda: "2026-11-02")
    new.restore(list(old.orders.values()), list(old.trades))
    assert new.book("EDP")["asks"][0]["remaining"] == 60
    assert new.next_order_id() == "O00003"
