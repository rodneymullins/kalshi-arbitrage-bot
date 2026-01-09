#!/usr/bin/env python3
"""Quick script to count Kalshi markets"""
import requests

api_base = "https://api.elections.kalshi.com/trade-api/v2"
url = f"{api_base}/markets"

print("Fetching first page of markets...")
response = requests.get(url, params={"limit": 1000}, timeout=10)

if response.status_code == 200:
    data = response.json()
    markets = data.get("markets", [])
    cursor = data.get("cursor")
    
    print(f"\n✅ First batch: {len(markets)} markets")
    print(f"   Cursor present: {'Yes - more markets available' if cursor else 'No - this is all'}")
    
    # Show some stats from first batch
    active = sum(1 for m in markets if m.get("status") == "active")
    closed = sum(1 for m in markets if m.get("status") == "closed")
    
    print(f"\n📊 From this sample:")
    print(f"   Active: {active}")
    print(f"   Closed: {closed}")
    
    # Get a rough total estimate
    if cursor:
        print(f"\n💡 Note: Kalshi has MORE than {len(markets)} markets total.")
        print(f"   (Multiple pages available)")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text[:500])
