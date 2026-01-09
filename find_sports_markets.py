#!/usr/bin/env python3
"""
Find liquid NBA and NFL markets on Kalshi
"""
import requests
from datetime import datetime

api_base = "https://api.elections.kalshi.com/trade-api/v2"

def get_sports_markets():
    """Get NBA and NFL markets"""
    url = f"{api_base}/markets"
    response = requests.get(url, params={"limit": 1000}, timeout=15)
    
    if response.status_code != 200:
        return []
    
    data = response.json()
    all_markets = data.get("markets", [])
    
    # Filter for active NBA/NFL markets
    sports_markets = []
    for m in all_markets:
        if m.get("status") != "active":
            continue
        
        ticker = m.get("ticker", "")
        title = m.get("title", "").lower()
        
        # Check if it's NBA or NFL
        is_nba = "nba" in ticker.lower() or any(team in title for team in ["lakers", "celtics", "warriors", "heat", "mavericks", "cavaliers"])
        is_nfl = "nfl" in ticker.lower() or any(team in title for team in ["chiefs", "bills", "eagles", "ravens", "cowboys", "packers"])
        
        if is_nba or is_nfl:
            sports_markets.append(m)
    
    return sports_markets

def main():
    print("🏀🏈 Fetching NBA and NFL markets from Kalshi...\n")
    
    markets = get_sports_markets()
    
    if not markets:
        print("❌ No NBA/NFL markets found")
        return
    
    print(f"✅ Found {len(markets)} active NBA/NFL markets\n")
    
    # Separate by category
    nba_markets = []
    nfl_markets = []
    
    for m in markets:
        ticker = m.get("ticker", "").lower()
        if "nba" in ticker:
            nba_markets.append(m)
        elif "nfl" in ticker:
            nfl_markets.append(m)
        else:
            # Guess based on title
            title = m.get("title", "").lower()
            if any(x in title for x in ["lakers", "celtics", "warriors", "heat", "points"]):
                nba_markets.append(m)
            else:
                nfl_markets.append(m)
    
    print(f"{'='*120}")
    print(f"🏀 NBA MARKETS ({len(nba_markets)} found)")
    print(f"{'='*120}\n")
    
    # Sort by volume + open interest
    nba_markets.sort(key=lambda x: x.get("volume", 0) + x.get("open_interest", 0), reverse=True)
    
    for i, m in enumerate(nba_markets[:30], 1):
        ticker = m.get("ticker", "N/A")
        title = m.get("title", "N/A")
        volume = m.get("volume", 0)
        oi = m.get("open_interest", 0)
        
        yes_bid = m.get("yes_bid", 0) / 100
        yes_ask = m.get("yes_ask", 0) / 100
        
        close_time = m.get("close_time", "")
        if close_time:
            try:
                dt = datetime.fromisoformat(close_time.replace('Z', '+00:00'))
                close_str = dt.strftime("%m/%d %H:%M")
            except:
                close_str = close_time[:16]
        else:
            close_str = "N/A"
        
        print(f"{i:2}. {title[:85]}")
        print(f"    Ticker: {ticker}")
        print(f"    💰 Bid/Ask: ${yes_bid:.2f}/${yes_ask:.2f} | 📊 Volume: {volume:,} | OI: {oi:,} | ⏰ {close_str}")
        print()
    
    print(f"\n{'='*120}")
    print(f"🏈 NFL MARKETS ({len(nfl_markets)} found)")
    print(f"{'='*120}\n")
    
    # Sort by volume + open interest
    nfl_markets.sort(key=lambda x: x.get("volume", 0) + x.get("open_interest", 0), reverse=True)
    
    for i, m in enumerate(nfl_markets[:30], 1):
        ticker = m.get("ticker", "N/A")
        title = m.get("title", "N/A")
        volume = m.get("volume", 0)
        oi = m.get("open_interest", 0)
        
        yes_bid = m.get("yes_bid", 0) / 100
        yes_ask = m.get("yes_ask", 0) / 100
        
        close_time = m.get("close_time", "")
        if close_time:
            try:
                dt = datetime.fromisoformat(close_time.replace('Z', '+00:00'))
                close_str = dt.strftime("%m/%d %H:%M")
            except:
                close_str = close_time[:16]
        else:
            close_str = "N/A"
        
        print(f"{i:2}. {title[:85]}")
        print(f"    Ticker: {ticker}")
        print(f"    💰 Bid/Ask: ${yes_bid:.2f}/${yes_ask:.2f} | 📊 Volume: {volume:,} | OI: {oi:,} | ⏰ {close_str}")
        print()
    
    # Save to file
    output_file = "sports_markets.txt"
    with open(output_file, "w") as f:
        f.write("KALSHI NBA & NFL MARKETS\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write(f"NBA MARKETS ({len(nba_markets)})\n")
        f.write("="*80 + "\n\n")
        for m in nba_markets[:50]:
            f.write(f"{m['ticker']}\n")
            f.write(f"{m['title']}\n")
            f.write(f"Volume: {m.get('volume', 0):,} | OI: {m.get('open_interest', 0):,}\n\n")
        
        f.write(f"\n\nNFL MARKETS ({len(nfl_markets)})\n")
        f.write("="*80 + "\n\n")
        for m in nfl_markets[:50]:
            f.write(f"{m['ticker']}\n")
            f.write(f"{m['title']}\n")
            f.write(f"Volume: {m.get('volume', 0):,} | OI: {m.get('open_interest', 0):,}\n\n")
    
    print(f"\n📝 Results saved to: {output_file}")
    
    print(f"\n{'='*120}")
    print(f"💡 KEY FINDINGS:")
    print(f"   • Total NBA markets: {len(nba_markets)}")
    print(f"   • Total NFL markets: {len(nfl_markets)}")
    print(f"   • Most markets have $0 bids (likely auto-resolved at close)")
    print(f"   • Focus on markets with high volume/OI for best liquidity")
    print(f"{'='*120}\n")

if __name__ == "__main__":
    main()
