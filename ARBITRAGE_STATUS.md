# Probability Arbitrage Quick Reference

## What is Probability Arbitrage?

When YES + NO prices ≠ 100%, you can buy both sides and lock in guaranteed profit regardless of outcome.

**Example:**
- YES @ 52¢ + NO @ 50¢ = 102¢ (should be 100¢)
- Buy both for $102
- Guaranteed payout: $100
- **Problem:** Fees are $14 (7% on each side)
- **Net: -$16 loss** ❌

## Why No Opportunities Right Now?

1. **Markets are efficient** during trading hours
2. **Fees are too high** (10.5% total) - eat most arbitrage profits
3. **Need larger positions** to overcome fee burden

## Current Status

**Ran scan at 12:19 PM ET:**
- Checked 200 markets
- Found: **0 profitable opportunities**
- Reason: All deviations too small to overcome fees

## How to Monitor

**Option 1: Continuous Monitor (Recommended)**
```bash
cd /Users/rod/Antigravity/kalshi_bot
python3 monitor_arbitrage.py
```
- Scans every 30 seconds
- Alerts when opportunities found
- Press Ctrl+C to stop

**Option 2: One-Time Scan**
```bash
python3 strategies/probability_arb.py
```

**Option 3: Very Aggressive (Lower Quality)**
```bash
# Edit strategies/probability_arb.py, line 244:
# Change min_deviation_pct=0.5 to min_deviation_pct=0.1
```

## Fee Reality Check

With **7% taker fees**, you need:
- **Minimum 2-3% deviation** for small profit
- **Minimum 100+ contracts** to make fees worthwhile
- **But:** Your bankroll limits you to ~20-30 contracts max

**Bottom Line:** Probability arbitrage is **very difficult** to profit from with:
- Small bankroll ($29.40)
- High fee tier (7%)
- Small position sizes

## Better Strategies for Your Situation

1. **Wait for larger bankroll** ($100+)
   - Better position sizing
   - Fees become manageable

2. **Use traditional edge betting** with 5-10% targets
   - Update .env: `TARGET_RETURN_PCT=5`
   - Run: `python3 bot_v3.py`

3. **Paper trade until volume increases**
   - Build up volume to hit $2,500 (5.5% fees)
   - Then strategies become more viable

## Recommendation

**For today:** Run the continuous monitor in background:
```bash
python3 monitor_arbitrage.py > arb_monitor.log 2>&1 &
```

This will log any opportunities. Check the log periodically:
```bash
tail -f arb_monitor.log
```

**But honestly:** With your current fee tier, you'll likely see very few (if any) profitable arbitrage opportunities.

**Better plan:**
1. Switch to 5% target return edge betting
2. Build up trading volume to reduce fees
3. Then probability arbitrage becomes viable
