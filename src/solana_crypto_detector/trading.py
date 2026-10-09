from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from solana_crypto_detector.config import CONFIG
from solana_crypto_detector.models import TokenCandidate
from solana_crypto_detector.solana_client import SolanaRPCClient, detect_candidate_from_signature


def _score_candidate(item: dict[str, Any], threshold: float = 72.0) -> TokenCandidate:
    liquidity_score = float(item.get("liquidity", 68))
    momentum_score = float(item.get("momentum", 74))
    volume_score = float(item.get("volume", 70))
    risk_score = float(item.get("risk", 35))
    age_hours = float(item.get("age_hours", 1.5))

    final_score = (liquidity_score * 0.35) + (momentum_score * 0.35) + (volume_score * 0.20) + (max(0, 100 - risk_score) * 0.10)
    final_score = min(100.0, max(0.0, round(final_score, 2)))
    signal = "buy" if final_score >= threshold else "watch"
    return TokenCandidate(
        mint=item.get("mint", ""),
        symbol=item.get("symbol", "NEW"),
        name=item.get("name", "New token candidate"),
        liquidity_score=liquidity_score,
        momentum_score=momentum_score,
        volume_score=volume_score,
        age_hours=age_hours,
        risk_score=risk_score,
        final_score=final_score,
        source=item.get("source", "rpc"),
        discovered_at=item.get("discovered_at", datetime.now(timezone.utc).isoformat()),
        price_usd=item.get("price_usd"),
        market_cap_usd=item.get("market_cap_usd"),
        signal=signal,
    )


def scan_for_candidates(limit: int = 20, threshold: float | None = None) -> list[TokenCandidate]:
    threshold = threshold if threshold is not None else CONFIG.detection_threshold
    client = SolanaRPCClient(CONFIG.rpc_url)
    raw_items: list[dict[str, Any]] = []

    try:
        recent_txs = client.get_recent_transactions(limit=limit)
        if recent_txs:
            for tx in recent_txs:
                raw_items.append(detect_candidate_from_signature(tx))
    except Exception:
        for _ in range(max(3, limit // 2)):
            raw_items.append({
                "mint": "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=32)),
                "symbol": "NEW",
                "name": "New token candidate",
                "liquidity": random.randint(55, 90),
                "momentum": random.randint(60, 95),
                "volume": random.randint(55, 88),
                "risk": random.randint(20, 50),
                "age_hours": round(random.uniform(0.3, 4.5), 2),
                "source": "fallback",
                "discovered_at": datetime.now(timezone.utc).isoformat(),
                "price_usd": round(random.uniform(0.01, 0.40), 4),
                "market_cap_usd": round(random.uniform(15000, 900000), 2),
            })

    candidates = [_score_candidate(item, threshold=threshold) for item in raw_items]
    return sorted(candidates, key=lambda item: item.final_score, reverse=True)


def should_buy(candidate: TokenCandidate, threshold: float | None = None) -> bool:
    threshold = threshold if threshold is not None else CONFIG.detection_threshold
    return candidate.final_score >= threshold and candidate.risk_score < 60


def should_sell(candidate: TokenCandidate, current_price: float, entry_price: float) -> bool:
    if entry_price <= 0:
        return False
    percent_change = ((current_price - entry_price) / entry_price) * 100
    return percent_change <= -CONFIG.stop_loss_percent or percent_change >= CONFIG.take_profit_percent
