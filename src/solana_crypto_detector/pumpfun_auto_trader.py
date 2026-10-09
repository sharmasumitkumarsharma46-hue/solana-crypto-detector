from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Callable

from rich.console import Console

from .jupiter_trader import JupiterTrader, SOL_MINT
from .pumpfun_listener import PumpFunMonitor, PumpFunToken
from .trade_engine import TradeEngine
from .wallet import SolanaWallet, load_wallet_config, require_live_wallet

console = Console()


@dataclass
class AutoTradeConfig:
    min_confidence: float = 72.0
    max_risk: float = 60.0
    auto_buy: bool = False
    auto_sell: bool = False
    dry_run: bool = True
    max_positions: int = 3


class PumpFunAutoTrader:
    def __init__(self, wallet: SolanaWallet | None = None, config: AutoTradeConfig | None = None):
        self.wallet = wallet
        self.config = config or AutoTradeConfig()
        self.monitor = PumpFunMonitor(auto_risk_scoring=True)
        self.trader = JupiterTrader()
        self.trade_engine = None
        self.active_trades = {}
        self.detected_count = 0
        self.buy_count = 0
        self.skip_count = 0

        if wallet:
            self.trade_engine = TradeEngine(wallet, dry_run=self.config.dry_run)

    def _validate_token(self, token: PumpFunToken) -> tuple[bool, str]:
        if token.risk_score > self.config.max_risk:
            return False, f"Risk too high: {token.risk_score:.1f}"
        if token.confidence_score < self.config.min_confidence:
            return False, f"Confidence too low: {token.confidence_score:.1f}"
        if self.trade_engine and len(self.trade_engine.portfolio.get_open_positions()) >= self.config.max_positions:
            return False, f"Max positions ({self.config.max_positions}) reached"
        return True, "Approved"

    async def _fetch_quote(self, token: PumpFunToken) -> dict[str, Any] | None:
        try:
            quote = self.trader.get_quote(SOL_MINT, token.mint, int(0.1 * 1_000_000_000), slippage_bps=50)
            return quote
        except Exception as e:
            console.print(f"[red]Quote error for {token.symbol}: {e}[/red]")
            return None

    async def _execute_buy(self, token: PumpFunToken, quote: dict[str, Any] | None) -> bool:
        if not self.config.auto_buy or not self.trade_engine:
            return False

        try:
            if quote:
                swap_result = self.trade_engine.trader.execute_swap(
                    self.trade_engine.wallet,
                    quote,
                    dry_run=self.config.dry_run,
                )
                if self.config.dry_run:
                    console.print(f"[yellow]DRY RUN: Would buy {token.symbol} from {token.mint[:14]}...[/yellow]")
                else:
                    console.print(f"[green]BUY EXECUTED: {token.symbol} at {token.mint[:14]}...[/green]")
                    console.print(f"  Signature: {swap_result.get('signature', 'pending')}")
                self.buy_count += 1
                self.active_trades[token.mint] = token
                return True
        except Exception as e:
            console.print(f"[red]Buy execution error: {e}[/red]")
        return False

    async def on_new_token(self, token: PumpFunToken):
        self.detected_count += 1
        valid, reason = self._validate_token(token)

        console.print(f"\n[cyan]━━━ Token #{self.detected_count} ━━━[/cyan]")
        console.print(f"[green]✓ Mint:[/green] {token.mint[:20]}...")
        console.print(f"[green]✓ Symbol:[/green] {token.symbol}")
        console.print(f"[green]✓ Name:[/green] {token.name}")
        console.print(f"[yellow]Risk:[/yellow] {token.risk_score:.1f} | [blue]Confidence:[/blue] {token.confidence_score:.1f}")

        if not valid:
            console.print(f"[red]✗ Rejected:[/red] {reason}")
            self.skip_count += 1
            return

        console.print(f"[green]✓ Validation:[/green] {reason}")

        if self.config.auto_buy:
            console.print(f"[cyan]Fetching Jupiter quote...[/cyan]")
            quote = await self._fetch_quote(token)
            if quote:
                console.print(f"[green]✓ Quote received: {quote.get('outAmount', 'N/A')} output[/green]")
                await self._execute_buy(token, quote)
            else:
                console.print(f"[red]✗ Quote failed[/red]")
        else:
            console.print(f"[yellow]Auto-buy disabled. Manual intervention required.[/yellow]")

    async def start_auto_trading(self):
        if not self.wallet:
            console.print("[red]ERROR: Wallet not configured[/red]")
            return

        console.print("[cyan]═══════════════════════════════════════[/cyan]")
        console.print("[cyan]  PUMP.FUN AUTO TRADER STARTED[/cyan]")
        console.print("[cyan]═══════════════════════════════════════[/cyan]")
        console.print(f"Mode: {'DRY-RUN' if self.config.dry_run else 'LIVE'}")
        console.print(f"Auto-buy: {self.config.auto_buy}")
        console.print(f"Min confidence: {self.config.min_confidence}")
        console.print(f"Max risk: {self.config.max_risk}")
        console.print(f"Wallet: {self.wallet.wallet_address}")
        console.print("[cyan]═══════════════════════════════════════\n[/cyan]")

        self.monitor.listener.on_token_detected(self.on_new_token)

        try:
            await self.monitor.start_monitoring()
        except KeyboardInterrupt:
            console.print("\n[yellow]Auto trader stopped[/yellow]")
            self._print_summary()
            self.monitor.stop_monitoring()

    def _print_summary(self):
        console.print("\n[cyan]═══════════════════════════════════════[/cyan]")
        console.print("[cyan]  SESSION SUMMARY[/cyan]")
        console.print("[cyan]═══════════════════════════════════════[/cyan]")
        console.print(f"Total detected: {self.detected_count}")
        console.print(f"Approved: {self.detected_count - self.skip_count}")
        console.print(f"Rejected: {self.skip_count}")
        console.print(f"Trades executed: {self.buy_count}")
        if self.trade_engine:
            console.print(f"Open positions: {len(self.trade_engine.portfolio.get_open_positions())}")
        console.print("[cyan]═══════════════════════════════════════\n[/cyan]")

    def stop_auto_trading(self):
        self.monitor.stop_monitoring()


async def run_pump_auto_trader(dry_run: bool = True, auto_buy: bool = False):
    cfg = load_wallet_config()
    if not cfg.enable_real_trading and not dry_run:
        console.print("[red]ERROR: ENABLE_REAL_TRADING is false. Use dry_run=True or set env variable.[/red]")
        return

    try:
        wallet = require_live_wallet()
    except RuntimeError as e:
        console.print(f"[yellow]{e}[/yellow]")
        console.print("[yellow]Running in discovery mode (no trading)[/yellow]")
        wallet = None

    config = AutoTradeConfig(
        min_confidence=72.0,
        max_risk=60.0,
        auto_buy=auto_buy,
        auto_sell=False,
        dry_run=dry_run,
        max_positions=3,
    )

    trader = PumpFunAutoTrader(wallet=wallet, config=config)
    await trader.start_auto_trading()
