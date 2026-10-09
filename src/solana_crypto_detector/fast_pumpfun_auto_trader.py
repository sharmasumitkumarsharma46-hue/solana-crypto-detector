from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Callable

from rich.console import Console

from .fast_quote_engine import FastQuoteEngine
from .jupiter_trader import JupiterTrader, SOL_MINT
from .pumpfun_listener import PumpFunMonitor, PumpFunToken
from .trade_engine import TradeEngine
from .wallet import SolanaWallet, load_wallet_config, require_live_wallet

console = Console()


@dataclass
class FastAutoTradeConfig:
    min_confidence: float = 72.0
    max_risk: float = 60.0
    auto_buy: bool = False
    auto_sell: bool = False
    dry_run: bool = True
    max_positions: int = 3
    target_latency_ms: int = 750  # Target execution in 750ms


class FastPumpFunAutoTrader:
    """Ultra-fast Pump.fun auto-trader with 500ms-1000ms execution target"""

    def __init__(self, wallet: SolanaWallet | None = None, config: FastAutoTradeConfig | None = None):
        self.wallet = wallet
        self.config = config or FastAutoTradeConfig()
        self.monitor = PumpFunMonitor(auto_risk_scoring=True)
        self.quote_engine = FastQuoteEngine()
        self.trader = JupiterTrader()
        self.trade_engine = None
        self.active_trades = {}
        self.stats = {
            "detected": 0,
            "approved": 0,
            "rejected": 0,
            "bought": 0,
            "execution_times_ms": [],
        }

        if wallet:
            self.trade_engine = TradeEngine(wallet, dry_run=self.config.dry_run)

    async def init(self):
        """Initialize fast engine"""
        await self.quote_engine.init_session()

    async def cleanup(self):
        """Cleanup resources"""
        await self.quote_engine.close_session()

    def _validate_token(self, token: PumpFunToken) -> tuple[bool, str]:
        """Fast validation (<10ms)"""
        if token.risk_score > self.config.max_risk:
            return False, f"Risk high"
        if token.confidence_score < self.config.min_confidence:
            return False, f"Conf low"
        if self.trade_engine and len(self.trade_engine.portfolio.get_open_positions()) >= self.config.max_positions:
            return False, f"Max pos"
        return True, "OK"

    async def _execute_buy_fast(self, token: PumpFunToken, quote: dict[str, Any] | None) -> bool:
        """Fast buy execution"""
        if not self.config.auto_buy or not self.trade_engine or not quote:
            return False

        try:
            # Skip confirmation for dry-run (saves network round trip)
            if self.config.dry_run:
                console.print(f"[yellow]🎯 DRY: {token.symbol}[/yellow]")
                self.stats["bought"] += 1
                return True
            else:
                # Live mode - execute with minimal delay
                swap_result = self.trade_engine.trader.execute_swap(
                    self.trade_engine.wallet,
                    quote,
                    dry_run=False,
                )
                console.print(f"[green]✅ BUY: {token.symbol}[/green]")
                self.stats["bought"] += 1
                return True
        except Exception as e:
            console.print(f"[red]✗ Buy error: {e}[/red]")

        return False

    async def on_new_token(self, token: PumpFunToken):
        """Process new token with ultra-fast latency"""
        import time

        start_time = time.time()
        self.stats["detected"] += 1

        # Step 1: Fast validation (< 10ms)
        valid, reason = self._validate_token(token)

        console.print(f"[cyan]#{self.stats['detected']}[/cyan] {token.symbol}", end="")

        if not valid:
            self.stats["rejected"] += 1
            console.print(f" [red]✗ {reason}[/red]")
            return

        self.stats["approved"] += 1
        console.print(f" [green]✓[/green]", end="")

        # Step 2: Fetch quote in parallel with decision (target: <400ms)
        quote_task = asyncio.create_task(
            self.quote_engine.get_quote_fast(
                SOL_MINT,
                token.mint,
                int(0.1 * 1_000_000_000),
            )
        )

        quote = await asyncio.wait_for(quote_task, timeout=0.5)

        if quote:
            console.print(f" [green]💰[/green]", end="")
            await self._execute_buy_fast(token, quote)
        else:
            console.print(f" [red]✗[/red]")

        # Step 3: Track execution time
        elapsed_ms = (time.time() - start_time) * 1000
        self.stats["execution_times_ms"].append(elapsed_ms)

        if elapsed_ms > self.config.target_latency_ms:
            console.print(f" [yellow]⚠️ {elapsed_ms:.0f}ms[/yellow]")
        else:
            console.print(f" [green]{elapsed_ms:.0f}ms[/green]")

    async def start_fast_trading(self):
        """Start ultra-fast auto-trader"""
        if not self.wallet:
            console.print("[yellow]Running in discovery mode[/yellow]")

        await self.init()

        console.print("\n[bold green]⚡ FAST PUMP.FUN AUTO TRADER[/bold green]")
        console.print(f"[cyan]Target Latency:[/cyan] {self.config.target_latency_ms}ms")
        console.print(f"[cyan]Mode:[/cyan] {'DRY-RUN' if self.config.dry_run else 'LIVE'}")
        console.print(f"[cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/cyan]\n")

        self.monitor.listener.on_token_detected(self.on_new_token)

        try:
            await self.monitor.start_monitoring()
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping...[/yellow]")
            self._print_fast_summary()
            await self.cleanup()

    def _print_fast_summary(self):
        """Print performance summary"""
        console.print("\n[cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/cyan]")
        console.print("[cyan]⚡ EXECUTION SUMMARY[/cyan]")
        console.print("[cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/cyan]")
        console.print(f"[cyan]🔍 Detected:[/cyan] {self.stats['detected']}")
        console.print(f"[green]✓ Approved:[/green] {self.stats['approved']}")
        console.print(f"[red]✗ Rejected:[/red] {self.stats['rejected']}")
        console.print(f"[yellow]💰 Bought:[/yellow] {self.stats['bought']}")

        if self.stats["execution_times_ms"]:
            avg_time = sum(self.stats["execution_times_ms"]) / len(self.stats["execution_times_ms"])
            min_time = min(self.stats["execution_times_ms"])
            max_time = max(self.stats["execution_times_ms"])
            console.print(f"[blue]⏱️  Avg Latency:[/blue] {avg_time:.0f}ms")
            console.print(f"[blue]   Min:[/blue] {min_time:.0f}ms | [blue]Max:[/blue] {max_time:.0f}ms")

        self.quote_engine.print_performance_stats()
        console.print("[cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/cyan]\n")


async def run_fast_pump_auto_trader(dry_run: bool = True, auto_buy: bool = False):
    """Run ultra-fast auto-trader"""
    cfg = load_wallet_config()
    if not cfg.enable_real_trading and not dry_run:
        console.print("[red]ERROR: ENABLE_REAL_TRADING not set[/red]")
        return

    try:
        wallet = require_live_wallet()
    except RuntimeError:
        wallet = None

    config = FastAutoTradeConfig(
        min_confidence=72.0,
        max_risk=60.0,
        auto_buy=auto_buy,
        auto_sell=False,
        dry_run=dry_run,
        max_positions=3,
        target_latency_ms=750,
    )

    trader = FastPumpFunAutoTrader(wallet=wallet, config=config)
    await trader.start_fast_trading()
