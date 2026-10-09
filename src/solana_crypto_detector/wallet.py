import os
from dataclasses import dataclass

import base58
from dotenv import load_dotenv

load_dotenv()

try:
    from solders.keypair import Keypair
except Exception:
    Keypair = None


@dataclass
class WalletConfig:
    wallet_address: str = ""
    private_key: str = ""
    enable_real_trading: bool = False


def load_wallet_config() -> WalletConfig:
    return WalletConfig(
        wallet_address=os.getenv("WALLET_ADDRESS", "").strip(),
        private_key=os.getenv("PRIVATE_KEY", "").strip(),
        enable_real_trading=os.getenv("ENABLE_REAL_TRADING", "false").lower() == "true",
    )


def validate_private_key(private_key: str) -> bool:
    if not private_key:
        return False
    try:
        key_bytes = base58.b58decode(private_key)
        return len(key_bytes) == 32
    except Exception:
        return False


class SolanaWallet:
    def __init__(self, private_key: str, wallet_address: str | None = None):
        if not validate_private_key(private_key):
            raise ValueError("Invalid or empty Solana private key. Please set PRIVATE_KEY in the environment.")
        if Keypair is None:
            raise RuntimeError("solders package is not installed. Run: pip install -r requirements.txt")

        self.private_key = private_key
        self.keypair = Keypair.from_base58_string(private_key)
        self.wallet_address = wallet_address or str(self.keypair.pubkey())

    @property
    def public_key(self) -> str:
        return self.wallet_address

    def sign_transaction(self, transaction: object) -> object:
        return transaction

    def sign_and_send(self, transaction: object, client: object | None = None) -> str:
        if client is None:
            raise ValueError("Solana RPC client is required to send a signed transaction.")
        try:
            return client.send_transaction(transaction, self.keypair)
        except TypeError:
            return client.send_transaction(transaction, self.keypair, opts={"skip_preflight": False})


def require_live_wallet() -> SolanaWallet:
    cfg = load_wallet_config()
    if not cfg.enable_real_trading:
        raise RuntimeError("Real trading is disabled. Set ENABLE_REAL_TRADING=true and provide PRIVATE_KEY and WALLET_ADDRESS.")
    if not cfg.private_key or not cfg.wallet_address:
        raise RuntimeError("WALLET_ADDRESS and PRIVATE_KEY must be set before enabling live trading.")
    return SolanaWallet(cfg.private_key, cfg.wallet_address)
