# bot.py
import os
import time
import requests
import base64
from datetime import datetime
from dotenv import load_dotenv
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import serialization
from py_clob_client.client import ClobClient

load_dotenv()

# --- KALSHI SIGNING LOGIC ---
class KalshiClient:
    def __init__(self):
        self.api_base = "https://api.elections.kalshi.com/trade-api/v2"
        self.key_id = os.getenv("KALSHI_KEY_ID")
        try:
            with open("kalshi.key", "rb") as key_file:
                self.private_key = serialization.load_pem_private_key(key_file.read(), password=None)
            print("✅ Kalshi: RSA Private Key loaded.")
        except FileNotFoundError:
            print("❌ Kalshi: 'kalshi.key' not found!")
            self.private_key = None

    def sign_request(self, method, path, timestamp):
        if not self.private_key: return "MISSING_KEY"
        message = f"{timestamp}{method}{path}"
        signature = self.private_key.sign(
            message.encode('utf-8'),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode('utf-8')

    def get_price(self, ticker):
        if not self.key_id or not self.private_key: return 0.0
        ts = str(int(time.time() * 1000))
        path = f"/markets/{ticker}/orderbook"
        headers = {
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": self.sign_request("GET", path, ts),
            "KALSHI-ACCESS-TIMESTAMP": ts
        }
        try:
            resp = requests.get(f"{self.api_base}{path}", headers=headers)
            if resp.status_code != 200:
                print(f"⚠️ Kalshi API Error {resp.status_code}: {resp.text}")
                return 0.0
            data = resp.json()
            yes_asks = data.get('orderbook', {}).get('yes', [])
            return min([x[0] for x in yes_asks]) / 100.0 if yes_asks else 0.0
        except Exception as e:
            print(f"Error fetching Kalshi price: {e}")
            return 0.0

# --- POLYMARKET LOGIC ---
class PolyClient:
    def __init__(self):
        self.host = "https://clob.polymarket.com"
        self.pk = os.getenv("POLY_PK")
        self.client = None
        if self.pk:
            try:
                self.client = ClobClient(self.host, key=self.pk, chain_id=137)
                print("✅ Polymarket: Client initialized.")
            except Exception as e: print(f"❌ Poly Init Failed: {e}")
        else:
            print("⚠️ Polymarket: POLY_PK missing in .env")

    def get_price(self, token_id):
        if not self.client: return 0.0
        try:
            price_info = self.client.get_price(token_id, side="BUY")
            return float(price_info['price'])
        except Exception: return 0.0

# --- BOT ---
class ArbitrageBot:
    def __init__(self, poly_token, kalshi_ticker):
        self.poly = PolyClient()
        self.kalshi = KalshiClient()
        self.poly_token = poly_token
        self.kalshi_ticker = kalshi_ticker

    def run(self):
        print(f"🤖 Bot started. Monitoring {self.kalshi_ticker}...")
        while True:
            # Polymarket disabled here to focus on Kalshi Verify
            p_price = 0.0 
            k_price = self.kalshi.get_price(self.kalshi_ticker)
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Kalshi ({self.kalshi_ticker}): {k_price:.2f}")
            time.sleep(5)

if __name__ == "__main__":
    # Using 'KXELONMARS-99' as verified live ticker
    bot = ArbitrageBot("0xDUMMY", "KXELONMARS-99")
    bot.run()
