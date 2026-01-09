# Cross-Platform Arbitrage Scanner

## Quick Start

### Single Scan
```bash
cd /Users/rod/Antigravity/kalshi_bot
python3 scan_cross_platform.py
```

### Continuous Scanning (Every 15 minutes)
```bash
python3 scan_cross_platform.py --continuous
```

### Custom Settings
```bash
# Custom scan interval (30 minutes)
python3 scan_cross_platform.py --continuous --interval 1800

# Override position size
python3 scan_cross_platform.py --position-size 10

# Override min profit threshold
python3 scan_cross_platform.py --min-profit 0.05
```

## Configuration

Edit `config/cross_platform_config.py`:
```python
CROSS_PLATFORM = {
    "position_size": 5.0,           # $5 per trade
    "min_profit_threshold": 0.02,   # $0.02 minimum profit
    "scan_interval": 900,            # 15 minutes
    "alert_only": True,              # No auto-execution
}
```

## Manual Market Matching

To guarantee a market match, add to `config/market_matches.json`:
```json
{
  "KALSHI-TICKER-HERE": "polymarket-condition-id-here"
}
```

Example:
```json
{
  "BTC-100K-2026": "0x1234567890abcdef1234567890abcdef12345678"
}
```

## How It Works

1. **Fetches Markets** from both Kalshi and Polymarket
2. **Matches Markets** using fuzzy text matching
3. **Calculates Arbitrage** for all matched pairs
4. **Applies Fees** (Kalshi tiered + Polymarket 2%)
5. **Displays Opportunities** with net profit after fees

## Example Output

```
🎯 FOUND 2 ARBITRAGE OPPORTUNITIES!

[1] ==========================================
Kalshi:      Will Bitcoin hit $100k by Jan 31?
Polymarket:  Will BTC reach $100,000 by January 31, 2026?

Strategy: Buy YES on Kalshi ($0.45), NO on Polymarket ($0.58)

Prices:
  Kalshi:      YES: $0.45, NO: $0.58
  Polymarket:  YES: $0.42, NO: $0.58

Profit Analysis (Position: $5):
  Gross Profit: $0.15
  Fees:         $0.08
  NET PROFIT:   $0.07
  ROI:          1.36%
==========================================
```

## Fee Structure

**Kalshi**:
- Tiered: 1-3.5% based on price
- Maker/taker distinction
- Uses your existing fee calculator

**Polymarket**:
- Flat 2% on profits
- ~$0.01 gas fee (Polygon)

## Troubleshooting

**No Kalshi markets found**:
- Currently Kalshi only has sports parlays active
- Wait for politics/economics markets to become available

**No opportunities found**:
- Markets are efficiently priced most of the time
- Keep scanning - opportunities appear during volatility
- Lower `min_profit_threshold` to see more marginal opportunities

**Match confidence too low**:
- Adjust `match_confidence_threshold` in config (default 0.75)
- Add manual matches to `config/market_matches.json`

## Safety Features

✅ **Alert-only mode** - No automatic trading
✅ **Fee calculation** - All profits are net of fees
✅ **Position limits** - Max $5 per trade (configurable)
✅ **Min profit threshold** - Only shows profitable opportunities
✅ **Manual matching** - Override file for guaranteed pairs

## Next Steps

1. **Run a single scan** to verify everything works
2. **Monitor opportunities** for a few days
3. **Fine-tune settings** based on results
4. **Consider manual execution** of best opportunities
5. **Apply to Kalshi Liquidity Incentive Program** to offset fees
