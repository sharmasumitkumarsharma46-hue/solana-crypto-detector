from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import aiohttp
from rich.console import Console

console = Console()


@dataclass
class CachedQuote:
    quote: dict[str, Any]
    timestamp: float
    token_mint: str
    expiry_ms: int = 2000  # Cache for 2 seconds


class FastQuoteEngine:
    """Ultra-fast quote engine with caching and parallel fetching"""

    def __init__(self, max_cache_size: int = 1000):
        self.quote_cache: dict[str, CachedQuote] = {}
        self.max_cache_size = max_cache_size
        self.session: aiohttp.ClientSession | None = None
        self.performance_metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_fetch_time_ms": 0,
            "parallel_fetches": 0,
        }

    async def init_session(self):
        """Initialize persistent HTTP session for connection pooling"""
        if not self.session:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
                enable_cleanup_closed=True,
            )
            timeout = aiohttp.ClientTimeout(total=5, connect=1, sock_read=2)
            self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
            console.print("[green]✓ Connection pool initialized[/green]")

    async def close_session(self):
        """Close persistent session"""
        if self.session:
            await self.session.close()

    def _cache_key(self, from_mint: str, to_mint: str, amount: int) -> str:
        return f"{from_mint}:{to_mint}:{amount}"

    def _is_cache_valid(self, cached: CachedQuote) -> bool:
        age_ms = (time.time() - cached.timestamp) * 1000
        return age_ms < cached.expiry_ms

    async def get_quote_fast(self, from_mint: str, to_mint: str, amount: int) -> dict[str, Any] | None:
        """Get quote with caching (target: <300ms)"""
        cache_key = self._cache_key(from_mint, to_mint, amount)

        # Check cache first
        if cache_key in self.quote_cache:
            cached = self.quote_cache[cache_key]
            if self._is_cache_valid(cached):
                self.performance_metrics["cache_hits"] += 1
                age_ms = (time.time() - cached.timestamp) * 1000
                console.print(f"[green]⚡ Cache hit ({age_ms:.0f}ms old)[/green]")
                return cached.quote

        # Cache miss - fetch new
        self.performance_metrics["cache_misses"] += 1
        start_time = time.time()

        try:
            quote = await self._fetch_quote_async(from_mint, to_mint, amount)
            fetch_time_ms = (time.time() - start_time) * 1000

            if quote:
                # Store in cache
                cached_quote = CachedQuote(
                    quote=quote,
                    timestamp=time.time(),
                    token_mint=to_mint,
                    expiry_ms=2000,
                )
                self.quote_cache[cache_key] = cached_quote

                # Keep cache size manageable
                if len(self.quote_cache) > self.max_cache_size:
                    oldest_key = min(self.quote_cache.keys(), key=lambda k: self.quote_cache[k].timestamp)
                    del self.quote_cache[oldest_key]

                console.print(f"[cyan]⏱️  Quote fetched in {fetch_time_ms:.0f}ms[/cyan]")
                return quote
        except Exception as e:
            console.print(f"[red]✗ Quote fetch failed: {e}[/red]")

        return None

    async def _fetch_quote_async(self, from_mint: str, to_mint: str, amount: int) -> dict[str, Any] | None:
        """Async quote fetch from Jupiter API"""
        if not self.session:
            await self.init_session()

        url = "https://quote-api.jup.ag/v6/quote"
        params = {
            "inputMint": from_mint,
            "outputMint": to_mint,
            "amount": amount,
            "slippageBps": 50,
        }

        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=2)) as resp:
                if resp.status == 200:
                    return await resp.json()
        except asyncio.TimeoutError:
            console.print("[yellow]⚠️  Quote timeout (using fallback)[/yellow]")
        except Exception as e:
            console.print(f"[red]Quote error: {e}[/red]")

        return None

    async def get_quotes_parallel(self, requests: list[tuple[str, str, int]]) -> list[dict[str, Any] | None]:
        """Fetch multiple quotes in parallel (target: <500ms for 5 quotes)"""
        self.performance_metrics["parallel_fetches"] += len(requests)
        tasks = [self.get_quote_fast(from_mint, to_mint, amount) for from_mint, to_mint, amount in requests]
        return await asyncio.gather(*tasks, return_exceptions=False)

    def get_performance_stats(self) -> dict[str, Any]:
        """Get performance metrics"""
        total_fetches = self.performance_metrics["cache_hits"] + self.performance_metrics["cache_misses"]
        hit_rate = (
            self.performance_metrics["cache_hits"] / total_fetches * 100 if total_fetches > 0 else 0
        )
        return {
            "cache_hits": self.performance_metrics["cache_hits"],
            "cache_misses": self.performance_metrics["cache_misses"],
            "hit_rate_percent": hit_rate,
            "cache_size": len(self.quote_cache),
        }

    def print_performance_stats(self):
        """Print performance report"""
        stats = self.get_performance_stats()
        console.print("\n[cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/cyan]")
        console.print("[cyan]⚡ QUOTE ENGINE PERFORMANCE[/cyan]")
        console.print("[cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/cyan]")
        console.print(f"[green]✓ Cache Hits:[/green] {stats['cache_hits']}")
        console.print(f"[red]✗ Cache Misses:[/red] {stats['cache_misses']}")
        console.print(f"[yellow]📊 Hit Rate:[/yellow] {stats['hit_rate_percent']:.1f}%")
        console.print(f"[blue]📦 Cache Size:[/blue] {stats['cache_size']}")
        console.print("[cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/cyan]\n")
