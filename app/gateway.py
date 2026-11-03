"""
Order Entry Gateway (OEG).

Entry point for orders, inspired by the gateway of Euronext's Optiq platform:
validates each order (pre-trade controls) before sending it to the Matching Engine.
An order rejected here never reaches the order book.

Rules:
- side BUY or SELL; known symbol
- quantity between 1 and MAX_QTY (inclusive)
- price > 0, a multiple of the tick size (0.01) and within ±10% of the reference price
"""

from app.logs import get_logger
from app.model import Order, challenge_mode

MAX_QTY = 10_000
TICK_SIZE = 0.01
PRICE_BAND = 0.10

log = get_logger("OEG")


class OrderEntryGateway:
    def __init__(self, engine, reference_prices):
        self.engine = engine
        self.reference_prices = dict(reference_prices)

    def validate(self, order: Order):
        """Returns the rejection reason, or None if the order is valid."""
        if order.side not in ("BUY", "SELL"):
            return "Invalid side"
        if order.symbol not in self.reference_prices:
            return "Unknown symbol"
        max_ok = order.qty < MAX_QTY if challenge_mode() else order.qty <= MAX_QTY
        if order.qty <= 0 or not max_ok:
            return "Invalid quantity"
        if order.price is not None:
            if order.price <= 0:
                return "Invalid price"
            ticks = order.price / TICK_SIZE
            if abs(round(ticks) - ticks) > 1e-6:
                return "Price not on tick size"
            ref = self.reference_prices[order.symbol]
            if abs(order.price - ref) / ref > PRICE_BAND + 1e-9:
                return "Price outside price bands"
        return None

    def submit(self, symbol, side, qty, price=None) -> Order:
        order = Order(self.engine.next_order_id(), symbol, side, qty, price)
        reason = self.validate(order)
        if reason:
            order.status = "REJECTED"
            order.reject_reason = reason
            self.engine.register_rejected(order)
            log.warning("Order %s REJECTED: %s (%s %s %s @ %s)", order.order_id, reason,
                        side, qty, symbol, "MKT" if price is None else price)
            return order
        log.info("Order %s accepted: %s %d %s @ %s", order.order_id, side, qty, symbol,
                 "MKT" if price is None else f"{price:.2f}")
        return self.engine.submit(order)

    def cancel(self, order_id) -> bool:
        ok = self.engine.cancel(order_id)
        if ok:
            log.info("Cancel request accepted for %s", order_id)
        else:
            log.warning("Cancel request refused for %s", order_id)
        return ok
