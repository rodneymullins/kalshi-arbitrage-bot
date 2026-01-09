#!/usr/bin/env python3
"""Kalshi Bot - Fixed Version with Debug Logging"""
import os, time, requests, base64
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
            print(f"✅ Key loaded: {self.key[:8]}...")
        except Exception as e:
            print(f"❌ Key error: {e}")
            self.pk = None
    
    def sign(self, method, path, ts):
        if not self.pk: return "NONE"
        msg = f"{ts}{method}{path}"
        sig = self.pk.sign(msg.encode(), padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
        return base64.b64encode(sig).decode()
    
    def price(self, ticker):
        if not self.key or not self.pk: return None
        ts = str(int(time.time() * 1000))
        path = f"/markets/{ticker}/orderbook"
        h = {"KALSHI-ACCESS-KEY": self.key, "KALSHI-ACCESS-SIGNATURE": self.sign("GET", path, ts), "KALSHI-ACCESS-TIMESTAMP": ts}
        try:
            r = requests.get(f"{self.base}{path}", headers=h, timeout=8)
            if r.status_code == 200:
                asks = r.json().get("orderbook", {}).get("yes", [])
                return min([x[0]/100 for x in asks]) if asks else None
        except: pass
        return None
    
    def buy(self, ticker, n, cents):
        print(f"  [ATTEMPT] Buying {n} @ ${cents/100:.2f}")
        
        if not LIVE:
            print(f"  [DRY RUN] Would buy {n} @ ${cents/100:.2f}")
            return True
        
        if not self.key or not self.pk:
            print(f"  ❌ Missing credentials!")
            return False
        
        ts = str(int(time.time() * 1000))
        path = "/portfolio/orders"
        data = {"ticker": ticker, "action": "buy", "side": "yes", "count": n, "type": "limit", "yes_price": cents}
        h = {"KALSHI-ACCESS-KEY": self.key, "KALSHI-ACCESS-SIGNATURE": self.sign("POST", path, ts), "KALSHI-ACCESS-TIMESTAMP": ts, "Content-Type": "application/json"}
        
        try:
            print(f"  [API] Sending order to Kalshi...")
            r = requests.post(f"{self.base}{path}", json=data, headers=h, timeout=8)
            print(f"  [API] Response: {r.status_code}")
            
            if r.status_code in [200, 201]:
                print(f"  ✅ SUCCESS! Bought {n} @ ${cents/100:.2f}")
                return True
            else:
                print(f"  ❌ API Error {r.status_code}: {r.text[:200]}")
                return False
        except Exception as e:
            print(f"  ❌ Exception: {e}")
            return False

print(f"🤖 Kalshi Bot {'LIVE' if LIVE else 'DRY RUN'} | ${BANKROLL}")
print("="*50)

k = Kalshi()
ticker = "KXELONMARS-99"
losses = 0

while True:
    try:
        p = k.price(ticker)
        if not p:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] No price")
            time.sleep(CHECK_SEC)
            continue
        
        edge = 0.05
        kelly = edge / ((1/p) - 1)
        kelly = min(kelly, 0.10)
        bet = kelly * BANKROLL
        n = int(bet / p) if p > 0 else 0
        
        t = datetime.now().strftime('%H:%M:%S')
        print(f"\n[{t}] ${p:.2f} edge:{edge:.0%} kelly:${bet:.2f} n:{n}")
        
        if n > 0 and losses < 3:
            success = k.buy(ticker, n, int(p * 100))
            if success:
                print(f"  💰 Trade logged!")
            else:
                losses += 1
                print(f"  ⚠️  Trade failed ({losses}/3)")
        else:
            why = "breaker" if losses >= 3 else "small"
            print(f"  ⏸️  Skip ({why})")
        
        time.sleep(CHECK_SEC)
    except KeyboardInterrupt:
        print("\nStopped")
        break
    except Exception as e:
        print(f"Main loop error: {e}")
        time.sleep(CHECK_SEC)
