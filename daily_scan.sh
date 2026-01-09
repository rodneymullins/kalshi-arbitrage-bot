#!/bin/bash
# Daily Kalshi Market Scanner - Auto-update bot ticker
# Run daily via cron to find the best liquid market

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🔍 Kalshi Daily Market Scan - $(date)"
echo "================================"

# Run the fast scanner and save output
SCAN_OUTPUT=$(python3 market_scanner_fast.py 2>&1)

# Extract the best ticker
BEST_TICKER=$(echo "$SCAN_OUTPUT" | grep -A 3 "💡 Best market:" | grep "ticker = " | cut -d'"' -f2)

if [ -z "$BEST_TICKER" ]; then
    echo "❌ Failed to identify best market. Scanner output:"
    echo "$SCAN_OUTPUT"
    exit 1
fi

echo ""
echo "✅ Best market identified: $BEST_TICKER"
echo ""

# Check if bot is currently running
BOT_PID=$(pgrep -f "bot_fixed.py" || true)

if [ ! -z "$BOT_PID" ]; then
    echo "⚠️  Bot is currently running (PID: $BOT_PID)"
    echo "   Stopping bot before updating ticker..."
    pkill -f bot_fixed.py
    sleep 2
fi

# Update the ticker in bot_fixed.py
echo "📝 Updating bot_fixed.py with new ticker..."
sed -i.bak "s/ticker = \".*\"/ticker = \"$BEST_TICKER\"/" bot_fixed.py

# Verify the change
NEW_TICKER=$(grep '^ticker = ' bot_fixed.py | head -1 | cut -d'"' -f2)
if [ "$NEW_TICKER" = "$BEST_TICKER" ]; then
    echo "✅ Ticker updated successfully: $NEW_TICKER"
else
    echo "❌ Ticker update failed!"
    mv bot_fixed.py.bak bot_fixed.py
    exit 1
fi

echo ""
echo "📊 Scan Summary:"
echo "$SCAN_OUTPUT" | tail -20

echo ""
echo "================================"
echo "✅ Daily scan complete!"
echo "   To restart bot: nohup python3 -u bot_fixed.py > trading.log 2>&1 &"
