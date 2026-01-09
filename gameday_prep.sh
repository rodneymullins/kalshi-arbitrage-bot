#!/bin/bash
# Game Day Preparation Script for Kalshi Trading Bot
# Run this script before peak trading hours

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🏀 KALSHI BOT - GAME DAY PREP"
echo "Time: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "================================================================"

# 1. Stop any running bots
echo ""
echo "1️⃣  Checking for running bots..."
BOT_PIDS=$(pgrep -f "bot.*\.py" || true)
if [ ! -z "$BOT_PIDS" ]; then
    echo "   ⚠️  Found running bot processes: $BOT_PIDS"
    echo "   Stopping them..."
    pkill -f "bot.*\.py" || true
    sleep 2
    echo "   ✅ Stopped"
else
    echo "   ✅ No bots currently running"
fi

# 2. Run market scanner to find best opportunities
echo ""
echo "2️⃣  Scanning markets for today's opportunities..."
python3 market_scanner_fast.py > scan_results.txt 2>&1

# Extract best market
BEST_TICKER=$(grep "💡 Best market:" scan_results.txt | head -1 | sed -E 's/.*: ([A-Z0-9-]+).*/\1/')
BEST_SCORE=$(grep "Score:" scan_results.txt | head -1 | sed -E 's/.*Score: ([0-9]+)\/100.*/\1/')

if [ -z "$BEST_TICKER" ]; then
    echo "   ❌ Failed to identify best market"
    echo "   Check scan_results.txt for details"
    exit 1
fi

echo "   ✅ Best market identified:"
echo "      Ticker: $BEST_TICKER"
echo "      Score: $BEST_SCORE/100"

# 3. Update bot configuration
echo ""
echo "3️⃣  Updating bot_v3.py with best market..."
sed -i.bak "s/ticker = \".*\"/ticker = \"$BEST_TICKER\"/" bot_v3.py
echo "   ✅ Updated"

# 4. Check market conditions
echo ""
echo "4️⃣  Checking current market conditions..."
MARKET_INFO=$(python3 -c "
import os, requests, base64, time
from dotenv import load_dotenv
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

load_dotenv()
key = os.getenv('KALSHI_KEY_ID')
with open('kalshi.key', 'rb') as f:
    pk = serialization.load_pem_private_key(f.read(), password=None)

def sign(method, path, ts):
    msg = f'{ts}{method}{path}'
    sig = pk.sign(msg.encode(), padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
    return base64.b64encode(sig).decode()

ticker = '$BEST_TICKER'
ts = str(int(time.time() * 1000))
path = f'/trade-api/v2/markets/{ticker}'
h = {'KALSHI-ACCESS-KEY': key, 'KALSHI-ACCESS-SIGNATURE': sign('GET', path, ts), 'KALSHI-ACCESS-TIMESTAMP': ts}
r = requests.get(f'https://api.elections.kalshi.com{path}', headers=h, timeout=10)

if r.status_code == 200:
    m = r.json().get('market', {})
    print(f\"Volume: \\\${m.get('volume', 0):,}\")
    print(f\"Title: {m.get('title', '')[:60]}\")
else:
    print('Error fetching market info')
" 2>&1)

echo "$MARKET_INFO" | while read line; do echo "      $line"; done

# 5. Check orderbook
echo ""
echo "5️⃣  Checking orderbook status..."
ORDERBOOK_STATUS=$(python3 -c "
import os, requests, base64, time
from dotenv import load_dotenv
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

load_dotenv()
key = os.getenv('KALSHI_KEY_ID')
with open('kalshi.key', 'rb') as f:
    pk = serialization.load_pem_private_key(f.read(), password=None)

def sign(method, path, ts):
    msg = f'{ts}{method}{path}'
    sig = pk.sign(msg.encode(), padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
    return base64.b64encode(sig).decode()

ticker = '$BEST_TICKER'
ts = str(int(time.time() * 1000))
path = f'/trade-api/v2/markets/{ticker}/orderbook'
h = {'KALSHI-ACCESS-KEY': key, 'KALSHI-ACCESS-SIGNATURE': sign('GET', path, ts), 'KALSHI-ACCESS-TIMESTAMP': ts}
r = requests.get(f'https://api.elections.kalshi.com{path}', headers=h, timeout=10)

if r.status_code == 200:
    ob = r.json().get('orderbook', {})
    yes_asks = ob.get('yes', [])
    
    if yes_asks:
        best_price = min([x[0]/100 for x in yes_asks])
        print(f'ACTIVE - {len(yes_asks)} orders, best ask: \\\${best_price:.2f}')
    else:
        print('EMPTY - No orders in orderbook')
else:
    print('Error checking orderbook')
" 2>&1)

echo "      $ORDERBOOK_STATUS"

# 6. Display preparation summary
echo ""
echo "================================================================"
echo "📊 PREPARATION SUMMARY"
echo "================================================================"
echo ""
echo "Tonight's NBA Schedule:"
echo "   7:10 PM ET - Raptors @ Hornets, Bulls @ Pistons, Wizards @ 76ers"
echo "   7:40 PM ET - Nuggets @ Celtics, Clippers @ Knicks, Pelicans @ Hawks, Magic @ Nets"
echo "   8:10 PM ET - Suns @ Grizzlies, Jazz @ Thunder"
echo "   9:30 PM ET - Lakers @ Spurs (ESPN)"
echo "   10:10 PM ET - Rockets @ Trail Blazers, Bucks @ Warriors"
echo ""
echo "Target Market:"
echo "   Ticker: $BEST_TICKER"
echo "   Score: $BEST_SCORE/100"
echo "   Orderbook: $ORDERBOOK_STATUS"
echo ""
echo "Recommended Trading Window: 6:00 PM - 11:00 PM ET"
echo ""
echo "================================================================"
echo "🚀 READY TO TRADE"
echo "================================================================"
echo ""
echo "To start the bot NOW:"
echo "   nohup python3 -u bot_v3.py > trading.log 2>&1 &"
echo ""
echo "To monitor:"
echo "   tail -f trading.log"
echo ""
echo "To schedule for peak hours (6 PM tonight):"
echo "   echo \"python3 -u $PWD/bot_v3.py > $PWD/trading.log 2>&1 &\" | at 18:00"
echo ""

# Clean up
rm -f scan_results.txt

echo "✅ Preparation complete!"
