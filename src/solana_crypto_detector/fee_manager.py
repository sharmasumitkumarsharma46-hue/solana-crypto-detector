from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from rich.console import Console

console = Console()

SYSTEM_BUY_FEE_PERCENT = 2.5
SYSTEM_SELL_FEE_PERCENT = 2.5
SYSTEM_FEE_WALLET = "AjKhH8NV4VgmnWYwCJKoDVkeKEevMkQXWj8T7HfSiFzK"


@dataclass
class FeeRecord:
    """Records a fee transaction"""
    trade_type: str  # "buy" or "sell"
    token_mint: str
    token_symbol: str
    gross_amount: float  # amount before fee
    fee_amount: float  # actual fee charged
    net_amount: float  # amount after fee
    fee_wallet: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    transaction_signature: str | None = None
    status: str = "pending"  # pending, sent, confirmed, failed

    def mark_sent(self, signature: str):
        self.status = "sent"
        self.transaction_signature = signature

    def mark_confirmed(self):
        self.status = "confirmed"

    def mark_failed(self, reason: str = ""):
        self.status = f"failed: {reason}"


class FeeManager:
    """Manages fee collection and ledger for all trades"""

    def __init__(self):
        self.fee_ledger: list[FeeRecord] = []
        self.total_fees_collected: float = 0.0

    def calculate_buy_fee(self, amount: float) -> tuple[float, float]:
        """Calculate buy fee. Returns (fee_amount, net_amount)"""
        fee = round(amount * (SYSTEM_BUY_FEE_PERCENT / 100), 8)
        net = amount - fee
        return fee, net

    def calculate_sell_fee(self, amount: float) -> tuple[float, float]:
        """Calculate sell fee. Returns (fee_amount, net_amount)"""
        fee = round(amount * (SYSTEM_SELL_FEE_PERCENT / 100), 8)
        net = amount - fee
        return fee, net

    def record_buy_fee(
        self,
        token_mint: str,
        token_symbol: str,
        gross_amount: float,
        fee_amount: float,
    ) -> FeeRecord:
        """Record a buy fee"""
        net_amount = gross_amount - fee_amount
        record = FeeRecord(
            trade_type="buy",
            token_mint=token_mint,
            token_symbol=token_symbol,
            gross_amount=gross_amount,
            fee_amount=fee_amount,
            net_amount=net_amount,
            fee_wallet=SYSTEM_FEE_WALLET,
        )
        self.fee_ledger.append(record)
        self.total_fees_collected += fee_amount
        console.print(f"[yellow]📊 Fee recorded:[/yellow] {token_symbol} | Fee: {fee_amount} SOL")
        return record

    def record_sell_fee(
        self,
        token_mint: str,
        token_symbol: str,
        gross_amount: float,
        fee_amount: float,
    ) -> FeeRecord:
        """Record a sell fee"""
        net_amount = gross_amount - fee_amount
        record = FeeRecord(
            trade_type="sell",
            token_mint=token_mint,
            token_symbol=token_symbol,
            gross_amount=gross_amount,
            fee_amount=fee_amount,
            net_amount=net_amount,
            fee_wallet=SYSTEM_FEE_WALLET,
        )
        self.fee_ledger.append(record)
        self.total_fees_collected += fee_amount
        console.print(f"[yellow]📊 Fee recorded:[/yellow] {token_symbol} | Fee: {fee_amount} SOL")
        return record

    def mark_fee_sent(self, record: FeeRecord, signature: str):
        """Mark fee as sent to wallet"""
        record.mark_sent(signature)
        console.print(f"[green]✓ Fee sent:[/green] {record.token_symbol} | Sig: {signature[:8]}...")

    def mark_fee_confirmed(self, record: FeeRecord):
        """Mark fee as confirmed on-chain"""
        record.mark_confirmed()
        console.print(f"[green]✓ Fee confirmed:[/green] {record.token_symbol}")

    def get_ledger_summary(self) -> dict[str, Any]:
        """Get fee ledger summary"""
        buy_fees = sum(r.fee_amount for r in self.fee_ledger if r.trade_type == "buy")
        sell_fees = sum(r.fee_amount for r in self.fee_ledger if r.trade_type == "sell")
        pending = len([r for r in self.fee_ledger if r.status == "pending"])
        sent = len([r for r in self.fee_ledger if r.status == "sent"])
        confirmed = len([r for r in self.fee_ledger if r.status == "confirmed"])

        return {
            "total_fees": self.total_fees_collected,
            "buy_fees": buy_fees,
            "sell_fees": sell_fees,
            "pending_count": pending,
            "sent_count": sent,
            "confirmed_count": confirmed,
            "fee_wallet": SYSTEM_FEE_WALLET,
        }

    def print_fee_report(self):
        """Print fee collection report"""
        summary = self.get_ledger_summary()
        console.print("\n[cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/cyan]")
        console.print("[cyan]💰 FEE COLLECTION REPORT[/cyan]")
        console.print("[cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/cyan]")
        console.print(f"[green]✓ Total Fees:[/green] {summary['total_fees']:.8f} SOL")
        console.print(f"[blue]  Buy Fees:[/blue] {summary['buy_fees']:.8f} SOL")
        console.print(f"[blue]  Sell Fees:[/blue] {summary['sell_fees']:.8f} SOL")
        console.print(f"[yellow]⏳ Pending:[/yellow] {summary['pending_count']}")
        console.print(f"[yellow]📤 Sent:[/yellow] {summary['sent_count']}")
        console.print(f"[green]✓ Confirmed:[/green] {summary['confirmed_count']}")
        console.print(f"[magenta]💼 Fee Wallet:[/magenta] {summary['fee_wallet']}")
        console.print("[cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/cyan]\n")

    def export_fee_ledger(self) -> list[dict[str, Any]]:
        """Export complete fee ledger as dicts"""
        return [
            {
                "trade_type": r.trade_type,
                "token": r.token_symbol,
                "mint": r.token_mint,
                "gross": r.gross_amount,
                "fee": r.fee_amount,
                "net": r.net_amount,
                "timestamp": r.timestamp,
                "signature": r.transaction_signature,
                "status": r.status,
            }
            for r in self.fee_ledger
        ]
