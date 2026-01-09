#!/usr/bin/env python3
"""Kalshi Market Scanner - FAST VERSION - Find liquid, near-term markets"""
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
    
    def score_market_fast(self, market):
        """Score market based on volume and time to close ONLY (skip orderbook fetch for speed)"""
        score = 0
        
        # Volume (0-50 points)
        volume = market.get("volume", 0)
        if volume > 1000000:  # $1M+
            score += 50
        elif volume > 100000:  # $100K+
            score += 30
        elif volume > 10000:   # $10K+
            score += 10
        elif volume > 1000:    # $1K+
            score += 5
        
        # Time to close (0-30 points) - prefer 1-7 days
        try:
            close_time = datetime.fromisoformat(market.get("close_time", "").replace("Z", "+00:00"))
            days_until_close = (close_time - datetime.now(close_time.tzinfo)).days
            
            if 1 <= days_until_close <= 7:
                score += 30
            elif 8 <= days_until_close <= 30:
                score += 15
            elif days_until_close < 1:
                score += 5  # Too soon
        except:
            pass
        
        return score
    
    def check_liquidity(self, ticker):
        """Check if market has active orderbook (0-20 points)"""
        orderbook = self.get_orderbook(ticker)
        if orderbook:
            yes_asks = orderbook.get("yes", [])
            if yes_asks and len(yes_asks) > 2:  # Multiple orders = liquid
                return 20
            elif yes_asks:
                return 10
        return 0
    
    def scan(self, top_n=10):
        """Scan and rank markets - FAST VERSION"""
        print("🔍 Scanning Kalshi markets...")
        markets = self.get_markets(limit=200)
        
        if not markets:
            print("❌ No markets found")
            return []
        
        print(f"📊 Found {len(markets)} open markets")
        
        # FAST PASS: Score based on volume & time only (no API calls)
        print("⚡ Phase 1: Fast scoring (volume + time)...")
        fast_scored = []
        for m in markets:
            score = self.score_market_fast(m)
            if score > 0:  # Only keep markets with some score
                fast_scored.append({
                    "ticker": m.get("ticker"),
                    "title": m.get("title"),
                    "volume": m.get("volume", 0),
                    "close_time": m.get("close_time"),
                    "score": score
                })
        
        # Sort and take top 20 candidates
        fast_scored.sort(key=lambda x: x["score"], reverse=True)
        candidates = fast_scored[:20]
        
        print(f"🎯 Phase 2: Checking orderbooks for top {len(candidates)} candidates...")
        # SLOW PASS: Check orderbooks for top candidates only
        final_scored = []
        for i, m in enumerate(candidates, 1):
            liquidity_score = self.check_liquidity(m["ticker"])
            final_score = m["score"] + liquidity_score
            final_scored.append({
                "ticker": m["ticker"],
                "title": m["title"],
                "volume": m["volume"],
                "close_time": m["close_time"],
                "score": final_score,
                "has_orderbook": liquidity_score > 0
            })
            print(f"  [{i}/{len(candidates)}] {m['ticker'][:40]}... Score: {final_score}/100")
            time.sleep(0.2)  # Rate limit
        
        final_scored.sort(key=lambda x: x["score"], reverse=True)
        return final_scored[:top_n]

if __name__ == "__main__":
    scanner = KalshiScanner()
    top_markets = scanner.scan(top_n=15)
    
    print("\n" + "="*80)
    print("🎯 TOP KALSHI MARKETS FOR TRADING")
    print("="*80)
    
    for i, m in enumerate(top_markets, 1):
        try:
            close_time = datetime.fromisoformat(m["close_time"].replace("Z", "+00:00"))
            days_left = (close_time - datetime.now(close_time.tzinfo)).days
        except:
            days_left = "?"
        
        orderbook_status = "✅ Active" if m.get("has_orderbook") else "⚠️  Empty"
        
        print(f"\n{i}. {m['title'][:75]}")
        print(f"   Ticker: {m['ticker']}")
        print(f"   Volume: ${m['volume']:,.0f}")
        print(f"   Closes: {close_time.strftime('%Y-%m-%d') if days_left != '?' else 'Unknown'} ({days_left}d)")
        print(f"   Orderbook: {orderbook_status}")
        print(f"   Score: {m['score']}/100")
    
    print("\n" + "="*80)
    if top_markets:
        best = top_markets[0]
        print(f"\n💡 Best market: {best['ticker']}")
        print(f"   Score: {best['score']}/100")
        if best.get('has_orderbook'):
            print(f"   ✅ HAS ACTIVE ORDERBOOK - Ready to trade!")
        else:
            print(f"   ⚠️  Empty orderbook - May be off-hours or illiquid")
        print(f"\n   Update bot with:")
        print(f'   ticker = "{best["ticker"]}"')
