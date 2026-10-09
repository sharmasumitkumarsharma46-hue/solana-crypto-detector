# Solana Crypto Token Detector - Complete Live Trading Bot

## What Is This?

A **safe, production-ready Pump.fun auto-trader** that:
- Listens to Pump.fun WebSocket for new token launches in **real-time**
- Fetches Jupiter quotes for pricing
- Auto-executes buy orders based on risk/confidence scoring
- Supports dry-run and live trading modes
- Requires explicit user confirmation for live trades

## Quick Start

### 1. Install

```bash
git clone https://github.com/sharmasumitkumarsharma46-hue/solana-crypto-detector.git
cd solana-crypto-detector
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Discovery Mode (Watch Only)

Monitor Pump.fun launches without trading:

```bash
python -m solana_crypto_detector.pumpfun_cli pump-monitor
```

### 3. Dry-Run Mode (Simulated Trading)

Test your auto-trading logic without real funds:

```bash
python -m solana_crypto_detector.pumpfun_cli pump-dry-run
```

### 4. Live Mode (Real Trading)

**ONLY after testing dry-run extensively!**

Setup .env:
```bash
WALLET_ADDRESS=your_solana_wallet_address
PRIVATE_KEY=your_base58_private_key
ENABLE_REAL_TRADING=true
```

Then run:
```bash
python -m solana_crypto_detector.pumpfun_cli pump-live --confirm
```

## How It Works

### Flow: Pump.fun → Jupiter → Live Buy

1. **Pump.fun WebSocket Listener**
   - Connects to Pump.fun event stream
   - Captures new token launch events in real-time
   - Parses mint, symbol, creator info
   - Auto-scores risk/confidence

2. **Token Validation**
   - Risk score must be below threshold
   - Confidence score must be above threshold
   - Position count must not exceed max
   - Creator validation

3. **Jupiter Quote Fetch**
   - Fetches SOL → Token quote
   - Gets exact price and output amount
   - Checks slippage

4. **Auto-Buy Decision**
   - If dry-run: simulates the trade
   - If live: requires confirmation, then executes
   - Applies stop-loss & take-profit rules

5. **Portfolio Tracking**
   - Tracks open positions
   - Monitors PnL
   - Enforces max positions cap

## Configuration (.env)

```bash
# Wallet (ONLY set for live trading)
WALLET_ADDRESS=
PRIVATE_KEY=
ENABLE_REAL_TRADING=false

# Risk Settings
DETECTION_THRESHOLD=72        # Min confidence to buy
STOP_LOSS_PERCENT=8           # Auto-sell on loss
TAKE_PROFIT_PERCENT=18        # Auto-sell on profit
MAX_BUY_PER_TRADE=25          # USD per trade
MAX_POSITION_COUNT=3          # Max open positions
RISK_PER_TRADE=0.15           # Risk as % of balance

# APIs
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
JUPITER_API_URL=https://quote-api.jup.ag/v6
```

## Safety Features

✓ **Dry-run mode** - Test before going live
✓ **Explicit confirmation** - Must type "YES I UNDERSTAND" for live mode
✓ **Risk scoring** - Automatic evaluation of each token
✓ **Position limits** - Max 3 open positions by default
✓ **Stop-loss/take-profit** - Automatic exit on profit/loss
✓ **Wallet validation** - Private key only loaded when needed
✓ **Error handling** - Graceful recovery from API failures
✓ **Logging** - Session summary on exit

## Commands

```bash
# Monitor tokens (discovery only, no trading)
python -m solana_crypto_detector.pumpfun_cli pump-monitor

# Dry-run auto-trading (simulated)
python -m solana_crypto_detector.pumpfun_cli pump-dry-run

# Live auto-trading (REAL FUNDS)
python -m solana_crypto_detector.pumpfun_cli pump-live --confirm

# Check wallet status
python -m solana_crypto_detector.main_cli wallet-status

# View portfolio
python -m solana_crypto_detector.main_cli portfolio
```

## Important Notes

- **Never commit your private key to git**
- Always test with dry-run first
- Start with small amounts in live mode
- Monitor your trades actively
- Set appropriate stop-loss and take-profit levels
- Be aware of Solana network fees and slippage
- Pump.fun tokens are high-risk and highly volatile
- This tool does NOT guarantee profits

## Troubleshooting

### "Connection failed to Pump.fun"
- Check internet connection
- Try again in a few seconds (auto-reconnects)

### "Quote error"
- Token may have low liquidity
- Jupiter API may be temporarily unavailable
- Try with a different token

### "Wallet not configured"
- Set WALLET_ADDRESS in .env
- Set PRIVATE_KEY in .env
- Set ENABLE_REAL_TRADING=true

### "Max positions reached"
- Close some positions first
- Or increase MAX_POSITION_COUNT in .env

## Performance

- **Detection latency**: < 1 second
- **Quote fetch**: 1-3 seconds
- **Total execution time**: 3-8 seconds from launch

## Disclaimer

This tool is provided as-is. Trading crypto is risky. You may lose money. Use at your own risk. The developers are not liable for any losses.

## License

MIT - Feel free to modify and use

## Support

GitHub Issues: https://github.com/sharmasumitkumarsharma46-hue/solana-crypto-detector/issues
