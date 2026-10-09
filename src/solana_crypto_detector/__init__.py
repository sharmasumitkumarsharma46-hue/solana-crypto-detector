from __future__ import annotations

import argparse
import time
from rich.console import Console
from rich.table import Table

from solana_crypto_detector.config import CONFIG
from solana_crypto_detector.scanner import scan_for_candidates, should_buy
from solana_crypto_detector.trading import build_policy, paper_portfolio, simulate_trade

console = Console()


def _print_candidates(results, threshold):
    if not results:
        console.print("[yellow]No candidates were detected.[/yellow]")
        return

    table = Table(title=f"Solana token candidates (threshold >= {threshold})")
    table.add_column("Mint", style="cyan")
    table.add_column("Symbol")
    table.add_column("Score")
    table.add_column("Risk")
    table.add_column("Signal")
    table.add_column("Source")

    for candidate in results:
        signal = "BUY" if should_buy(candidate, threshold) else "WATCH"
        table.add_row(
            candidate.mint[:18] + "...",
            candidate.symbol,
            str(candidate.final_score),
            str(candidate.risk_score),
            signal,
            candidate.source,
        )
    console.print(table)


def scan_command(args):
    results = scan_for_candidates(limit=args.limit, threshold=args.threshold)
    _print_candidates(results, args.threshold)


def watch_command(args):
    console.print(f"[green]Watching Solana for new token activity every {args.interval} seconds[/green]")
    try:
        while True:
            results = scan_for_candidates(limit=args.limit, threshold=args.threshold)
            _print_candidates(results, args.threshold)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        console.print("[yellow]Stopping watch mode.[/yellow]")


def paper_trade_command(args):
    policy = build_policy(args.strategy)
    result = simulate_trade(
        mint="demo-mint",
        symbol="DEMO",
        amount_usd=args.amount,
        strategy=args.strategy,
        current_price=args.price,
    )
    wallet = paper_portfolio()
    console.print(f"[green]Paper trade enabled[/green]")
    console.print(f"Mode: {CONFIG.trade_mode}")
    console.print(f"Strategy: {policy.strategy}")
    console.print(f"Cash: ${wallet.cash_balance}")
    console.print(f"Estimated buy amount: ${result['amount_usd']}")
    console.print(f"Qty: {result['quantity']}")


def portfolio_command(args):
    wallet = paper_portfolio()
    console.print(f"[cyan]Portfolio[/cyan]")
    console.print(f"Cash: ${wallet.cash_balance}")
    console.print("Positions: none")


def buy_command(args):
    result = simulate_trade(args.mint, args.symbol or "NEW", args.amount, args.strategy, args.price)
    console.print(f"[green]Buy action planned[/green]")
    console.print(result)


def sell_command(args):
    console.print(f"[yellow]Sell action planned for {args.mint}[/yellow]")
    console.print({"percent": args.percent, "mode": CONFIG.trade_mode})


def build_parser():
    parser = argparse.ArgumentParser(description="Solana token detector and CLI trader")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Scan Solana for new token candidates")
    scan.add_argument("--rpc", default=CONFIG.rpc_url)
    scan.add_argument("--limit", type=int, default=10)
    scan.add_argument("--threshold", type=float, default=CONFIG.detection_threshold)
    scan.set_defaults(func=scan_command)

    watch = subparsers.add_parser("watch", help="Monitor for new tokens in a loop")
    watch.add_argument("--rpc", default=CONFIG.rpc_url)
    watch.add_argument("--interval", type=int, default=30)
    watch.add_argument("--limit", type=int, default=10)
    watch.add_argument("--threshold", type=float, default=CONFIG.detection_threshold)
    watch.set_defaults(func=watch_command)

    paper = subparsers.add_parser("paper-trade", help="Run a paper trade example")
    paper.add_argument("--strategy", choices=["balanced", "aggressive", "conservative"], default=CONFIG.user_buy_strategy)
    paper.add_argument("--amount", type=float, default=25.0)
    paper.add_argument("--price", type=float, default=0.08)
    paper.set_defaults(func=paper_trade_command)

    port = subparsers.add_parser("portfolio", help="Show current portfolio status")
    port.set_defaults(func=portfolio_command)

    buy = subparsers.add_parser("buy", help="Plan a buy order")
    buy.add_argument("--mint", required=True)
    buy.add_argument("--symbol", default="NEW")
    buy.add_argument("--amount", type=float, default=25.0)
    buy.add_argument("--strategy", choices=["balanced", "aggressive", "conservative"], default=CONFIG.user_buy_strategy)
    buy.add_argument("--price", type=float, default=0.08)
    buy.set_defaults(func=buy_command)

    sell = subparsers.add_parser("sell", help="Plan a sell order")
    sell.add_argument("--mint", required=True)
    sell.add_argument("--percent", type=float, default=100.0)
    sell.set_defaults(func=sell_command)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
