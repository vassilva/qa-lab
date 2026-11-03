"""Business objects shared by the components."""

import os
from dataclasses import dataclass, field, asdict
from typing import Optional


def challenge_mode() -> bool:
    """Challenge mode: QA_LAB_CHALLENGE=1 enables hidden defects to practise defect analysis."""
    return os.environ.get("QA_LAB_CHALLENGE", "0") == "1"


@dataclass
class Order:
    order_id: str
    symbol: str
    side: str                       # "BUY" or "SELL"
    qty: int
    price: Optional[float] = None   # None = market order
    seq: int = 0                    # arrival sequence (time priority)
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
    trade_date: str = ""            # trade date (YYYY-MM-DD)

    def to_dict(self):
        return asdict(self)
