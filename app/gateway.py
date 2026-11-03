"""
Order Entry Gateway (OEG).

Porta de entrada das ordens, inspirada no gateway da plataforma Optiq da Euronext:
valida cada ordem (controlos pré-negociação) antes de a enviar ao Matching Engine.
Uma ordem rejeitada aqui nunca chega ao livro de ordens.

Regras:
- lado BUY ou SELL; símbolo conhecido
- quantidade entre 1 e MAX_QTY (inclusive)
- preço > 0, múltiplo do tick size (0.01) e dentro de ±10% do preço de referência
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
        """Devolve o motivo de rejeição, ou None se a ordem for válida."""
        if order.side not in ("BUY", "SELL"):
            return "Lado inválido"
        if order.symbol not in self.reference_prices:
            return "Símbolo desconhecido"
        max_ok = order.qty < MAX_QTY if challenge_mode() else order.qty <= MAX_QTY
        if order.qty <= 0 or not max_ok:
            return "Quantidade inválida"
        if order.price is not None:
            if order.price <= 0:
                return "Preço inválido"
            ticks = order.price / TICK_SIZE
            if abs(round(ticks) - ticks) > 1e-6:
                return "Preço fora do tick size"
            ref = self.reference_prices[order.symbol]
            if abs(order.price - ref) / ref > PRICE_BAND + 1e-9:
                return "Preço fora das bandas"
        return None

    def submit(self, symbol, side, qty, price=None) -> Order:
        order = Order(self.engine.next_order_id(), symbol, side, qty, price)
        reason = self.validate(order)
        if reason:
            order.status = "REJECTED"
            order.reject_reason = reason
            self.engine.register_rejected(order)
            log.warning("Ordem %s REJEITADA: %s (%s %s %s @ %s)", order.order_id, reason,
                        side, qty, symbol, "MKT" if price is None else price)
            return order
        log.info("Ordem %s aceite: %s %d %s @ %s", order.order_id, side, qty, symbol,
                 "MKT" if price is None else f"{price:.2f}")
        return self.engine.submit(order)

    def cancel(self, order_id) -> bool:
        ok = self.engine.cancel(order_id)
        if ok:
            log.info("Pedido de cancelamento aceite para %s", order_id)
        else:
            log.warning("Pedido de cancelamento recusado para %s", order_id)
        return ok
