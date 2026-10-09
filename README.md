# solana-crypto-detector

A CLI-based Solana trading assistant that looks for fresh/new crypto tokens on the Solana chain, scores them by risk/reward, and can buy/sell based on a user-configurable strategy.

This project is intentionally safe by default:
- paper-trading mode is enabled unless a real wallet is configured
- no live wallet action is performed without explicit config
- all decisions are logged and explained

## Features

- Detect new token candidates from Solana RPC + recent token activity
- Score each token with a risk/reward model
- Buy/sell logic based on user strategy
- CLI commands for scan, watch, portfolio, and paper-trade
- Config through `.env` or command flags

## Quick start

1. Create a virtual environment
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. Copy the example config
   ```bash
   cp .env.example .env
   ```

4. Run a scan
   ```bash
   python -m solana_crypto_detector.cli scan --limit 20 --threshold 70
   ```

5. Run paper trading monitor
   ```bash
   python -m solana_crypto_detector.cli watch --interval 30 --threshold 72
   ```

## Example commands

```bash
python -m solana_crypto_detector.cli scan --rpc https://api.mainnet-beta.solana.com --limit 15 --threshold 72
python -m solana_crypto_detector.cli paper-trade --amount 25 --strategy balanced
python -m solana_crypto_detector.cli portfolio
python -m solana_crypto_detector.cli buy --mint 4zMMC9sX... --amount 10 --strategy balanced
python -m solana_crypto_detector.cli sell --mint 4zMMC9sX... --percent 100
```

## Important notes

- This is a research / trading assistant starter.
- Real wallet trading requires setting a valid Solana RPC URL and wallet configuration.
- For safety, `--real` is disabled unless explicitly enabled.

## Environment variables

See `.env.example` for the available options.
