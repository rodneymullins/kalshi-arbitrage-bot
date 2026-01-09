#!/usr/bin/env python3
"""
Fetch markets with ACTUAL trading liquidity
Query orderbooks to find markets with real bids/offers
"""
import requests
import time
from collections import defaultdict

api_base = "https://api.elections.kalshi.com/trade-api/v2"

def get_active_markets():
    """Get list of active market tickers"""
    url = f"{api_base}/markets"
    response = requests.get(url, params={"limit": 1000}, timeout=15)
    
    if response.status_code != 200:
        return []
    
    data = response.json()
    all_markets = data.get("markets", [])
    active = [m for m in all_markets if m.get("status") == "active"]
    return active

def get_orderbook(ticker):
    """Get orderbook for a specific market"""
    url = f"{api_base}/markets/{ticker}/orderbook"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def has_real_liquidity(orderbook_data):
    """Check if orderbook has real liquidity"""
    if not orderbook_data:
        return False, {}
    
    orderbook = orderbook_data.get("orderbook", {})
    
    # Check yes side
    yes_bids = orderbook.get("yes", [])
    
    # Filter for actual bids (price > 0)
    real_yes_bids = [bid for bid in yes_bids if bid and bid[0] > 0]
    
    if not real_yes_bids:
        return False, {}
    
    # Get best bid/ask
    best_bid = max(real_yes_bids, key=lambda x: x[0]) if real_yes_bids else [0, 0]
    
    # Calculate total liquidity
    total_bid_size = sum(bid[1] for bid in real_yes_bids)
    
    return True, {
        "best_bid": best_bid[0] / 100,
        "best_bid_size": best_bid[1],
        "total_bids": len(real_yes_bids),
        "total_bid_volume": total_bid_size
    }

def main():
    print("🔍 Fetching active markets from Kalshi...")
    markets = get_active_markets()
    
    print(f"✅ Found {len(markets)} active markets")
    print(f"📊 Now checking orderbooks for real liquidity (this may take a minute)...\n")
    
    liquid_markets = []
    checked = 0
    
    # Check orderbooks for a sample of markets
    # Start with markets that have volume or open interest
    candidates = sorted(markets, 
                       key=lambda m: m.get("volume", 0) + m.get("open_interest", 0),
                       reverse=True)[:200]  # Check top 200 by activity
    
    for market in candidates:
        ticker = market.get("ticker")
        checked += 1
        
        if checked % 20 == 0:
            print(f"  Checked {checked}/{len(candidates)} markets... Found {len(liquid_markets)} liquid")
        
        orderbook = get_orderbook(ticker)
        is_liquid, liquidity_info = has_real_liquidity(orderbook)
        
        if is_liquid:
            market_info = {
                "ticker": ticker,
                "title": market.get("title", ""),
                "series": market.get("series_ticker", "Unknown"),
                "volume": market.get("volume", 0),
                "open_interest": market.get("open_interest", 0),
                "close_time": market.get("close_time", ""),
                **liquidity_info
            }
            liquid_markets.append(market_info)
        
        time.sleep(0.05)  # Rate limiting
    
    print(f"\n{'='*120}")
    print(f"✅ Found {len(liquid_markets)} markets with REAL liquidity (actual bids in orderbook)")
    print(f"{'='*120}\n")
    
    if not liquid_markets:
        print("❌ No markets with real orderbook liquidity found.")
        print("💡 This might mean:")
        print("   • Markets are open but no one is placing limit orders")
        print("   • Most trading happens at market close via automated pricing")
        print("   • Kalshi's orderbook might be different from traditional exchanges")
        return
    
    # Sort by liquidity
    liquid_markets.sort(key=lambda x: x["total_bid_volume"], reverse=True)
    
    # Display results
    print(f"🏆 TOP LIQUID MARKETS (Sorted by bid volume):\n")
    
    for i, m in enumerate(liquid_markets[:50], 1):
        print(f"{i:2}. [{m['ticker']}]")
        print(f"    {m['title'][:90]}")
        print(f"    📂 Series: {m['series']}")
        print(f"    💰 Best Bid: ${m['best_bid']:.3f} (size: {m['best_bid_size']})")
        print(f"    📊 Total Bids: {m['total_bids']} | Total Bid Volume: {m['total_bid_volume']:,}")
        print(f"    📈 Market Volume: {m['volume']:,} | Open Interest: {m['open_interest']:,}")
        print()
    
    # Summary by category
    print(f"{'='*120}")
    print("📈 CATEGORY BREAKDOWN")
    print(f"{'='*120}\n")
    
    series_counts = defaultdict(int)
    for m in liquid_markets:
        series_counts[m['series']] += 1
    
    for series, count in sorted(series_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {series:40s}: {count:3} markets")
    
    # Save results
    output_file = "truly_liquid_markets.txt"
    with open(output_file, "w") as f:
        f.write(f"KALSHI MARKETS WITH REAL ORDERBOOK LIQUIDITY\\n")
        f.write(f"Checked: {checked} markets\\n")
        f.write(f"Found: {len(liquid_markets)} with real bids\\n\\n")
        
        for i, m in enumerate(liquid_markets, 1):
            f.write(f"{i}. {m['ticker']}\\n")
            f.write(f"   {m['title']}\\n")
            f.write(f"   Best Bid: ${m['best_bid']:.3f} (size: {m['best_bid_size']})\\n")
            f.write(f"   Total Bids: {m['total_bids']} | Bid Volume: {m['total_bid_volume']:,}\\n")
            f.write(f"   Volume: {m['volume']:,} | OI: {m['open_interest']:,}\\n\\n")
    
    print(f"\\n📝 Results saved to: {output_file}")

if __name__ == "__main__":
    main()
