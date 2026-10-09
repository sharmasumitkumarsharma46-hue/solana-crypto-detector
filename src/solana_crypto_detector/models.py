from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TokenCandidate:
    mint: str
    symbol: str
    name: str
    liquidity_score: float
    momentum_score: float
    volume_score: float
    age_hours: float
    risk_score: float
    final_score: float
    source: str = "rpc"
    discovered_at: str = ""
    price_usd: float | None = None
    market_cap_usd: float | None = None
    signal: str = "watch"


@dataclass
class TradePolicy:
    max_buy_per_trade: float = 25.0
    max_position_count: int = 3
    risk_per_trade: float = 0.15
    stop_loss_percent: float = 8.0
    take_profit_percent: float = 18.0
    strategy: str = "balanced"


@dataclass
class Position:
    mint: str
    symbol: str
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    strategy: str = "balanced"
    status: str = "open"
    pnl: float = 0.0


@dataclass
class Portfolio:
    positions: list[Position] = field(default_factory=list)
    cash_balance: float = 1000.0
