"""
Motor de negociação (matching engine) do QA Lab.

Simula, de forma simplificada, o que faz uma bolsa:
- recebe ordens de compra (BUY) e venda (SELL), limitadas ou de mercado
- valida as ordens (quantidade, tick size, bandas de preço)
- cruza compras com vendas por prioridade preço-tempo
- regista negócios (trades)
- escreve um log em logs/engine.log (ou na pasta definida em QA_LAB_LOG_DIR)

Modo desafio: com a variável de ambiente QA_LAB_CHALLENGE=1 o motor passa a ter
defeitos escondidos, para treinares a análise e o reporte de defeitos.
Sem essa variável, o motor funciona corretamente.
"""

import itertools
import logging
import os
from dataclasses import dataclass, field, asdict
from typing import Optional

MAX_QTY = 10_000      # quantidade máxima por ordem (10 000 é válido)
TICK_SIZE = 0.01      # o preço tem de ser múltiplo de 0.01
PRICE_BAND = 0.10     # o preço não pode afastar-se mais de 10% do preço de referência

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.environ.get("QA_LAB_LOG_DIR", os.path.join(BASE_DIR, "logs"))


def challenge_mode() -> bool:
    return os.environ.get("QA_LAB_CHALLENGE", "0") == "1"


def _build_logger():
    os.makedirs(LOG_DIR, exist_ok=True)
    log = logging.getLogger("engine")
    if not log.handlers:
        handler = logging.FileHandler(os.path.join(LOG_DIR, "engine.log"), encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
        log.addHandler(handler)
        log.setLevel(logging.INFO)
    return log


logger = _build_logger()


@dataclass
class Order:
    order_id: str
    symbol: str
    side: str                       # "BUY" ou "SELL"
    qty: int
    price: Optional[float] = None   # None = ordem de mercado
    seq: int = 0                    # ordem de chegada (prioridade tempo)
    remaining: int = field(init=False)
    status: str = field(init=False, default="NEW")
    reject_reason: Optional[str] = field(init=False, default=None)

    def __post_init__(self):
        self.remaining = self.qty

    def to_dict(self):
        return asdict(self)


@dataclass
class Trade:
    trade_id: str
    symbol: str
    buy_order_id: str
    sell_order_id: str
    qty: int
    price: float

    def to_dict(self):
        return asdict(self)


class MatchingEngine:
    def __init__(self, reference_prices=None):
        self.reference_prices = dict(reference_prices or {})
        self.bids = {}      # compras em espera, por símbolo
        self.asks = {}      # vendas em espera, por símbolo
        self.trades = []
        self.orders = {}
        self._seq = itertools.count(1)
        self._trade_seq = itertools.count(1)
        self._order_seq = itertools.count(1)

    def next_order_id(self):
        return f"O{next(self._order_seq):05d}"

    # ------------------------------------------------------------------ validação
    def validate(self, order: Order):
        if order.side not in ("BUY", "SELL"):
            return "Lado inválido"
        max_ok = order.qty < MAX_QTY if challenge_mode() else order.qty <= MAX_QTY
        if order.qty <= 0 or not max_ok:
            return "Quantidade inválida"
        if order.price is not None:
            if order.price <= 0:
                return "Preço inválido"
            ticks = order.price / TICK_SIZE
            if abs(round(ticks) - ticks) > 1e-6:
                return "Preço fora do tick size"
            ref = self.reference_prices.get(order.symbol)
            if ref and abs(order.price - ref) / ref > PRICE_BAND + 1e-9:
                return "Preço fora das bandas"
        return None

    # ------------------------------------------------------------------ livro de ordens
    def _book_side(self, symbol, side):
        book = self.bids if side == "BUY" else self.asks
        return book.setdefault(symbol, [])

    def _sort_book(self, symbol):
        # Compras: preço mais alto primeiro. Vendas: preço mais baixo primeiro.
        # Empate de preço: executa primeiro quem chegou antes (prioridade tempo).
        time_key = (lambda o: -o.seq) if challenge_mode() else (lambda o: o.seq)
        self._book_side(symbol, "BUY").sort(key=lambda o: (-o.price, time_key(o)))
        self._book_side(symbol, "SELL").sort(key=lambda o: (o.price, o.seq))

    def best_bid(self, symbol):
        side = self._book_side(symbol, "BUY")
        return side[0] if side else None

    def best_ask(self, symbol):
        side = self._book_side(symbol, "SELL")
        return side[0] if side else None

    def book(self, symbol):
        return {
            "symbol": symbol,
            "bids": [o.to_dict() for o in self._book_side(symbol, "BUY")],
            "asks": [o.to_dict() for o in self._book_side(symbol, "SELL")],
        }

    def symbols(self):
        return sorted(set(self.reference_prices) | set(self.bids) | set(self.asks))

    # ------------------------------------------------------------------ entrada de ordens
    def submit(self, order: Order) -> Order:
        order.seq = next(self._seq)
        self.orders[order.order_id] = order
        reason = self.validate(order)
        if reason:
            order.status = "REJECTED"
            order.reject_reason = reason
            logger.warning("Ordem %s REJEITADA: %s (%s %d %s @ %s)", order.order_id, reason,
                           order.side, order.qty, order.symbol, order.price)
            return order

        logger.info("Ordem %s recebida: %s %d %s @ %s", order.order_id, order.side, order.qty,
                    order.symbol, "MKT" if order.price is None else f"{order.price:.2f}")
        self._match(order)

        if order.remaining > 0:
            if order.price is None:
                # ordens de mercado não ficam no livro
                order.status = "CANCELLED" if order.remaining == order.qty else "PARTIALLY_FILLED"
                logger.info("Ordem de mercado %s sem contraparte suficiente (restam %d)",
                            order.order_id, order.remaining)
            else:
                self._book_side(order.symbol, order.side).append(order)
                self._sort_book(order.symbol)
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
            # Regra: o negócio é feito ao preço da ordem que JÁ ESTAVA no livro.
            if challenge_mode() and incoming.price is not None:
                price = incoming.price
            else:
                price = resting.price
            buy, sell = (incoming, resting) if incoming.side == "BUY" else (resting, incoming)
            trade = Trade(f"T{next(self._trade_seq):05d}", incoming.symbol,
                          buy.order_id, sell.order_id, qty, price)
            self.trades.append(trade)
            logger.info("Negócio %s: %d %s @ %.2f (compra %s / venda %s)", trade.trade_id, qty,
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
            logger.warning("Cancelamento recusado para %s", order_id)
            return False
        side = self._book_side(order.symbol, order.side)
        if order in side:
            side.remove(order)
        order.status = "CANCELLED"
        logger.info("Ordem %s cancelada (restavam %d)", order_id, order.remaining)
        return True
