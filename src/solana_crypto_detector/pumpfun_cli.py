from __future__ import annotations

import argparse
import asyncio

from rich.console import Console

from .pumpfun_auto_trader import AutoTradeConfig, run_pump_auto_trader

console = Console()


def cmd_pump_monitor(args):
    """Monitor Pump.fun tokens in real-time (discovery mode)"""
    console.print("[cyan]Starting Pump.fun token monitor (no trading)[/cyan]")
    asyncio.run(run_pump_auto_trader(dry_run=True, auto_buy=False))


def cmd_pump_dry_run(args):
    """Dry-run Pump.fun auto-trading (simulated)"""
    console.print("[yellow]Starting Pump.fun auto-trader in DRY-RUN mode[/yellow]")
    console.print("[yellow]No real funds will be used.\n[/yellow]")
    asyncio.run(run_pump_auto_trader(dry_run=True, auto_buy=True))


def cmd_pump_live(args):
    """Execute LIVE Pump.fun auto-trading (REAL FUNDS AT RISK)"""
    if not args.confirm:
        console.print("[red]ERROR: Live trading requires --confirm flag[/red]")
        return

    console.print("[red]╔════════════════════════════════════════╗[/red]")
    console.print("[red]║  WARNING: LIVE PUMP.FUN AUTO-TRADER    ║[/red]")
    console.print("[red]║  REAL FUNDS WILL BE USED AND MOVED!    ║[/red]")
    console.print("[red]╚════════════════════════════════════════╝[/red]")

    confirm = input("\nType 'YES I UNDERSTAND' to proceed: ").strip().upper()
    if confirm != "YES I UNDERSTAND":
        console.print("[yellow]Live trading cancelled.[/yellow]")
        return

    console.print("[red]Starting LIVE Pump.fun auto-trader...\n[/red]")
    asyncio.run(run_pump_auto_trader(dry_run=False, auto_buy=True))


def build_pumpfun_parser():
    parser = argparse.ArgumentParser(description="Pump.fun Auto-Trader for Solana")
    subparsers = parser.add_subparsers(dest="command", required=True)

    monitor = subparsers.add_parser("pump-monitor", help="Monitor Pump.fun tokens in real-time (discovery only)")
    monitor.set_defaults(func=cmd_pump_monitor)

    dry_run = subparsers.add_parser("pump-dry-run", help="Dry-run Pump.fun auto-trading (simulated)")
    dry_run.set_defaults(func=cmd_pump_dry_run)

    live = subparsers.add_parser("pump-live", help="Execute LIVE Pump.fun auto-trading (REAL FUNDS AT RISK)")
    live.add_argument("--confirm", action="store_true", help="Confirm live trading mode")
    live.set_defaults(func=cmd_pump_live)

    return parser


def main_pumpfun():
    parser = build_pumpfun_parser()
    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main_pumpfun()
