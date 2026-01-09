#!/usr/bin/env python3
"""
Quick script to get Kalshi market statistics
"""
import requests
from collections import Counter

def get_all_markets():
    """Fetch all markets from Kalshi API"""
    api_base = "https://api.elections.kalshi.com/trade-api/v2"
    url = f"{api_base}/markets"
    
    all_markets = []
    cursor = None
    
    while True:
        params = {"limit": 1000}
        if cursor:
            params["cursor"] = cursor
            
        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            break
            
        data = response.json()
        markets = data.get("markets", [])
        all_markets.extend(markets)
        
        cursor = data.get("cursor")
        if not cursor:
            break
    
    return all_markets

def analyze_markets(markets):
    """Analyze and display market statistics"""
    total = len(markets)
    
    # Count by series (category)
    series_counts = Counter()
    status_counts = Counter()
    
    for market in markets:
        series = market.get("series_ticker", "Unknown")
        status = market.get("status", "Unknown")
        series_counts[series] += 1
        status_counts[status] += 1
    
    # Print statistics
    print(f"\n{'='*60}")
    print(f"KALSHI MARKET STATISTICS")
    print(f"{'='*60}\n")
    
    print(f"📊 TOTAL MARKETS: {total:,}")
    print(f"\n{'='*60}")
    
    print(f"\n📈 BY STATUS:")
    print(f"{'-'*60}")
    for status, count in status_counts.most_common():
        pct = (count / total) * 100
        print(f"  {status:20s}: {count:6,} ({pct:5.1f}%)")
    
    print(f"\n{'='*60}")
    print(f"\n🎯 TOP 20 SERIES (Categories):")
    print(f"{'-'*60}")
    for series, count in series_counts.most_common(20):
        pct = (count / total) * 100
        print(f"  {series:30s}: {count:5,} ({pct:5.1f}%)")
    
    print(f"\n{'='*60}")
    print(f"\n📋 SUMMARY:")
    print(f"{'-'*60}")
    print(f"  Total Series: {len(series_counts)}")
    print(f"  Active Markets: {status_counts.get('active', 0):,}")
    print(f"  Closed Markets: {status_counts.get('closed', 0):,}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    print("Fetching markets from Kalshi API...")
    markets = get_all_markets()
    analyze_markets(markets)
