#!/usr/bin/env python3
"""Kalshi Bot - Clean Final Version"""
import os, time, requests, base64
from datetime import datetime
from dotenv import load_dotenv
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

load_dotenv()

LIVE = True  # SET TO FALSE FOR DRY RUN
BANKROLL = 9.80
CHECK_SEC = 10

class Kalshi:
    def __init__(self):
        self.base = "https://api.elections.kalshi.com/trade-api/v2"
        self.key = os.getenv("KALSHI_KEY_ID")
        try:
            with open("kalshi.key", "rb") as f:
                self.pk = serialization.load_pem_private_key(f.read(), password=None)
        except: self.pk = None
    
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
        if not LIVE:
            print(f"  [DRY] Buy {n} @ ${cents/100:.2f}")
            return True
        ts = str(int(time.time() * 1000))
        path = "/portfolio/orders"
        data = {"ticker": ticker, "action": "buy", "side": "yes", "count": n, "type": "limit", "yes_price": cents}
        h = {"KALSHI-ACCESS-KEY": self.key, "KALSHI-ACCESS-SIGNATURE": self.sign("POST", path, ts), "KALSHI-ACCESS-TIMESTAMP": ts, "Content-Type": "application/json"}
        try:
            r = requests.post(f"{self.base}{path}", json=data, headers=h, timeout=8)
            if r.status_code in [200, 201]:
                print(f"  ✅ Bought {n} @ ${cents/100:.2f}")
                return True
        except Exception as e:
            print(f"  ❌ {e}")
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
        print(f"[{t}] ${p:.2f} edge:{edge:.0%} kelly:${bet:.2f} n:{n}")
        
        if n > 0 and losses < 3:
            if k.buy(ticker, n, int(p * 100)):
                print(f"  💰 Trade done")
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
