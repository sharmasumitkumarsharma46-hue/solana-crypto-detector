from __future__ import annotations

import argparse
import asyncio

from rich.console import Console

from .fast_pumpfun_auto_trader import run_fast_pump_auto_trader

console = Console()


def cmd_fast_monitor(args):
    """Monitor tokens at ultra-fast speed (discovery only)"""
    console.print("[cyan]⚡ Starting FAST monitor mode[/cyan]")
    asyncio.run(run_fast_pump_auto_trader(dry_run=True, auto_buy=False))


def cmd_fast_dry_run(args):
    """Dry-run with ultra-fast execution (500ms-1000ms target)"""
    console.print("[yellow]⚡ Starting FAST dry-run mode[/yellow]")
    asyncio.run(run_fast_pump_auto_trader(dry_run=True, auto_buy=True))


def cmd_fast_live(args):
    """LIVE ultra-fast execution (REAL FUNDS AT RISK)"""
    if not args.confirm:
        console.print("[red]ERROR: Requires --confirm flag[/red]")
        return

    console.print("[red]╔════════════════════════════════════════╗[/red]")
    console.print("[red]║  ⚡ ULTRA-FAST LIVE MODE ⚡            ║[/red]")
    console.print("[red]║  REAL FUNDS - HIGH SPEED EXECUTION     ║[/red]")
    console.print("[red]╚════════════════════════════════════════╝[/red]")

    confirm = input("\nType 'YES FAST' to proceed: ").strip().upper()
    if confirm != "YES FAST":
        console.print("[yellow]Cancelled[/yellow]")
        return

    console.print("[red]⚡ Starting FAST live trader...\n[/red]")
    asyncio.run(run_fast_pump_auto_trader(dry_run=False, auto_buy=True))


def build_fast_parser():
    parser = argparse.ArgumentParser(description="⚡ Ultra-Fast Pump.fun Auto-Trader (500ms-1000ms)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    monitor = subparsers.add_parser("fast-monitor", help="⚡ Monitor tokens at ultra-fast speed")
    monitor.set_defaults(func=cmd_fast_monitor)

    dry_run = subparsers.add_parser("fast-dry-run", help="⚡ Dry-run with 500ms-1000ms latency")
    dry_run.set_defaults(func=cmd_fast_dry_run)

    live = subparsers.add_parser("fast-live", help="⚡ LIVE ultra-fast trading (REAL FUNDS)")
    live.add_argument("--confirm", action="store_true", help="Confirm ultra-fast live mode")
    live.set_defaults(func=cmd_fast_live)

    return parser


def main_fast():
    parser = build_fast_parser()
    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main_fast()
