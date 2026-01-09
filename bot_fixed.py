#!/usr/bin/env python3
"""Kalshi Bot - FIXED Authentication"""
import os, time, requests, base64, json
from datetime import datetime
from dotenv import load_dotenv
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

load_dotenv()

LIVE = True
BANKROLL = 29.40
CHECK_SEC = 10

class Kalshi:
    def __init__(self):
        self.base = "https://api.elections.kalshi.com/trade-api/v2"
        self.key = os.getenv("KALSHI_KEY_ID")
        try:
            with open("kalshi.key", "rb") as f:
                self.pk = serialization.load_pem_private_key(f.read(), password=None)
            print(f"✅ Key loaded")
        except Exception as e:
            print(f"❌ Key error: {e}")
            self.pk = None
    
    def sign(self, method, path, ts):
        """Sign request - path must start with /trade-api/v2"""
        if not self.pk: return "NONE"
        msg = f"{ts}{method}{path}"
        sig = self.pk.sign(msg.encode(), padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
        return base64.b64encode(sig).decode()
    
    def price(self, ticker):
        if not self.key or not self.pk: return None
        ts = str(int(time.time() * 1000))
        path = f"/trade-api/v2/markets/{ticker}/orderbook"
        h = {"KALSHI-ACCESS-KEY": self.key, "KALSHI-ACCESS-SIGNATURE": self.sign("GET", path, ts), "KALSHI-ACCESS-TIMESTAMP": ts}
        try:
            r = requests.get(f"{self.base}/markets/{ticker}/orderbook", headers=h, timeout=8)
            if r.status_code == 200:
                asks = r.json().get("orderbook", {}).get("yes", [])
                return min([x[0]/100 for x in asks]) if asks else None
        except: pass
        return None
    
    def buy(self, ticker, n, cents):
        print(f"  [BUY] {n} contracts @ ${cents/100:.2f}")
        
        if not LIVE:
            print(f"  [DRY] Would place order")
            return True
        
        if not self.key or not self.pk:
            print(f"  ❌ Missing credentials")
            return False
        
        ts = str(int(time.time() * 1000))
        path = "/trade-api/v2/portfolio/orders"  # FULL PATH for signature
        data = {"ticker": ticker, "action": "buy", "side": "yes", "count": n, "type": "limit", "yes_price": cents}
        h = {
            "KALSHI-ACCESS-KEY": self.key,
            "KALSHI-ACCESS-SIGNATURE": self.sign("POST", path, ts),
            "KALSHI-ACCESS-TIMESTAMP": ts,
            "Content-Type": "application/json"
        }
        
        try:
            r = requests.post(f"{self.base}/portfolio/orders", json=data, headers=h, timeout=8)
            print(f"  [API] {r.status_code}")
            
            if r.status_code in [200, 201]:
                print(f"  ✅ SUCCESS! Order placed")
                print(f"  Order: {r.json()}")
                return True
            else:
                print(f"  ❌ Error {r.status_code}: {r.text[:300]}")
                return False
        except Exception as e:
            print(f"  ❌ Exception: {e}")
            return False

print(f"🤖 Kalshi Bot {'LIVE' if LIVE else 'DRY'} | ${BANKROLL}")
print("="*50)

k = Kalshi()
ticker = "KXMVESPORTSMULTIGAMEEXTENDED-S2025CD04A6D8FC5-931A134C1A1"  # NBA multi-game (highest volume)
losses = 0
no_price_count = 0  # Track consecutive "no price" errors

while True:
    try:
        p = k.price(ticker)
        if not p:
            no_price_count += 1
            print(f"[{datetime.now().strftime('%H:%M:%S')}] No price (#{no_price_count})")
            if no_price_count >= 30:
                print("\n⛔ HALTED: Market has no pricing for 5+ minutes. Empty orderbook.")
                print("   This usually means we're outside trading hours or the market is illiquid.")
                break
            time.sleep(CHECK_SEC)
            continue
        
        no_price_count = 0  # Reset counter when we get a price
        
        edge = 0.05
        kelly = edge / ((1/p) - 1)
        kelly = min(kelly, 0.10)
        bet = kelly * BANKROLL
        n = int(bet / p) if p > 0 else 0
        
        t = datetime.now().strftime('%H:%M:%S')
        print(f"\n[{t}] ${p:.2f} edge:{edge:.0%} kelly:${bet:.2f} n:{n}")
        
        if n > 0 and losses < 3:
            if k.buy(ticker, n, int(p * 100)):
                print(f"  💰 SUCCESS!")
                losses = 0  # Reset on success
            else:
                losses += 1
                print(f"  ⚠️  Failed ({losses}/3)")
        else:
            why = "breaker" if losses >= 3 else "small"
            print(f"  ⏸️  Skip ({why})")
        
        time.sleep(CHECK_SEC)
    except KeyboardInterrupt:
        print("\nStopped")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(CHECK_SEC)
