"""
Matching Engine (ME).

Matches buy and sell orders by price-time priority, like an exchange's matching engine:
- buys: highest price first; sells: lowest price first
- at the same price, the order that arrived first executes first
- the trade is done at the price of the order that was already resting in the book
- partial fill: the remainder stays in the book
- market orders without enough liquidity do not rest in the book

Only receives orders already validated by the Order Entry Gateway.
"""

import itertools

from app.logs import get_logger
from app.model import Order, Trade, challenge_mode

log = get_logger("ME")


class MatchingEngine:
    def __init__(self, trade_date_provider=None):
        self.bids = {}      # resting buy orders, by symbol
        self.asks = {}      # resting sell orders, by symbol
        self.trades = []
        self.orders = {}
        self._seq = itertools.count(1)
        self._trade_seq = itertools.count(1)
        self._order_seq = itertools.count(1)
        self._trade_date = trade_date_provider or (lambda: "")

    # ------------------------------------------------------------------ identifiers and state
    def next_order_id(self):
        return f"O{next(self._order_seq):05d}"

    def restore(self, orders, trades):
        """Rebuilds the state from the database (after a service restart)."""
        for o in sorted(orders, key=lambda x: x.order_id):
            o.seq = next(self._seq)
            self.orders[o.order_id] = o
            if o.status in ("NEW", "PARTIALLY_FILLED") and o.price is not None and o.remaining > 0:
                self._book_side(o.symbol, o.side).append(o)
        for symbol in {o.symbol for o in orders}:
            self._sort_book(symbol)
        self.trades = sorted(trades, key=lambda t: t.trade_id)
        self._order_seq = itertools.count(_next_number(self.orders))
        self._trade_seq = itertools.count(_next_number({t.trade_id: t for t in self.trades}))
        log.info("State restored: %d orders, %d trades", len(self.orders), len(self.trades))

    def register_rejected(self, order):
        order.seq = next(self._seq)
        self.orders[order.order_id] = order

    # ------------------------------------------------------------------ order book (market data)
    def _book_side(self, symbol, side):
        book = self.bids if side == "BUY" else self.asks
        return book.setdefault(symbol, [])

    def _sort_book(self, symbol):
        time_key = (lambda o: -o.seq) if challenge_mode() else (lambda o: o.seq)
        self._book_side(symbol, "BUY").sort(key=lambda o: (-o.price, time_key(o)))
        self._book_side(symbol, "SELL").sort(key=lambda o: (o.price, o.seq))

    def book(self, symbol):
        return {
            "symbol": symbol,
            "bids": [o.to_dict() for o in self._book_side(symbol, "BUY")],
            "asks": [o.to_dict() for o in self._book_side(symbol, "SELL")],
        }

    # ------------------------------------------------------------------ order entry
    def submit(self, order: Order) -> Order:
        order.seq = next(self._seq)
        self.orders[order.order_id] = order
        self._match(order)
        if order.remaining > 0:
            if order.price is None:
                order.status = "CANCELLED" if order.remaining == order.qty else "PARTIALLY_FILLED"
                log.info("Market order %s without enough liquidity (%d left, not added to the book)",
                         order.order_id, order.remaining)
            else:
                self._book_side(order.symbol, order.side).append(order)
                self._sort_book(order.symbol)
                log.info("Order %s added to the book: %s %d %s @ %.2f", order.order_id, order.side,
                         order.remaining, order.symbol, order.price)
        return order

    def _crosses(self, incoming, resting):
        if incoming.price is None:
            return True
        if incoming.side == "BUY":
            return incoming.price >= resting.price
        return incoming.price <= resting.price

    def _match(self, incoming):
        opposite = self._book_side(incoming.symbol, "SELL" if incoming.side == "BUY" else "BUY")
        while incoming.remaining > 0 and opposite:
            resting = opposite[0]
            if not self._crosses(incoming, resting):
                break
            qty = min(incoming.remaining, resting.remaining)
            if challenge_mode() and incoming.price is not None:
                price = incoming.price
            else:
                price = resting.price
            buy, sell = (incoming, resting) if incoming.side == "BUY" else (resting, incoming)
            trade = Trade(f"T{next(self._trade_seq):05d}", incoming.symbol, buy.order_id,
                          sell.order_id, qty, price, self._trade_date())
            self.trades.append(trade)
            log.info("Trade %s: %d %s @ %.2f (buy %s / sell %s)", trade.trade_id, qty,
                     trade.symbol, price, buy.order_id, sell.order_id)

            incoming.remaining -= qty
            if not (challenge_mode() and resting.side == "SELL" and qty < resting.remaining):
                resting.remaining -= qty
            for o in (incoming, resting):
                o.status = "FILLED" if o.remaining == 0 else "PARTIALLY_FILLED"
            if resting.remaining == 0:
                opposite.pop(0)

    def cancel(self, order_id) -> bool:
        order = self.orders.get(order_id)
        if order is None or order.status in ("FILLED", "REJECTED", "CANCELLED"):
            return False
        side = self._book_side(order.symbol, order.side)
        if order in side:
            side.remove(order)
        order.status = "CANCELLED"
        log.info("Order %s cancelled (%d remaining)", order_id, order.remaining)
        return True


def _next_number(items):
    numbers = [int(k[1:]) for k in items if k[1:].isdigit()]
    return (max(numbers) + 1) if numbers else 1
