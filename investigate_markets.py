#!/usr/bin/env python3
"""Investigate the current state of Kalshi markets"""
import requests
from collections import Counter

api_base = "https://api.elections.kalshi.com/trade-api/v2"
url = f"{api_base}/markets"

print("Fetching markets...")
response = requests.get(url, params={"limit": 1000}, timeout=15)

if response.status_code == 200:
    data = response.json()
    all_markets = data.get("markets", [])
    active_markets = [m for m in all_markets if m.get("status") == "active"]
    
    print(f"\nTotal active markets: {len(active_markets)}\n")
    
    # Analyze bid/ask patterns
    zero_bid = 0
    has_bid = 0
    wide_spread = 0
    tight_spread = 0
    max_ask = 0
    
    bid_histogram = Counter()
    spread_histogram = Counter()
    
    for m in active_markets:
        yes_bid = m.get("yes_bid", 0)
        yes_ask = m.get("yes_ask", 100)
        spread = yes_ask - yes_bid
        
        if yes_bid == 0:
            zero_bid += 1
        else:
            has_bid += 1
            bid_histogram[yes_bid] += 1
        
        if yes_ask >= 99:
            max_ask += 1
        
        spread_histogram[spread] += 1
        
        if spread > 20:
            wide_spread += 1
        elif spread <= 5:
            tight_spread += 1
    
    print("BID ANALYSIS:")
    print(f"  Markets with $0.00 bid: {zero_bid} ({zero_bid/len(active_markets)*100:.1f}%)")
    print(f"  Markets with real bid:  {has_bid} ({has_bid/len(active_markets)*100:.1f}%)")
    print(f"  Markets with $1.00 ask: {max_ask} ({max_ask/len(active_markets)*100:.1f}%)")
    
    print(f"\nSPREAD ANALYSIS:")
    print(f"  Tight spreads (≤5¢):  {tight_spread}")
    print(f"  Wide spreads (>20¢):  {wide_spread}")
    
    print(f"\nMost common spreads (cents):")
    for spread, count in spread_histogram.most_common(10):
        print(f"  {spread}¢: {count} markets")
    
    if has_bid > 0:
        print(f"\n✅ Found {has_bid} markets with real bids!")
        print(f"\nLet's look at some examples with bids > 0:")
        
        count = 0
        for m in active_markets:
            yes_bid = m.get("yes_bid", 0)
            if yes_bid > 0:
                yes_ask = m.get("yes_ask", 100)
                spread = yes_ask - yes_bid
                volume = m.get("volume", 0)
                oi = m.get("open_interest", 0)
                
                print(f"\n  {m.get('ticker', 'N/A')}")
                print(f"  {m.get('title', 'N/A')[:80]}")
                print(f"  Bid/Ask: {yes_bid/100:.3f}/{yes_ask/100:.3f} | Spread: {spread}¢ | Vol: {volume} | OI: {oi}")
                
                count += 1
                if count >= 10:
                    break
else:
    print(f"Error: {response.status_code}")
