from __future__ import annotations

from typing import Any

from solana_crypto_detector.config import CONFIG
from solana_crypto_detector.models import Portfolio, Position, TradePolicy


def build_policy(strategy: str | None = None) -> TradePolicy:
    s = (strategy or CONFIG.user_buy_strategy or "balanced").lower()
    if s == "aggressive":
        return TradePolicy(max_buy_per_trade=60.0, max_position_count=5, risk_per_trade=0.25, stop_loss_percent=10.0, take_profit_percent=25.0, strategy="aggressive")
    if s == "conservative":
        return TradePolicy(max_buy_per_trade=10.0, max_position_count=2, risk_per_trade=0.10, stop_loss_percent=6.0, take_profit_percent=15.0, strategy="conservative")
    return TradePolicy(max_buy_per_trade=CONFIG.max_buy_per_trade, max_position_count=CONFIG.max_position_count, risk_per_trade=CONFIG.risk_per_trade, stop_loss_percent=CONFIG.stop_loss_percent, take_profit_percent=CONFIG.take_profit_percent, strategy="balanced")


def calculate_trade_amount(balance: float, policy: TradePolicy, risk_mode: str = "paper") -> float:
    size = balance * policy.risk_per_trade
    return min(size, policy.max_buy_per_trade)


def create_position(mint: str, symbol: str, entry_price: float, quantity: float, strategy: str) -> Position:
    stop = entry_price * (1 - (CONFIG.stop_loss_percent / 100))
    take = entry_price * (1 + (CONFIG.take_profit_percent / 100))
    return Position(mint=mint, symbol=symbol, entry_price=entry_price, quantity=quantity, stop_loss=stop, take_profit=take, strategy=strategy)


def simulate_trade(mint: str, symbol: str, amount_usd: float, strategy: str, current_price: float = 0.10) -> dict[str, Any]:
    policy = build_policy(strategy)
    actual_amount = min(amount_usd, policy.max_buy_per_trade)
    quantity = actual_amount / max(current_price, 0.000001)
    position = create_position(mint, symbol, current_price, quantity, policy.strategy)
    return {
        "mode": CONFIG.trade_mode,
        "amount_usd": actual_amount,
        "quantity": round(quantity, 6),
        "position": position,
        "policy": policy,
    }


def paper_portfolio() -> Portfolio:
    return Portfolio(cash_balance=1000.0, positions=[])
