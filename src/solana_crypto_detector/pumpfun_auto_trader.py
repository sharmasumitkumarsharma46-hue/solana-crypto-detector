from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Callable

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

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


class AnimatedStats:
    def __init__(self):
        self.detected_count = 0
        self.approved_count = 0
        self.rejected_count = 0
        self.buy_count = 0
        self.last_token: PumpFunToken | None = None

    def render(self) -> Table:
        table = Table(title="[cyan]LIVE STATS[/cyan]", show_header=False, box=None)
        
        table.add_row("[green]📊 Total Detected[/green]", f"[cyan]{self.detected_count}[/cyan]")
        table.add_row("[green]✓ Approved[/green]", f"[green]{self.approved_count}[/green]")
        table.add_row("[red]✗ Rejected[/red]", f"[red]{self.rejected_count}[/red]")
        table.add_row("[yellow]💰 Bought[/yellow]", f"[yellow]{self.buy_count}[/yellow]")
        
        if self.last_token:
            table.add_row("[cyan]Last Token[/cyan]", f"[blue]{self.last_token.symbol}[/blue]")
        
        return table


class PumpFunAutoTrader:
    def __init__(self, wallet: SolanaWallet | None = None, config: AutoTradeConfig | None = None):
        self.wallet = wallet
        self.config = config or AutoTradeConfig()
        self.monitor = PumpFunMonitor(auto_risk_scoring=True)
        self.trader = JupiterTrader()
        self.trade_engine = None
        self.active_trades = {}
        self.stats = AnimatedStats()

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
            with console.status("[bold cyan]⏳ Fetching Jupiter quote...[/bold cyan]", spinner="dots"):
                await asyncio.sleep(0.5)
                quote = self.trader.get_quote(SOL_MINT, token.mint, int(0.1 * 1_000_000_000), slippage_bps=50)
            return quote
        except Exception as e:
            console.print(f"[red]✗ Quote error: {e}[/red]")
            return None

    async def _execute_buy(self, token: PumpFunToken, quote: dict[str, Any] | None) -> bool:
        if not self.config.auto_buy or not self.trade_engine:
            return False

        try:
            if quote:
                with console.status("[bold yellow]🔄 Executing trade...[/bold yellow]", spinner="dots"):
                    await asyncio.sleep(0.3)
                    swap_result = self.trade_engine.trader.execute_swap(
                        self.trade_engine.wallet,
                        quote,
                        dry_run=self.config.dry_run,
                    )
                
                if self.config.dry_run:
                    console.print(f"[yellow]🎯 DRY RUN: {token.symbol} would be bought[/yellow]")
                else:
                    console.print(f"[green]✅ BUY EXECUTED: {token.symbol}[/green]")
                
                self.stats.buy_count += 1
                self.active_trades[token.mint] = token
                return True
        except Exception as e:
            console.print(f"[red]✗ Buy error: {e}[/red]")
        return False

    async def on_new_token(self, token: PumpFunToken):
        self.stats.detected_count += 1
        self.stats.last_token = token
        valid, reason = self._validate_token(token)

        # Animated token detection
        console.print(f"\n[bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold cyan]")
        console.print(f"[green]🎉 NEW TOKEN #{self.stats.detected_count}[/green]")
        console.print(f"[bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold cyan]")
        
        # Token info animation
        console.print(f"  [cyan]📍 Mint:[/cyan]   {token.mint[:16]}...")
        console.print(f"  [green]💎 Symbol:[/green] {token.symbol}")
        console.print(f"  [blue]📝 Name:[/blue]   {token.name}")
        
        # Score bars
        risk_bar = "█" * int(token.risk_score / 5) + "░" * (20 - int(token.risk_score / 5))
        conf_bar = "█" * int(token.confidence_score / 5) + "░" * (20 - int(token.confidence_score / 5))
        
        console.print(f"  [red]⚠️  Risk:[/red]        [{risk_bar}] {token.risk_score:.1f}")
        console.print(f"  [green]💪 Confidence:[/green] [{conf_bar}] {token.confidence_score:.1f}")

        if not valid:
            self.stats.rejected_count += 1
            console.print(f"  [red]✗ REJECTED:[/red] {reason}\n")
            return

        self.stats.approved_count += 1
        console.print(f"  [green]✓ APPROVED[/green]\n")

        if self.config.auto_buy:
            quote = await self._fetch_quote(token)
            if quote:
                console.print(f"  [green]✓ Quote:[/green] {quote.get('outAmount', 'N/A')} output")
                await self._execute_buy(token, quote)
            else:
                console.print(f"  [red]✗ Quote failed[/red]")
        else:
            console.print(f"  [yellow]⏸️  Auto-buy disabled[/yellow]")

    async def start_auto_trading(self):
        if not self.wallet:
            console.print("[red]ERROR: Wallet not configured[/red]")
            return

        # Header animation
        console.print("\n")
        console.print(Panel(
            Text("🚀 PUMP.FUN AUTO TRADER 🚀", style="bold cyan", justify="center"),
            border_style="cyan",
            padding=(1, 2)
        ))
        
        info_table = Table(show_header=False, box=None)
        info_table.add_row("[cyan]Mode:[/cyan]", f"[bold]{'🎮 DRY-RUN' if self.config.dry_run else '💰 LIVE TRADING'}[/bold]")
        info_table.add_row("[cyan]Auto-Buy:[/cyan]", f"[bold]{'✓ ENABLED' if self.config.auto_buy else '✗ DISABLED'}[/bold]")
        info_table.add_row("[cyan]Min Confidence:[/cyan]", f"[yellow]{self.config.min_confidence}[/yellow]")
        info_table.add_row("[cyan]Max Risk:[/cyan]", f"[yellow]{self.config.max_risk}[/yellow]")
        info_table.add_row("[cyan]Wallet:[/cyan]", f"[blue]{self.wallet.wallet_address[:16]}...[/blue]")
        
        console.print(info_table)
        console.print("[cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/cyan]\n")

        # Spinner for connection
        with console.status("[bold green]🔗 Connecting to Pump.fun...[/bold green]", spinner="dots"):
            await asyncio.sleep(1)
            self.monitor.listener.on_token_detected(self.on_new_token)

        console.print("[bold green]✓ Connected! Listening for tokens...[/bold green]\n")

        try:
            await self.monitor.start_monitoring()
        except KeyboardInterrupt:
            console.print("\n[yellow]⏹️  Stopping auto trader...[/yellow]")
            self._print_summary()
            self.monitor.stop_monitoring()

    def _print_summary(self):
        console.print("\n")
        console.print(Panel(
            Text("📊 SESSION SUMMARY 📊", style="bold cyan", justify="center"),
            border_style="cyan",
            padding=(1, 2)
        ))
        
        summary_table = Table(show_header=False, box=None)
        summary_table.add_row("[cyan]🔍 Total Detected:[/cyan]", f"[bold green]{self.stats.detected_count}[/bold green]")
        summary_table.add_row("[cyan]✓ Approved:[/cyan]", f"[bold green]{self.stats.approved_count}[/bold green]")
        summary_table.add_row("[cyan]✗ Rejected:[/cyan]", f"[bold red]{self.stats.rejected_count}[/bold red]")
        summary_table.add_row("[cyan]💰 Bought:[/cyan]", f"[bold yellow]{self.stats.buy_count}[/bold yellow]")
        
        if self.trade_engine:
            open_pos = len(self.trade_engine.portfolio.get_open_positions())
            summary_table.add_row("[cyan]📈 Open Positions:[/cyan]", f"[bold blue]{open_pos}[/bold blue]")
        
        console.print(summary_table)
        console.print("[cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/cyan]\n")

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
