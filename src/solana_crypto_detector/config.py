import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AppConfig:
    rpc_url: str = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    trade_mode: str = os.getenv("TRADE_MODE", "paper")
    detection_threshold: float = float(os.getenv("DETECTION_THRESHOLD", "72"))
    max_position_count: int = int(os.getenv("MAX_POSITION_COUNT", "3"))
    max_buy_per_trade: float = float(os.getenv("MAX_BUY_PER_TRADE", "25"))
    stop_loss_percent: float = float(os.getenv("STOP_LOSS_PERCENT", "8"))
    take_profit_percent: float = float(os.getenv("TAKE_PROFIT_PERCENT", "18"))
    risk_per_trade: float = float(os.getenv("RISK_PER_TRADE", "0.15"))
    user_buy_strategy: str = os.getenv("USER_BUY_STRATEGY", "balanced")
    wallet_address: str = os.getenv("WALLET_ADDRESS", "")
    private_key: str = os.getenv("PRIVATE_KEY", "")
    enable_real_trading: bool = os.getenv("ENABLE_REAL_TRADING", "false").lower() == "true"
    jupiter_api_url: str = os.getenv("JUPITER_API_URL", "https://quote-api.jup.ag/v6")


CONFIG = AppConfig()
