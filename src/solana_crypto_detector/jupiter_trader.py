from __future__ import annotations

import base64
from typing import Any

import requests

from .config import CONFIG
from .wallet import SolanaWallet


class JupiterTrader:
    def __init__(self, api_url: str | None = None):
        self.api_url = (api_url or CONFIG.jupiter_api_url).rstrip("/")

    def get_quote(self, input_mint: str, output_mint: str, amount: int, slippage_bps: int = 50) -> dict[str, Any]:
        url = f"{self.api_url}/quote"
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "slippageBps": str(slippage_bps),
            "onlyDirectRoutes": "false",
            "asLegacyTransaction": "false",
        }
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if "error" in payload:
            raise RuntimeError(f"Jupiter quote error: {payload['error']}")
        return payload

    def execute_swap(self, wallet: SolanaWallet, quote: dict[str, Any], slippage_bps: int = 50, dry_run: bool = True) -> dict[str, Any]:
        if dry_run:
            return {
                "dry_run": True,
                "wallet": wallet.wallet_address,
                "quote": quote,
                "message": "Dry run only. Set dry_run=False to attempt a live swap.",
            }

        url = f"{self.api_url}/swap"
        payload = {
            "quoteResponse": quote,
            "userPublicKey": wallet.wallet_address,
            "wrapAndUnwrapSol": True,
            "slippageBps": slippage_bps,
            "dynamicComputeUnitLimit": True,
            "prioritizationFeeLamports": "auto",
        }
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        if "swapTransaction" not in data:
            raise RuntimeError(f"Jupiter swap failed: {data}")

        raw_tx = base64.b64decode(data["swapTransaction"])
        signed = wallet.sign_transaction(raw_tx)
        return {
            "dry_run": False,
            "signed": signed,
            "response": data,
        }


SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeMRefm4qz5U2d9hGHQxK4vfxQx2A4"


def build_buy_quote(trader: JupiterTrader, amount_sol: float, output_mint: str = USDC_MINT, slippage_bps: int = 50) -> dict[str, Any]:
    return trader.get_quote(SOL_MINT, output_mint, int(amount_sol * 1_000_000_000), slippage_bps=slippage_bps)


def build_sell_quote(trader: JupiterTrader, amount_usdc: float, input_mint: str = USDC_MINT, slippage_bps: int = 50) -> dict[str, Any]:
    return trader.get_quote(input_mint, SOL_MINT, int(amount_usdc * 1_000_000), slippage_bps=slippage_bps)
