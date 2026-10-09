from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

import aiohttp
import websockets
from rich.console import Console

console = Console()


@dataclass
class PumpFunToken:
    mint: str
    symbol: str
    name: str
    creator: str
    bonding_curve: str
    associated_bonding_curve: str
    decimals: int = 6
    initial_supply: float = 1_000_000_000.0
    transaction_type: str = "create"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    market_cap: float = 0.0
    liquidity: float = 0.0
    risk_score: float = 45.0
    confidence_score: float = 65.0
    sentiment: str = "neutral"


class PumpFunWebSocketListener:
    def __init__(self, endpoint: str = "wss://pumpportal.fun/api/data", auto_risk_scoring: bool = True):
        self.endpoint = endpoint
        self.auto_risk_scoring = auto_risk_scoring
        self.callbacks: list[Callable[[PumpFunToken], None]] = []
        self.running = False
        self.detected_tokens: dict[str, PumpFunToken] = {}

    def on_token_detected(self, callback: Callable[[PumpFunToken], None]):
        self.callbacks.append(callback)

    def _parse_pump_event(self, data: dict[str, Any]) -> PumpFunToken | None:
        try:
            if data.get("txType") == "create":
                token = PumpFunToken(
                    mint=data.get("mint", "unknown"),
                    symbol=data.get("symbol", "NEW"),
                    name=data.get("name", "New Token"),
                    creator=data.get("user", "unknown"),
                    bonding_curve=data.get("bondingCurveKey", ""),
                    associated_bonding_curve=data.get("associatedBondingCurveKey", ""),
                    decimals=int(data.get("decimals", 6)),
                    initial_supply=float(data.get("initialSupply", 1_000_000_000)),
                    transaction_type="create",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

                if self.auto_risk_scoring:
                    token = self._score_token(token)

                return token
        except Exception as e:
            console.print(f"[red]Error parsing pump event: {e}[/red]")
        return None

    def _score_token(self, token: PumpFunToken) -> PumpFunToken:
        risk_score = 35.0
        confidence_score = 70.0

        if "pump" in token.name.lower():\n            risk_score += 5
            confidence_score -= 3

        if len(token.symbol) > 10:\n            risk_score += 8

        if token.creator == "unknown":\n            risk_score += 12

        token.risk_score = min(100.0, risk_score)
        token.confidence_score = max(0.0, min(100.0, confidence_score))
        token.sentiment = "bullish" if confidence_score >= 72 else "neutral"

        return token

    async def connect_and_listen(self):
        self.running = True
        console.print(f"[cyan]Connecting to Pump.fun WebSocket: {self.endpoint}[/cyan]")

        try:
            async with websockets.connect(self.endpoint, ping_interval=20, ping_timeout=10) as websocket:
                console.print("[green]Connected to Pump.fun!\\nListening for new token launches...[/green]\\n")

                subscribe_msg = json.dumps({
                    "method": "subscribeNewToken",
                })
                await websocket.send(subscribe_msg)

                while self.running:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=60)
                        data = json.loads(message)

                        token = self._parse_pump_event(data)
                        if token:
                            self.detected_tokens[token.mint] = token
                            console.print(f"[green]✓ NEW TOKEN DETECTED[/green]")
                            console.print(f"  Mint: {token.mint[:14]}...")
                            console.print(f"  Symbol: {token.symbol}")
                            console.print(f"  Risk: {token.risk_score:.1f} | Confidence: {token.confidence_score:.1f}")
                            console.print(f"  Time: {token.timestamp}\\n")

                            for callback in self.callbacks:
                                try:
                                    callback(token)
                                except Exception as e:
                                    console.print(f"[red]Callback error: {e}[/red]")

                    except asyncio.TimeoutError:
                        console.print("[yellow]Ping timeout, reconnecting...[/yellow]")
                        break
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        console.print(f"[red]Error: {e}[/red]")
                        break

        except Exception as e:
            console.print(f"[red]Connection failed: {e}[/red]")
            console.print("[yellow]Retrying in 5 seconds...[/yellow]")
            await asyncio.sleep(5)
            if self.running:
                await self.connect_and_listen()

    def stop(self):
        self.running = False
        console.print("[yellow]Stopping listener...[/yellow]")

    async def run(self):
        await self.connect_and_listen()


class PumpFunMonitor:
    def __init__(self, auto_risk_scoring: bool = True):
        self.listener = PumpFunWebSocketListener(auto_risk_scoring=auto_risk_scoring)
        self.tokens_detected = 0
        self.tokens_by_risk: dict[str, list[PumpFunToken]] = {
            "low": [],
            "medium": [],
            "high": [],
        }

    def on_new_token(self, token: PumpFunToken):
        self.tokens_detected += 1
        risk_level = "high" if token.risk_score > 60 else "medium" if token.risk_score > 30 else "low"
        self.tokens_by_risk[risk_level].append(token)
        console.print(f"[cyan]Total detected: {self.tokens_detected}[/cyan]")

    async def start_monitoring(self):
        self.listener.on_token_detected(self.on_new_token)
        await self.listener.run()

    def stop_monitoring(self):
        self.listener.stop()

    def get_detected_tokens(self, risk_level: str | None = None) -> list[PumpFunToken]:
        if risk_level:
            return self.tokens_by_risk.get(risk_level, [])
        return [
            *self.tokens_by_risk["low"],
            *self.tokens_by_risk["medium"],
            *self.tokens_by_risk["high"],
        ]


async def demo_pump_listener():
    monitor = PumpFunMonitor(auto_risk_scoring=True)
    try:
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        console.print("[yellow]Listener stopped by user[/yellow]")
        monitor.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(demo_pump_listener())
