#!/bin/bash

echo "Solana Crypto Token Detector - Setup"
echo "====================================="
echo ""

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "⚠️  Edit .env with your wallet details before running live trading"
fi

echo ""
echo "✓ Setup complete!"
echo ""
echo "Quick start:"
echo "  1. Edit .env (set wallet details ONLY for live mode)"
echo "  2. Test: python -m solana_crypto_detector.pumpfun_cli pump-monitor"
echo "  3. Dry-run: python -m solana_crypto_detector.pumpfun_cli pump-dry-run"
echo "  4. Live: python -m solana_crypto_detector.pumpfun_cli pump-live --confirm"
echo ""
