from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .config import CONFIG
from .jupiter_trader import JupiterTrader, SOL_MINT, USDC_MINT, build_buy_quote
from .token_detector import TokenMetadata
from .wallet import SolanaWallet

SYSTEM_BUY_FEE_PERCENT = 2.5
SYSTEM_SELL_FEE_PERCENT = 2.5
SYSTEM_FEE_WALLET = "AjKhH8NV4VgmnWYwCJKoDVkeKEevMkQXWj8T7HfSiFzK"


@dataclass
class TradeOrder:
    token_mint: str
    token_symbol: str
    action: str
    amount_usd: float
    entry_price: float
    stop_loss: float
    take_profit: float
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    executed_at: str | None = None
    signature: str | None = None
    pnl: float = 0.0
    fee_amount: float = 0.0
    fee_wallet: str = SYSTEM_FEE_WALLET

    def update_status(self, status: str, signature: str | None = None):
        self.status = status
        if signature:
            self.signature = signature
            self.executed_at = datetime.now(timezone.utc).isoformat()


@dataclass
class Portfolio:
    wallet_address: str
    positions: dict[str, TradeOrder] = field(default_factory=dict)
    cash_balance: float = 1000.0
    total_value: float = 1000.0
    active_orders: list[TradeOrder] = field(default_factory=list)

    def add_order(self, order: TradeOrder):
        self.active_orders.append(order)
        self.positions[order.token_mint] = order

    def get_open_positions(self) -> list[TradeOrder]:
        return [o for o in self.active_orders if o.status in ("pending", "executed")]

    def calculate_pnl(self, current_prices: dict[str, float]) -> float:
        total_pnl = 0.0
        for order in self.get_open_positions():
            if order.token_mint in current_prices:
                current = current_prices[order.token_mint]
                pnl = (current - order.entry_price) * (order.amount_usd / order.entry_price)
                order.pnl = pnl
                total_pnl += pnl
        return total_pnl


class TradeEngine:
    def __init__(self, wallet: SolanaWallet, dry_run: bool = True):
        self.wallet = wallet
        self.dry_run = dry_run
        self.trader = JupiterTrader(CONFIG.jupiter_api_url)
        self.portfolio = Portfolio(wallet_address=wallet.wallet_address)
        self.max_loss_per_trade = CONFIG.max_buy_per_trade * (CONFIG.risk_per_trade / 100)
        self.max_positions = CONFIG.max_position_count

    @staticmethod
    def _system_buy_fee(amount_usd: float) -> float:
        return round(amount_usd * (SYSTEM_BUY_FEE_PERCENT / 100), 6)

    @staticmethod
    def _system_sell_fee(amount_usd: float) -> float:
        return round(amount_usd * (SYSTEM_SELL_FEE_PERCENT / 100), 6)

    def validate_candidate(self, candidate: TokenMetadata) -> tuple[bool, str]:
        if candidate.risk_score > 60:
            return False, f"Risk score too high: {candidate.risk_score}"
        if candidate.confidence_score < 65:
            return False, f"Confidence score too low: {candidate.confidence_score}"
        if len(self.portfolio.get_open_positions()) >= self.max_positions:
            return False, f"Max positions ({self.max_positions}) reached"
        return True, "Candidate approved"

    def should_buy(self, candidate: TokenMetadata) -> bool:
        valid, _ = self.validate_candidate(candidate)
        if not valid:
            return False
        return candidate.confidence_score >= CONFIG.detection_threshold

    def should_sell(self, order: TradeOrder, current_price: float) -> bool:
        if current_price <= 0:
            return False
        pnl_percent = ((current_price - order.entry_price) / order.entry_price) * 100
        if pnl_percent <= -CONFIG.stop_loss_percent:
            return True
        if pnl_percent >= CONFIG.take_profit_percent:
            return True
        return False

    def calculate_buy_amount(self) -> float:
        available = self.portfolio.cash_balance
        max_risk = available * CONFIG.risk_per_trade
        return min(max_risk, CONFIG.max_buy_per_trade)

    def place_buy_order(self, candidate: TokenMetadata) -> TradeOrder | None:
        valid, _ = self.validate_candidate(candidate)
        if not valid:
            return None

        amount = self.calculate_buy_amount()
        if amount <= 0:
            return None

        fee_amount = self._system_buy_fee(amount)
        net_amount = amount - fee_amount

        order = TradeOrder(
            token_mint=candidate.mint,
            token_symbol=candidate.symbol,
            action="buy",
            amount_usd=amount,
            entry_price=0.1,
            stop_loss=0.1 * (1 - CONFIG.stop_loss_percent / 100),
            take_profit=0.1 * (1 + CONFIG.take_profit_percent / 100),
            fee_amount=fee_amount,
            fee_wallet=SYSTEM_FEE_WALLET,
        )

        if self.dry_run:
            order.update_status("dry_run")
        else:
            try:
                quote = build_buy_quote(self.trader, net_amount / 1e9, output_mint=candidate.mint)
                swap_result = self.trader.execute_swap(self.wallet, quote, dry_run=False)
                order.update_status("executed", swap_result.get("signature"))
                self.portfolio.cash_balance -= amount
            except Exception as e:
                order.update_status(f"failed: {str(e)}")
                return None

        self.portfolio.add_order(order)
        return order

    def place_sell_order(self, order: TradeOrder) -> TradeOrder | None:
        if order.status not in ("executed", "pending"):
            return None

        fee_amount = self._system_sell_fee(order.amount_usd)
        net_amount = order.amount_usd - fee_amount

        sell_order = TradeOrder(
            token_mint=order.token_mint,
            token_symbol=order.token_symbol,
            action="sell",
            amount_usd=order.amount_usd,
            entry_price=order.entry_price,
            stop_loss=0,
            take_profit=0,
            fee_amount=fee_amount,
            fee_wallet=SYSTEM_FEE_WALLET,
        )

        if self.dry_run:
            sell_order.update_status("dry_run")
            self.portfolio.cash_balance += net_amount
        else:
            try:
                quote = build_buy_quote(self.trader, net_amount / 1e9, output_mint=SOL_MINT)
                swap_result = self.trader.execute_swap(self.wallet, quote, dry_run=False)
                sell_order.update_status("executed", swap_result.get("signature"))
                self.portfolio.cash_balance += net_amount
            except Exception as e:
                sell_order.update_status(f"failed: {str(e)}")
                return None

        order.update_status("closed")
        return sell_order

    def scan_and_trade(self, candidates: list[TokenMetadata], auto_sell: bool = False) -> dict[str, Any]:
        results = {
            "scanned": len(candidates),
            "buy_orders": [],
            "sell_orders": [],
            "rejected": [],
        }

        for candidate in candidates:
            if self.should_buy(candidate):
                order = self.place_buy_order(candidate)
                if order:
                    results["buy_orders"].append({
                        "mint": order.token_mint,
                        "status": order.status,
                        "fee_amount": order.fee_amount,
                        "fee_wallet": order.fee_wallet,
                    })
                else:
                    results["rejected"].append({"mint": candidate.mint, "reason": "buy placement failed"})
            else:
                results["rejected"].append({"mint": candidate.mint, "reason": "did not meet buy criteria"})

        if auto_sell:
            for order in self.portfolio.get_open_positions():
                current_price = 0.1
                if self.should_sell(order, current_price):
                    sell = self.place_sell_order(order)
                    if sell:
                        results["sell_orders"].append({
                            "mint": sell.token_mint,
                            "status": sell.status,
                            "fee_amount": sell.fee_amount,
                            "fee_wallet": sell.fee_wallet,
                        })

        return results
