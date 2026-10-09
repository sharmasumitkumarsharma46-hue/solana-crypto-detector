from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import requests


@dataclass
class TokenMetadata:
    mint: str
    symbol: str
    name: str
    decimals: int = 9
    website: str | None = None
    total_supply: str | None = None
    source: str = "jupiter"
    discovered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sentiment: str = "neutral"
    risk_score: float = 35.0
    confidence_score: float = 70.0


class TokenLaunchDetector:
    def __init__(self, rpc_url: str | None = None):
        self.rpc_url = rpc_url or "https://api.mainnet-beta.solana.com"

    def fetch_jupiter_tokens(self, limit: int = 25) -> list[dict[str, Any]]:
        url = "https://tokens.jup.ag/tokens"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list):
            return payload[:limit]
        if isinstance(payload, dict) and "tokens" in payload:
            return payload["tokens"][:limit]
        return []

    def build_candidate(self, item: dict[str, Any]) -> TokenMetadata:
        mint = str(item.get("address") or item.get("mint") or "unknown")
        symbol = str(item.get("symbol") or "NEW")
        name = str(item.get("name") or "New token")
        decimals = int(item.get("decimals") or 9)
        website = item.get("website") or (item.get("extensions") or {}).get("website")
        total_supply = item.get("totalSupply") or item.get("supply")
        risk_score = 22.0 + (decimals % 10) * 3.5
        confidence_score = 70.0 + (100 - risk_score) * 0.35
        confidence_score = max(0.0, min(100.0, confidence_score))
        sentiment = "bullish" if confidence_score >= 74 else "neutral"

        return TokenMetadata(
            mint=mint,
            symbol=symbol,
            name=name,
            decimals=decimals,
            website=website,
            total_supply=str(total_supply) if total_supply is not None else None,
            source="jupiter",
            discovered_at=datetime.now(timezone.utc).isoformat(),
            sentiment=sentiment,
            risk_score=risk_score,
            confidence_score=confidence_score,
        )

    def detect_new_tokens(self, limit: int = 25) -> list[TokenMetadata]:
        tokens = self.fetch_jupiter_tokens(limit=limit)
        return [self.build_candidate(item) for item in tokens]


def detect_live_candidates(limit: int = 20) -> list[TokenMetadata]:
    return TokenLaunchDetector().detect_new_tokens(limit=limit)
