from __future__ import annotations

import argparse
import json
import time

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import CONFIG
from .token_detector import detect_live_candidates
from .trade_engine import TradeEngine
from .wallet import load_wallet_config, require_live_wallet

console = Console()


def _print_candidates(items):
    if not items:
        console.print("[yellow]No live candidates found.[/yellow]")
        return

    table = Table(title="Live Solana token candidates")
    table.add_column("Mint", style="cyan")
    table.add_column("Symbol", style="green")
    table.add_column("Name")
    table.add_column("Risk", style="red")
    table.add_column("Confidence", style="blue")
    table.add_column("Sentiment", style="yellow")

    for item in items:
        table.add_row(
            item.mint[:14] + "...",
            item.symbol,
            item.name[:20],
            f"{item.risk_score:.1f}",
            f"{item.confidence_score:.1f}",
            item.sentiment.upper(),
        )
    console.print(table)


def cmd_scan(args):
    """Scan for new token candidates"""
    console.print(f"[cyan]Scanning for new tokens (limit: {args.limit})...[/cyan]")
    items = detect_live_candidates(limit=args.limit)
    _print_candidates(items)
    console.print(f"\n[green]Total: {len(items)} candidates found[/green]")


def cmd_watch(args):
    """Watch for tokens in real-time"""
    console.print(f"[green]Watching Solana for new tokens every {args.interval}s[/green]")
    try:
        while True:
            items = detect_live_candidates(limit=args.limit)
            console.clear()
            console.print(f"[cyan]Watch mode (refresh every {args.interval}s)[/cyan]")
            _print_candidates(items)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        console.print("\n[yellow]Watch mode stopped.[/yellow]")


def cmd_wallet_status(args):
    """Check wallet configuration"""
    cfg = load_wallet_config()
    console.print("[cyan]=== Wallet Configuration ===[/cyan]")
    console.print(f"Wallet address set: {'✓' if cfg.wallet_address else '✗'}")
    console.print(f"Private key set: {'✓' if cfg.private_key else '✗'}")
    console.print(f"Live trading enabled: {'✓' if cfg.enable_real_trading else '✗'}")
    if cfg.wallet_address:
        console.print(f"Address: {cfg.wallet_address}")


def cmd_dry_run_trade(args):
    """Run a dry-run trade simulation"""
    console.print("[cyan]=== DRY RUN MODE ===[/cyan]")
    console.print("[yellow]No real funds will be used or moved.\n[/yellow]")

    try:
        wallet = require_live_wallet()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        return

    engine = TradeEngine(wallet, dry_run=True)
    console.print(f"[green]Engine initialized in dry-run mode[/green]")
    console.print(f"Wallet: {wallet.wallet_address}")
    console.print(f"Max positions: {engine.max_positions}")
    console.print(f"Max loss per trade: ${engine.max_loss_per_trade:.2f}\n")

    items = detect_live_candidates(limit=args.limit)
    if not items:
        console.print("[yellow]No candidates found.[/yellow]")
        return

    console.print(f"[cyan]Scanning {len(items)} candidates...\n[/cyan]")

    results = engine.scan_and_trade(items, auto_sell=args.auto_sell)
    console.print("[cyan]=== DRY RUN RESULTS ===[/cyan]")
    console.print(f"Scanned: {results['scanned']}")
    console.print(f"Buy orders (dry): {len(results['buy_orders'])}")
    console.print(f"Sell orders (dry): {len(results['sell_orders'])}")
    console.print(f"Rejected: {len(results['rejected'])}")

    if results["buy_orders"]:
        console.print("\n[green]Buy orders (simulated):[/green]")
        for order in results["buy_orders"]:
            console.print(f"  - {order['mint'][:14]}... : {order['status']}")

    if results["rejected"]:
        console.print("\n[yellow]Rejected candidates:[/yellow]")
        for item in results["rejected"][:5]:
            console.print(f"  - {item['mint'][:14]}... : {item['reason']}")

    console.print("\n[green]Dry run complete. No actual transactions.\n[/green]")


def cmd_live_trade(args):
    """Execute LIVE trading (real funds at risk)"""
    if not args.confirm:
        console.print("[red]ERROR: Live trading requires --confirm flag[/red]")
        console.print("[yellow]Usage: solana-crypto-detector live-trade --confirm --limit 10[/yellow]")
        return

    cfg = load_wallet_config()
    if not cfg.enable_real_trading:
        console.print("[red]ERROR: ENABLE_REAL_TRADING is not set to true in .env[/red]")
        return

    console.print("[red]╔════════════════════════════════════════╗[/red]")
    console.print("[red]║  WARNING: LIVE TRADING MODE ACTIVATED  ║[/red]")
    console.print("[red]║  REAL FUNDS WILL BE USED AND MOVED!    ║[/red]")
    console.print("[red]╚════════════════════════════════════════╝[/red]")

    confirm = input("\nType 'YES' to proceed with live trading: ").strip().upper()
    if confirm != "YES":
        console.print("[yellow]Live trading cancelled.[/yellow]")
        return

    try:
        wallet = require_live_wallet()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        return

    engine = TradeEngine(wallet, dry_run=False)
    console.print(f"\n[green]Engine initialized in LIVE mode[/green]")
    console.print(f"Wallet: {wallet.wallet_address}")
    console.print(f"Max loss per trade: ${engine.max_loss_per_trade:.2f}\n")

    items = detect_live_candidates(limit=args.limit)
    if not items:
        console.print("[yellow]No candidates found.[/yellow]")
        return

    console.print(f"[cyan]Scanning {len(items)} candidates...\n[/cyan]")
    results = engine.scan_and_trade(items, auto_sell=args.auto_sell)

    console.print("[cyan]=== LIVE TRADE RESULTS ===[/cyan]")
    console.print(f"Scanned: {results['scanned']}")
    console.print(f"[red]Buy orders (LIVE): {len(results['buy_orders'])}[/red]")
    console.print(f"[red]Sell orders (LIVE): {len(results['sell_orders'])}[/red]")
    console.print(f"Rejected: {len(results['rejected'])}")

    if results["buy_orders"]:
        console.print("\n[red]Live buy orders placed:[/red]")
        for order in results["buy_orders"]:
            console.print(f"  - {order['mint'][:14]}... : {order['status']}")


def cmd_portfolio(args):
    """View portfolio status"""
    try:
        wallet = require_live_wallet()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        return

    engine = TradeEngine(wallet, dry_run=True)
    console.print("[cyan]=== Portfolio ===[/cyan]")
    console.print(f"Wallet: {wallet.wallet_address}")
    console.print(f"Cash balance: ${engine.portfolio.cash_balance:.2f}")
    console.print(f"Open positions: {len(engine.portfolio.get_open_positions())}")
    console.print(f"Total value: ${engine.portfolio.total_value:.2f}")


def build_parser():
    parser = argparse.ArgumentParser(description="Solana Live Crypto Token Detector and Trader")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Scan for new token candidates")
    scan.add_argument("--limit", type=int, default=20)
    scan.set_defaults(func=cmd_scan)

    watch = subparsers.add_parser("watch", help="Watch for new tokens in real-time")
    watch.add_argument("--limit", type=int, default=15)
    watch.add_argument("--interval", type=int, default=30)
    watch.set_defaults(func=cmd_watch)

    wallet = subparsers.add_parser("wallet-status", help="Check wallet configuration")
    wallet.set_defaults(func=cmd_wallet_status)

    dry_run = subparsers.add_parser("dry-run", help="Run simulation with dry-run mode (no real funds)")
    dry_run.add_argument("--limit", type=int, default=20)
    dry_run.add_argument("--auto-sell", action="store_true", help="Automatically sell at take-profit/stop-loss")
    dry_run.set_defaults(func=cmd_dry_run_trade)

    live = subparsers.add_parser("live-trade", help="Execute LIVE trading (REAL FUNDS AT RISK)")
    live.add_argument("--limit", type=int, default=20)
    live.add_argument("--auto-sell", action="store_true", help="Automatically sell at take-profit/stop-loss")
    live.add_argument("--confirm", action="store_true", help="Confirm live trading mode")
    live.set_defaults(func=cmd_live_trade)

    port = subparsers.add_parser("portfolio", help="View current portfolio")
    port.set_defaults(func=cmd_portfolio)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
