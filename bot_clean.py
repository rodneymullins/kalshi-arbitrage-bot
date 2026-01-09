#!/usr/bin/env python3
"""
Clean Kalshi Trading Bot
Simple +5% edge strategy with safety limits
"""

import os
import time
import requests
import base64
from datetime import datetime
from dotenv import load_dotenv
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

load_dotenv()

# Configuration
LIVE_TRADING = True
BANKROLL = 9.80
MIN_EDGE = 0.05
MAX_BET_FRACTION = 0.10
CHECK_INTERVAL = 10

class KalshiClient:
    def __init__(self):
        self.api_base = "https://api.elections.kalshi.com/trade-api/v2"
        self.key_id = os.getenv("KALSHI_KEY_ID")
        
        try:
            with open("kalshi.key", "rb") as f:
                self.private_key = serialization.load_pem_private_key(f.read(), password=None)
            print("✅ Kalshi: Key loaded")
        except:
            print("❌ Kalshi: Key not found")
            self.private_key = None

    def sign_request(self, method, path, timestamp):
        if not self.private_key:
            return "MISSING_KEY"
        message = f"{timestamp}{method}{path}"
        signature = self.private_key.sign(
            message.encode('utf-8'),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode('utf-8')

    def get_price(self, ticker):
        if not self.key_id or not self.private_key:
            return None
        
        ts = str(int(time.time() * 1000))
        path = f"/markets/{ticker}/orderbook"
        headers = {
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": self.sign_request("GET", path, ts),
            "KALSHI-ACCESS-TIMESTAMP": ts
        }
        
        try:
            resp = requests.get(f"{self.api_base}{path}", headers=headers, timeout=10)
            if resp.status_code != 200:
                return None
            
            data = resp.json()
            yes_asks = data.get('orderbook', {}).get('yes', [])
            if yes_asks:
                return min([x[0] for x in yes_asks]) / 100.0
        except:
            pass
        
        return None

    def place_order(self, ticker, contracts, price_cents):
        if not LIVE_TRADING:
            print(f"[DRY RUN] Would buy {contracts} contracts @ ${price_cents/100:.2f}")
            return True
        
        ts = str(int(time.time() * 1000))
        path = "/portfolio/orders"
        payload = {
            "ticker": ticker,
            "action": "buy",
            "side": "yes",
            "count": contracts,
            "type": "limit",
            "yes_price": price_cents
        }
        
        headers = {
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": self.sign_request("POST", path, ts),
            "KALSHI-ACCESS-TIMESTAMP": ts,
            "Content-Type": "application/json"
        }
        
        try:
            resp = requests.post(f"{self.api_base}{path}", json=payload, headers=headers, timeout=10)
            if resp.status_code in [200, 201]:
                print(f"✅ Order placed: {contracts} @ ${price_cents/100:.2f}")
                return True
            else:
                print(f"❌ Order failed: {resp.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False


def main():
    print("🤖 Kalshi Bot Started")
    print(f"📊 Mode: {'LIVE' if LIVE_TRADING else 'DRY RUN'}")
    print(f"💰 Bankroll: ${BANKROLL:.2f}")
    print(f"📈 Strategy: Market price + 5% edge")
    print("="*50)
    
    kalshi = KalshiClient()
    ticker = "KXELONMARS-99"
    
    consecutive_losses = 0
    total_pnl = 0.0
    
    while True:
        try:
            # Get price
            price = kalshi.get_price(ticker)
            
            if price is None:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  Can't fetch price")
                time.sleep(CHECK_INTERVAL)
                continue
            
            # Calculate edge (simple +5%)
            win_prob = min(price + 0.05, 0.95)
            edge = win_prob - price
            
            # Kelly sizing
            if edge >= MIN_EDGE:
                kelly_fraction = edge / (1/price - 1)
                kelly_fraction = min(kelly_fraction, MAX_BET_FRACTION)
                bet_amount = kelly_fraction * BANKROLL
                contracts = int(bet_amount / price) if price > 0 else 0
                
                now = datetime.now().strftime('%H:%M:%S')
                print(f"\n[{now}] ${price:.2f} | Edge: {edge:+.1%} | Kelly: ${bet_amount:.2f}")
                
                if contracts > 0 and consecutive_losses < 3:
                    # Place order
                    success = kalshi.place_order(ticker, contracts, int(price * 100))
                    
                    if success:
                        # Log trade (simplified - just print for now)
                        print(f"💰 Trade: {contracts} contracts @ ${price:.2f}")
                    else:
                        consecutive_losses += 1
                else:
                    print(f"⏸️  No trade: {'Circuit breaker' if consecutive_losses >= 3 else 'Size too small'}")
            else:
                now = datetime.now().strftime('%H:%M:%S')
                print(f"[{now}] ${price:.2f} | Edge: {edge:+.1%} | No trade (< 5%)")
            
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n👋 Bot stopped")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
