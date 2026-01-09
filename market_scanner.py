#!/usr/bin/env python3
"""Kalshi Market Scanner - Find liquid, near-term markets"""
import os, time, requests, json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import base64

load_dotenv()

class KalshiScanner:
    def __init__(self):
        self.base = "https://api.elections.kalshi.com/trade-api/v2"
        self.key = os.getenv("KALSHI_KEY_ID")
        try:
            with open("kalshi.key", "rb") as f:
                self.pk = serialization.load_pem_private_key(f.read(), password=None)
        except Exception as e:
            print(f"❌ Key error: {e}")
            self.pk = None
    
    def sign(self, method, path, ts):
        if not self.pk: return "NONE"
        msg = f"{ts}{method}{path}"
        sig = self.pk.sign(msg.encode(), padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
        return base64.b64encode(sig).decode()
    
    def get_markets(self, limit=100, status="open"):
        """Fetch all open markets"""
        ts = str(int(time.time() * 1000))
        path = f"/trade-api/v2/markets?limit={limit}&status={status}"
        headers = {
            "KALSHI-ACCESS-KEY": self.key,
            "KALSHI-ACCESS-SIGNATURE": self.sign("GET", path, ts),
            "KALSHI-ACCESS-TIMESTAMP": ts
        }
        
        try:
            r = requests.get(f"{self.base}/markets?limit={limit}&status={status}", headers=headers, timeout=10)
            if r.status_code == 200:
                return r.json().get("markets", [])
        except Exception as e:
            print(f"❌ Error: {e}")
        return []
    
    def get_orderbook(self, ticker):
        """Get orderbook for volume/liquidity data"""
        ts = str(int(time.time() * 1000))
        path = f"/trade-api/v2/markets/{ticker}/orderbook"
        headers = {
            "KALSHI-ACCESS-KEY": self.key,
            "KALSHI-ACCESS-SIGNATURE": self.sign("GET", path, ts),
            "KALSHI-ACCESS-TIMESTAMP": ts
        }
        
        try:
            r = requests.get(f"{self.base}/markets/{ticker}/orderbook", headers=headers, timeout=8)
            if r.status_code == 200:
                return r.json().get("orderbook", {})
        except:
            pass
        return {}
    
    def score_market(self, market):
        """Score market based on volume, time to close, and liquidity"""
        score = 0
        
        # Volume (0-50 points)
        volume = market.get("volume", 0)
        if volume > 1000000:  # $1M+
            score += 50
        elif volume > 100000:  # $100K+
            score += 30
        elif volume > 10000:   # $10K+
            score += 10
        
        # Time to close (0-30 points) - prefer 1-7 days
        close_time = datetime.fromisoformat(market.get("close_time", "").replace("Z", "+00:00"))
        days_until_close = (close_time - datetime.now(close_time.tzinfo)).days
        
        if 1 <= days_until_close <= 7:
            score += 30
        elif 8 <= days_until_close <= 30:
            score += 15
        elif days_until_close < 1:
            score += 5  # Too soon
        
        # Check ask/bid spread for liquidity (0-20 points)
        orderbook = self.get_orderbook(market.get("ticker", ""))
        if orderbook:
            yes_bids = orderbook.get("yes", [])
            if yes_bids and len(yes_bids) > 2:  # Multiple orders = liquid
                score += 20
            elif yes_bids:
                score += 10
        
        return score
    
    def scan(self, top_n=10):
        """Scan and rank markets"""
        print("🔍 Scanning Kalshi markets...")
        markets = self.get_markets(limit=200)
        
        if not markets:
            print("❌ No markets found")
            return []
        
        print(f"📊 Found {len(markets)} open markets")
        
        # Score and sort
        scored = []
        for m in markets:
            score = self.score_market(m)
            scored.append({
                "ticker": m.get("ticker"),
                "title": m.get("title"),
                "volume": m.get("volume", 0),
                "close_time": m.get("close_time"),
                "score": score
            })
            time.sleep(0.1)  # Rate limit
        
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_n]

if __name__ == "__main__":
    scanner = KalshiScanner()
    top_markets = scanner.scan(top_n=15)
    
    print("\n" + "="*80)
    print("🎯 TOP KALSHI MARKETS FOR TRADING")
    print("="*80)
    
    for i, m in enumerate(top_markets, 1):
        close_time = datetime.fromisoformat(m["close_time"].replace("Z", "+00:00"))
        days_left = (close_time - datetime.now(close_time.tzinfo)).days
        
        print(f"\n{i}. {m['title']}")
        print(f"   Ticker: {m['ticker']}")
        print(f"   Volume: ${m['volume']:,.0f}")
        print(f"   Closes: {close_time.strftime('%Y-%m-%d')} ({days_left}d)")
        print(f"   Score: {m['score']}/100")
    
    print("\n" + "="*80)
    if top_markets:
        print(f"\n💡 Best market: {top_markets[0]['ticker']}")
        print(f"   Update bot with: ticker = \"{top_markets[0]['ticker']}\"")
