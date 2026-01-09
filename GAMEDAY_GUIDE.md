# Kalshi Trading Bot - Game Day Strategy Guide
**Date:** January 7, 2026  
**Tonight's Action:** 12 NBA games (7:10pm - 10:10pm ET)

---

## 🏀 TONIGHT'S NBA SCHEDULE

### Early Games (7:10 PM ET)
- **Toronto Raptors** @ Charlotte Hornets
- **Chicago Bulls** @ Detroit Pistons
- **Washington Wizards** @ Philadelphia 76ers

### Prime Time (7:40 PM ET)
- **Denver Nuggets** @ Boston Celtics
- **LA Clippers** @ New York Knicks
- **New Orleans Pelicans** @ Atlanta Hawks
- **Orlando Magic** @ Brooklyn Nets

### Western Conference (8:10 PM ET)
- **Phoenix Suns** @ Memphis Grizzlies
- **Utah Jazz** @ Oklahoma City Thunder

### Featured Game (9:30 PM ET - ESPN)
- **LA Lakers** @ San Antonio Spurs

### Late Games (10:10 PM ET)
- **Houston Rockets** @ Portland Trail Blazers
- **Milwaukee Bucks** @ Golden State Warriors

---

## 📊 MARKET REALITY CHECK

### What We Found:
- ❌ **No individual game markets** on Kalshi
- ✅ **Multi-week player prop markets** (e.g., "Player X scores 20+ in any game this week")
- ⚠️ **Low overall liquidity** ($0-$2K volume per market)
- ⏰ **Markets close in 8-30 days**, not tonight

### What This Means:
Kalshi doesn't operate like DraftKings or FanDuel with individual game markets. Instead:
- Markets are **aggregated player props** (e.g., "Steph Curry: 3+ threes in next 7 days")
- Liquidity comes from **betting on outcomes across multiple games**
- **Tonight's games contribute to active markets**, but markets don't close tonight

---

## 🎯 TRADING STRATEGY FOR TONIGHT

### Peak Trading Windows:
1. **6:00 PM - 7:30 PM ET** - Pre-game buildup, lineup news
2. **7:30 PM - 9:00 PM ET** - Early games in progress, highest activity
3. **9:00 PM - 11:00 PM ET** - West coast games, late action

### Why These Windows Matter:
- **Liquidity spikes** during live game action
- **Orderbooks fill** as recreational traders enter
- **Price discovery** happens when events occur (injuries, hot streaks)

---

## 🚀 QUICK START GUIDE

### Option 1: Run Prep Script Now (Recommended)
```bash
cd /Users/rod/Antigravity/kalshi_bot
./gameday_prep.sh
```

This will:
1. ✅ Stop any running bots
2. 🔍 Scan for best markets
3. 🎯 Update bot configuration
4. 📊 Check current orderbook status
5. 📋 Display trading plan

### Option 2: Auto-Start at 6 PM Tonight
```bash
cd /Users/rod/Antigravity/kalshi_bot

# Schedule bot to start at 6 PM
echo "cd /Users/rod/Antigravity/kalshi_bot && nohup python3 -u bot_v3.py > trading_$(date +%Y%m%d).log 2>&1 &" | at 18:00

# Verify it's scheduled
atq
```

### Option 3: Manual Start (For Testing)
```bash
cd /Users/rod/Antigravity/kalshi_bot
python3 -u bot_v3.py

# Watch output in real-time
# Ctrl+C to stop
```

### Option 4: Background Execution
```bash
cd /Users/rod/Antigravity/kalshi_bot
nohup python3 -u bot_v3.py > trading.log 2>&1 &

# Monitor
tail -f trading.log

# Stop
pkill -f bot_v3.py
```

---

## 📈 PERFORMANCE MONITORING

### Live Dashboard
```bash
# Terminal 1: Bot logs
tail -f /Users/rod/Antigravity/kalshi_bot/trading.log

# Terminal 2: Dashboard
cd /Users/rod/Antigravity/kalshi_bot
python3 -m uvicorn dashboard_api:app --host 0.0.0.0 --port 8082

# Access at: http://192.168.1.18:8082 (Aragorn)
```

### Database Queries
```bash
# Check recent trades
python3 -c "
import psycopg2
conn = psycopg2.connect(host='192.168.1.211', database='postgres', user='rod', password='')
cur = conn.cursor()
cur.execute('SELECT timestamp, market, side, size, price, status FROM kalshi_trades ORDER BY timestamp DESC LIMIT 10')
for row in cur.fetchall():
    print(row)
"
```

---

## ⚠️ REALISTIC EXPECTATIONS FOR TONIGHT

### Best Case Scenario:
- 🎯 3-5 orders placed during peak hours
- ✅ 1-2 orders **actually fill** (rest remain "resting")
- 💰 $0.50 - $2.00 profit (on $29.40 bankroll)
- 📊 Validate that 5% edge assumption holds

### Likely Case Scenario:
- 🎯 5-10 orders placed
- ⏸️ 80-90% remain "resting" (unfilled)
- 💰 Break-even to small loss (fees + unfilled capital)
- 📝 Data collection for strategy refinement

### Worst Case Scenario:
- ❌ Empty orderbooks entire evening (off-day for Kalshi)
- 🛑 Bot auto-halts after 30 "no price" errors
- 💡 Lesson learned: Need higher-volume platforms (Polymarket)

---

## 🔧 TROUBLESHOOTING

### Bot Halts Immediately
**Symptom:** "⛔ HALTED: Market volume below minimum"  
**Fix:** Lower MIN_VOLUME in bot_v3.py from $1000 to $500

### No Price Errors
**Symptom:** "[10:00:00] No price (#X)"  
**Cause:** Empty orderbook (off-peak hours)  
**Fix:** Wait until 6 PM or later

### Orders Stay "Resting"
**Symptom:** "status": "resting" in API response  
**Cause:** Normal in low-liquidity markets  
**Action:** Monitor for fills over next few hours

### Circuit Breaker Triggered
**Symptom:** "⚠️ Failed (3/3)"  
**Cause:** 3 consecutive failed order placements  
**Fix:** Check API credentials, network, or market status

---

## 📅 AUTOMATED SCHEDULE (Cron Setup)

### Daily Market Scan (9 AM)
```bash
crontab -e

# Add this line:
0 9 * * * cd /Users/rod/Antigravity/kalshi_bot && ./daily_scan.sh >> /tmp/kalshi_scan.log 2>&1
```

### Game Day Bot (6 PM on game days)
```bash
# For regular game days (Mon, Tue, Thu, Sat, Sun typically)
0 18 * * 1,2,4,6,0 cd /Users/rod/Antigravity/kalshi_bot && nohup python3 -u bot_v3.py > /tmp/kalshi_bot_$(date +\%Y\%m\%d).log 2>&1 &
```

### Auto-Stop Late Night (11:30 PM)
```bash
# Stop bot after games end
30 23 * * * pkill -f bot_v3.py
```

---

## 💡 KEY INSIGHTS FOR TONIGHT

### DO:
- ✅ Start bot between 6-7 PM ET
- ✅ Monitor orderbook fills vs "resting" ratio
- ✅ Track which markets actually have liquidity
- ✅ Test the 5% edge assumption with real data
- ✅ Keep expectations realistic (this is R&D phase)

### DON'T:
- ❌ Expect high-frequency trading (this isn't that)
- ❌ Be surprised by "resting" orders (normal)
- ❌ Increase bankroll until strategy validates
- ❌ Run bot during off-peak hours (waste of compute)
- ❌ Panic if no fills tonight (patience required)

---

## 🎓 LEARNING OBJECTIVES FOR TONIGHT:

1. **Validate liquidity timing** - Do orderbooks fill during games?
2. **Measure fill rate** - What % of orders actually execute?
3. **Test edge assumption** - Is 5% realistic or optimistic?
4. **Identify best markets** - Which player props have volume?
5. **Refine strategy** - What adjustments needed?

---

## 📞 QUICK COMMANDS REFERENCE

```bash
# Prep for tonight
./gameday_prep.sh

# Start bot
nohup python3 -u bot_v3.py > trading.log 2>&1 &

# Monitor
tail -f trading.log

# Check if running
ps aux | grep bot_v3

# Stop
pkill -f bot_v3.py

# View dashboard
open http://192.168.1.18:8082
```

---

**Good luck tonight! 🍀**  
*Remember: This is about validating the strategy, not making quick profits.*

---

**Files Created:**
- ✅ `gameday_prep.sh` - Pre-game preparation script
- ✅ `bot_v3.py` - Enhanced bot with volume checks
- ✅ `market_scanner_fast.py` - Fast market discovery
- ✅ `daily_scan.sh` - Automated daily scanning
- ✅ `analyze_markets.py` - Market analysis tool
