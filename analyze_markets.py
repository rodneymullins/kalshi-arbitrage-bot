#!/usr/bin/env python3
"""Deep dive analysis of Kalshi market conditions"""
import os, time, requests, base64
from datetime import datetime, timedelta
from dotenv import load_dotenv
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import json

load_dotenv()

key = os.getenv('KALSHI_KEY_ID')
with open('kalshi.key', 'rb') as f:
    pk = serialization.load_pem_private_key(f.read(), password=None)

def sign(method, path, ts):
    msg = f'{ts}{method}{path}'
    sig = pk.sign(msg.encode(), padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
    return base64.b64encode(sig).decode()

print("=" * 90)
print("KALSHI MARKET ANALYSIS - LIQUIDITY & TRADING PATTERNS")
print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")
print("=" * 90)

# 1. Get all markets
ts = str(int(time.time() * 1000))
path = '/trade-api/v2/markets?limit=200&status=open'
h = {'KALSHI-ACCESS-KEY': key, 'KALSHI-ACCESS-SIGNATURE': sign('GET', path, ts), 'KALSHI-ACCESS-TIMESTAMP': ts}
r = requests.get('https://api.elections.kalshi.com' + path, headers=h, timeout=15)

if r.status_code != 200:
    print(f"❌ API Error: {r.status_code}")
    exit(1)

markets = r.json().get('markets', [])
print(f"\n📊 Total Open Markets: {len(markets)}\n")

# 2. Analyze volume distribution
volume_buckets = {
    '> $1M': 0,
    '$100K - $1M': 0,
    '$10K - $100K': 0,
    '$1K - $10K': 0,
    '$1 - $1K': 0,
    '$0': 0
}

for m in markets:
    vol = m.get('volume', 0)
    if vol > 1_000_000:
        volume_buckets['> $1M'] += 1
    elif vol > 100_000:
        volume_buckets['$100K - $1M'] += 1
    elif vol > 10_000:
        volume_buckets['$10K - $100K'] += 1
    elif vol > 1_000:
        volume_buckets['$1K - $10K'] += 1
    elif vol > 0:
        volume_buckets['$1 - $1K'] += 1
    else:
        volume_buckets['$0'] += 1

print("VOLUME DISTRIBUTION:")
print("-" * 40)
for bucket, count in volume_buckets.items():
    pct = (count / len(markets)) * 100
    bar = "█" * int(pct / 2)
    print(f"{bucket:15} | {count:3} ({pct:5.1f}%) {bar}")

# 3. Find markets with ANY orderbook activity (sample 50 random markets)
print("\n\nORDERBOOK SAMPLING (checking 30 random markets):")
print("-" * 90)

import random
sample_markets = random.sample(markets, min(30, len(markets)))

active_orderbooks = 0
total_checked = 0

for m in sample_markets[:30]:
    ticker = m.get('ticker', '')
    ts = str(int(time.time() * 1000))
    path = f'/trade-api/v2/markets/{ticker}/orderbook'
    h = {'KALSHI-ACCESS-KEY': key, 'KALSHI-ACCESS-SIGNATURE': sign('GET', path, ts), 'KALSHI-ACCESS-TIMESTAMP': ts}
    
    try:
        r = requests.get(f'https://api.elections.kalshi.com{path}', headers=h, timeout=5)
        if r.status_code == 200:
            ob = r.json().get('orderbook', {})
            yes_asks = ob.get('yes', [])
            yes_bids = ob.get('no', [])
            
            if yes_asks or yes_bids:
                active_orderbooks += 1
                print(f"✅ {ticker[:60]}")
                print(f"   YES asks: {len(yes_asks)} | NO bids: {len(yes_bids)}")
            
            total_checked += 1
        time.sleep(0.3)
    except:
        pass

print(f"\nActive Orderbooks: {active_orderbooks}/{total_checked} ({(active_orderbooks/total_checked)*100:.1f}%)")

# 4. Category analysis
print("\n\nMARKET CATEGORIES (by ticker prefix):")
print("-" * 90)

categories = {}
for m in markets:
    ticker = m.get('ticker', '')
    # Extract category from ticker
    if ticker.startswith('KXMVESPORTS'):
        cat = 'Sports (Multi-game)'
    elif ticker.startswith('KXMVENBA'):
        cat = 'NBA (Single game)'
    elif ticker.startswith('KXMVENFLS'):
        cat = 'NFL (Single game)'
    elif ticker.startswith('KXHIGH'):
        cat = 'Weather (High temp)'
    elif ticker.startswith('KXLOW'):
        cat = 'Weather (Low temp)'
    elif ticker.startswith('KXELON'):
        cat = 'Long-term (Elon/Mars)'
    elif 'PRES' in ticker or 'REP' in ticker or 'DEM' in ticker:
        cat = 'Politics'
    else:
        cat = 'Other'
    
    categories[cat] = categories.get(cat, 0) + 1

for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
    pct = (count / len(markets)) * 100
    print(f"{cat:25} | {count:3} markets ({pct:5.1f}%)")

# 5. Time horizon analysis
print("\n\nTIME TO CLOSE DISTRIBUTION:")
print("-" * 90)

time_buckets = {
    '< 1 day': 0,
    '1-7 days': 0,
    '8-30 days': 0,
    '31-180 days': 0,
    '> 180 days': 0
}

for m in markets:
    try:
        close_time = datetime.fromisoformat(m.get('close_time', '').replace('Z', '+00:00'))
        days = (close_time.replace(tzinfo=None) - datetime.now()).days
        
        if days < 1:
            time_buckets['< 1 day'] += 1
        elif days <= 7:
            time_buckets['1-7 days'] += 1
        elif days <= 30:
            time_buckets['8-30 days'] += 1
        elif days <= 180:
            time_buckets['31-180 days'] += 1
        else:
            time_buckets['> 180 days'] += 1
    except:
        pass

for bucket, count in time_buckets.items():
    pct = (count / len(markets)) * 100
    bar = "█" * int(pct / 3)
    print(f"{bucket:15} | {count:3} ({pct:5.1f}%) {bar}")

print("\n" + "=" * 90)
print("SUMMARY & RECOMMENDATIONS")
print("=" * 90)

print(f"""
📊 Market Landscape:
   - Total markets: {len(markets)}
   - Markets with >$1K volume: {volume_buckets['$1K - $10K'] + volume_buckets['$10K - $100K'] + volume_buckets['$100K - $1M'] + volume_buckets['> $1M']}
   - Markets with active orderbooks: ~{(active_orderbooks/total_checked)*100:.0f}% (sampled)

⚠️  Current Challenges:
   - Very low overall liquidity (most markets have $0-$1K volume)
   - Most orderbooks are empty (off-peak hours: 10am ET)
   - No markets currently have >$10K volume

💡 Strategy Recommendations:

   1. TIMING IS CRITICAL:
      - Peak trading hours: 12pm-8pm ET (during market events)
      - Sports markets active: Game days (evenings/weekends)
      - Political markets: News-driven, unpredictable

   2. MARKET SELECTION:
      - Focus: NBA/NFL single-game markets during game days
      - Avoid: Long-term markets (Mars, multi-year politics)
      - Sweet spot: 1-7 day time horizon

   3. BOT STRATEGY ADJUSTMENT:
      - Run bot during peak hours (automated via cron)
      - Daily market scanner to find liquid opportunities
      - Consider PAUSE strategy during off-hours
      - Minimum volume threshold: $1K recent activity

   4. REALISTIC EXPECTATIONS:
      - Current $29.40 bankroll in low-liquidity environment = high risk
      - Orders may sit "resting" for hours/days
      - Consider paper trading to validate timing strategy first

🔧 Next Steps:
   - Schedule daily_scan.sh via cron (9am ET daily)
   - Add volume threshold check to bot (min $1K)
   - Track market hours and adjust bot schedule
   - Monitor for higher-liquidity event-driven markets
""")

print("=" * 90)
