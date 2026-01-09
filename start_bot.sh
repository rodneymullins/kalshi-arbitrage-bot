#!/bin/bash
# Quick start guide for running the bot

set -e

echo "=============================================="
echo "🤖 Kalshi Bot - Quick Start Guide"
echo "=============================================="
echo ""

# Check location
if [ ! -f "bot_v3.py" ]; then
    echo "❌ Error: Run from /Users/rod/Antigravity/kalshi_bot directory"
    exit 1
fi

echo "Select mode:"
echo "  1) DRY RUN (paper trading - safe)"
echo "  2) SNAPSHOT TEST (find opportunities - safe)"
echo "  3) PROBABILITY ARBITRAGE SCANNER (safe)"
echo "  4) LIVE TRADING (⚠️  real money!)"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        echo ""
        echo "Starting DRY RUN mode..."
        echo "Bot will show decisions but NOT execute trades"
        echo ""
        export BOT_MODE=DRY
        python3 bot_v3.py
        ;;
    2)
        echo ""
        echo "Running snapshot test..."
        echo "Scanning current markets for opportunities"
        echo ""
        python3 backtest.py --mode snapshot
        ;;
    3)
        echo ""
        echo "Running probability arbitrage scanner..."
        echo "Looking for YES + NO price mismatches"
        echo ""
        python3 strategies/probability_arb.py
        ;;
    4)
        echo ""
        echo "⚠️  ⚠️  ⚠️  WARNING ⚠️  ⚠️  ⚠️"
        echo "You are about to enable LIVE TRADING"
        echo "Real money will be used!"
        echo ""
        read -p "Are you SURE? Type 'YES' to confirm: " confirm
        
        if [ "$confirm" = "YES" ]; then
            echo ""
            echo "Starting LIVE TRADING mode..."
            echo "Circuit breaker active (3 consecutive losses)"
            echo ""
            export BOT_MODE=LIVE
            python3 bot_v3.py
        else
            echo "Cancelled."
            exit 0
        fi
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
