"""Objetos de negócio partilhados pelos componentes."""

import os
from dataclasses import dataclass, field, asdict
from typing import Optional


def challenge_mode() -> bool:
    """Modo desafio: QA_LAB_CHALLENGE=1 ativa defeitos escondidos para treinar análise de defeitos."""
    return os.environ.get("QA_LAB_CHALLENGE", "0") == "1"


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
    trade_date: str = ""            # data de negociação (AAAA-MM-DD)

    def to_dict(self):
        return asdict(self)
