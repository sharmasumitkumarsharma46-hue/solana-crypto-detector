# Solana Crypto Detector

This project detects Pump.fun tokens, validates them, and can execute trading logic with risk controls.

## System Fee Policy

This application enforces a fixed system fee policy on every trade:

- Buy fee: 2.5%
- Sell fee: 2.5%
- Fee wallet: `AjKhH8NV4VgmnWYwCJKoDVkeKEevMkQXWj8T7HfSiFzK`
- Override: not allowed from `.env`, runtime config, or user input

The fee wallet and percentages are locked in the backend configuration and trade engine, so users cannot change them.

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and set wallet values only if enabling live trading.

3. Run in dry-run mode:
   ```bash
   python -m solana_crypto_detector.pumpfun_cli pump-dry-run
   ```

4. Run in live mode when enabled and confirmed:
   ```bash
   python -m solana_crypto_detector.pumpfun_cli pump-live --confirm
   ```

## Notes

- Dry run is recommended before any real trading.
- Trade fees are calculated automatically before execution and are logged with the locked fee wallet.
- This repository is intended for controlled and monitored trading workflows.
