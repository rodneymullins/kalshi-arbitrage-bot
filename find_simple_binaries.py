#!/usr/bin/env python3
"""
Find simple BINARY markets on Kalshi
Look for markets with clean yes/no structure
"""
import requests
from datetime import datetime
from collections import defaultdict

api_base = "https://api.elections.kalshi.com/trade-api/v2"

def main():
    print("🔍 Analyzing Kalshi market structure...\n")
    
    response = requests.get(f"{api_base}/markets", params={"limit": 1000}, timeout=15)
    
    if response.status_code != 200:
        print(f"❌ API Error: {response.status_code}")
        return
    
    data = response.json()
    all_markets = data.get("markets", [])
    active_markets = [m for m in all_markets if m.get("status") == "active"]
    
    print(f"Total active markets: {len(active_markets)}\n")
    
    # Analyze ticker patterns
    ticker_patterns = defaultdict(list)
    series_counts = defaultdict(int)
    
    for m in active_markets:
        ticker = m.get("ticker", "")
        series = m.get("series_ticker", "Unknown")
        
        series_counts[series] += 1
        
        # Group by ticker prefix pattern
        if "-" in ticker:
            prefix = ticker.split("-")[0]
            ticker_patterns[prefix].append(m)
    
    print(f"{'='*120}")
    print("MARKET SERIES ANALYSIS")
    print(f"{'='*120}\n")
    
    # Show top series
    print("Top 20 Series:")
    for series, count in sorted(series_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"  {series:40s}: {count:4} markets")
    
    print(f"\n{'='*120}")
    print("TICKER PREFIX PATTERNS")
    print(f"{'='*120}\n")
    
    # Show ticker patterns
    for prefix, markets in sorted(ticker_patterns.items(), key=lambda x: len(x[1]), reverse=True)[:15]:
        print(f"{prefix:30s}: {len(markets):4} markets")
        
        # Show example
        example = markets[0]
        print(f"  Example: {example.get('title', 'N/A')[:70]}")
        print()
    
    # Find non-sports markets
    print(f"\n{'='*120}")
    print("NON-SPORTS MARKETS (Likely Simple Binaries)")
    print(f"{'='*120}\n")
    
    non_sports = []
    for m in active_markets:
        ticker = m.get("ticker", "").upper()
        
        # Skip if it's clearly sports
        if any(x in ticker for x in ["NBA", "NFL", "MLB", "NHL", "SINGLEGAME", "MULTIGAME", "ESPORTS"]):
            continue
        
        non_sports.append(m)
    
    print(f"Found {len(non_sports)} non-sports markets\n")
    
    # Categorize non-sports
    categories = {
        "Politics": [],
        "Economics": [],
        "Finance/Crypto": [],
        "Weather": [],
        "Entertainment": [],
        "Other": []
    }
    
    for m in non_sports:
        ticker = m.get("ticker", "").upper()
        title = m.get("title", "").lower()
        
        if any(x in ticker or x in title for x in ["PRES", "SENATE", "CONGRESS", "ELECTION", "CABINET", "PRESIDENT", "TRUMP", "BIDEN"]):
            categories["Politics"].append(m)
        elif any(x in ticker or x in title for x in ["FED", "INFL", "GDP", "UNEMPLOYMENT", "CPI", "RATE", "RECESSION"]):
            categories["Economics"].append(m)
        elif any(x in ticker or x in title for x in ["BTC", "ETH", "CRYPTO", "STOCK", "SPX", "NASDAQ", "DOW", "BITCOIN"]):
            categories["Finance/Crypto"].append(m)
        elif any(x in ticker or x in title for x in ["TEMP", "WEATHER", "RAIN", "SNOW", "HURRICANE"]):
            categories["Weather"].append(m)
        elif any(x in ticker or x in title for x in ["OSCAR", "EMMY", "GRAMMY", "MOVIE", "BOX"]):
            categories["Entertainment"].append(m)
        else:
            categories["Other"].append(m)
    
    # Display each category
    for category, markets in categories.items():
        if not markets:
            continue
        
        print(f"\n{'='*120}")
        print(f"📊 {category.upper()} ({len(markets)} markets)")
        print(f"{'='*120}\n")
        
        # Sort by volume + OI
        markets.sort(key=lambda x: x.get("volume", 0) + x.get("open_interest", 0), reverse=True)
        
        for i, m in enumerate(markets[:15], 1):
            ticker = m.get("ticker", "N/A")
            title = m.get("title", "N/A")
            volume = m.get("volume", 0)
            oi = m.get("open_interest", 0)
            series = m.get("series_ticker", "N/A")
            
            yes_bid = m.get("yes_bid", 0) / 100
            yes_ask = m.get("yes_ask", 0) / 100
            
            print(f"{i:2}. {title[:75]}")
            print(f"    Series: {series} | Ticker: {ticker}")
            print(f"    💰 ${yes_bid:.2f}/${yes_ask:.2f} | 📊 Vol: {volume:,} | OI: {oi:,}")
            print()
    
    # Summary
    print(f"\n{'='*120}")
    print("SUMMARY - SIMPLE BINARY MARKET COUNTS")
    print(f"{'='*120}\n")
    
    for category, markets in categories.items():
        if markets:
            total_vol = sum(m.get("volume", 0) for m in markets)
            total_oi = sum(m.get("open_interest", 0) for m in markets)
            print(f"{category:20s}: {len(markets):4} markets | Total Vol: {total_vol:,} | Total OI: {total_oi:,}")
    
    print(f"\n{'='*120}\n")

if __name__ == "__main__":
    main()
