from __future__ import annotations

import argparse

from rich.console import Console
from rich.table import Table

from .config import CONFIG
from .jupiter_trader import JupiterTrader, SOL_MINT, USDC_MINT
from .token_detector import detect_live_candidates
from .wallet import load_wallet_config, require_live_wallet

console = Console()


def _print_candidates(items):
    if not items:
        console.print("[yellow]No live candidates found.[/yellow]")
        return

    table = Table(title="Live Solana token candidates")
    table.add_column("Mint")
    table.add_column("Symbol")
    table.add_column("Name")
    table.add_column("Risk")
    table.add_column("Confidence")
    table.add_column("Sentiment")

    for item in items:
        table.add_row(
            item.mint[:14] + "...",
            item.symbol,
            item.name,
            f"{item.risk_score:.1f}",
            f"{item.confidence_score:.1f}",
            item.sentiment,
        )
    console.print(table)


def command_live_scan(args):
    items = detect_live_candidates(limit=args.limit)
    _print_candidates(items)


def command_live_trade(args):
    cfg = load_wallet_config()
    if not cfg.enable_real_trading:
        console.print("[red]Live trading is disabled. Set ENABLE_REAL_TRADING=true and valid wallet values first.[/red]")
        return

    try:
        wallet = require_live_wallet()
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        return

    trader = JupiterTrader(CONFIG.jupiter_api_url)
    try:
        quote = trader.get_quote(SOL_MINT, args.output_mint, int(args.amount * 1_000_000_000), slippage_bps=args.slippage_bps)
        console.print("[green]Live quote fetched successfully.[/green]")
        console.print(f"Quote: {quote.get('outAmount', 'n/a')}")
        console.print(f"Wallet: {wallet.wallet_address}")
    except Exception as exc:
        console.print(f"[red]Live quote error: {exc}[/red]")


def command_wallet_status(args):
    cfg = load_wallet_config()
    console.print("[cyan]Wallet configuration[/cyan]")
    console.print(f"Wallet address set: {bool(cfg.wallet_address)}")
    console.print(f"Private key set: {bool(cfg.private_key)}")
    console.print(f"Live trading enabled: {cfg.enable_real_trading}")


def build_parser():
    parser = argparse.ArgumentParser(description="Solana token detector and live trader")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("live-scan", help="Scan for new token candidates from Jupiter metadata")
    scan.add_argument("--limit", type=int, default=20)
    scan.set_defaults(func=command_live_scan)

    trade = subparsers.add_parser("live-trade", help="Fetch a live Jupiter quote for a real wallet")
    trade.add_argument("--amount", type=float, default=0.1)
    trade.add_argument("--output-mint", default=USDC_MINT)
    trade.add_argument("--slippage-bps", type=int, default=50)
    trade.set_defaults(func=command_live_trade)

    wallet = subparsers.add_parser("wallet-status", help="Check current live wallet setup")
    wallet.set_defaults(func=command_wallet_status)

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
