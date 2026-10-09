# Solana Crypto Token Detector - Quick Start Guide

## Installation

```bash
git clone https://github.com/sharmasumitkumarsharma46-hue/solana-crypto-detector.git
cd solana-crypto-detector
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

```bash
cp .env.example .env
# Edit .env with your settings
```

## Usage

### 1. Scan for New Tokens

```bash
python -m solana_crypto_detector.main_cli scan --limit 20
```

### 2. Watch Mode (Real-time Monitoring)

```bash
python -m solana_crypto_detector.main_cli watch --limit 15 --interval 30
```

### 3. Check Wallet Status

```bash
python -m solana_crypto_detector.main_cli wallet-status
```

### 4. DRY RUN (Simulate Trading - NO REAL FUNDS)

```bash
python -m solana_crypto_detector.main_cli dry-run --limit 20
python -m solana_crypto_detector.main_cli dry-run --limit 20 --auto-sell
```

### 5. View Portfolio

```bash
python -m solana_crypto_detector.main_cli portfolio
```

### 6. LIVE TRADING (REAL FUNDS - Use with Caution)

**WARNING: This will use your actual Solana wallet and real funds!**

Before running live trading:
1. Test with `dry-run` mode multiple times
2. Set `WALLET_ADDRESS` and `PRIVATE_KEY` in `.env`
3. Set `ENABLE_REAL_TRADING=true` in `.env`
4. Confirm you understand the risks

```bash
python -m solana_crypto_detector.main_cli live-trade --limit 20 --confirm
python -m solana_crypto_detector.main_cli live-trade --limit 20 --confirm --auto-sell
```

## Strategy Configuration

Edit `.env` to customize:

- `DETECTION_THRESHOLD` - Minimum confidence score to buy (0-100)
- `STOP_LOSS_PERCENT` - Auto-sell if loss exceeds this %
- `TAKE_PROFIT_PERCENT` - Auto-sell if profit reaches this %
- `MAX_BUY_PER_TRADE` - Maximum USD per trade
- `MAX_POSITION_COUNT` - Max simultaneous positions
- `RISK_PER_TRADE` - Risk percentage per trade
- `USER_BUY_STRATEGY` - Strategy type: balanced, aggressive, conservative

## Safety Features

✓ Dry-run mode by default (no real funds)
✓ Wallet validation and encryption
✓ Risk scoring and position limits
✓ Stop-loss and take-profit enforcement
✓ User confirmation gates before live trading
✓ Manual confirmation required for live operations

## Important Notes

- **NEVER commit your private key to git**
- Always test with dry-run mode first
- Start with small amounts in live mode
- Monitor your trades actively
- Set appropriate stop-loss and take-profit levels
- Be aware of transaction fees and slippage

## Troubleshooting

### "Real trading is disabled" error
- Make sure `ENABLE_REAL_TRADING=true` in `.env`
- Verify `WALLET_ADDRESS` and `PRIVATE_KEY` are set

### "No live candidates found"
- Check your internet connection
- Verify `SOLANA_RPC_URL` is correct
- Try a different RPC endpoint

### Transaction failures
- Ensure you have enough SOL for transaction fees
- Check Jupiter API status
- Verify token mint is valid

## Support

For issues, check the GitHub repository: 
https://github.com/sharmasumitkumarsharma46-hue/solana-crypto-detector
