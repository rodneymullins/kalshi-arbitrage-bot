# Enhanced Kalshi Bot with Kelly Criterion, Circuit Breaker, and Live Trading
import os
import time
import requests
import base64
from datetime import datetime
from dotenv import load_dotenv
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
# from py_clob_client.client import ClobClient  # Not needed for Kalshi-only

# Import our modules
from kelly_criterion import calculate_kelly_bet
from circuit_breaker import CircuitBreaker
from trade_db import TradeDB
# win_probability model now inline (simple +5% edge)

load_dotenv()

# Configuration
LIVE_TRADING = False  # Set to True to enable real trades
BANKROLL = 9.80  # Current account balance
MIN_EDGE = 0.05  # Minimum 5% edge to trade
CHECK_INTERVAL = 10  # Seconds between checks

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

    def get_balance(self):
        """Get current account balance"""
        if not self.key_id or not self.private_key: return 0.0
        ts = str(int(time.time() * 1000))
        path = "/portfolio/balance"
        headers = {
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": self.sign_request("GET", path, ts),
            "KALSHI-ACCESS-TIMESTAMP": ts
        }
        try:
            resp = requests.get(f"{self.api_base}{path}", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                balance = data.get('balance', 0) / 100.0  # Convert cents to dollars
                return balance
            return 0.0
        except Exception as e:
            print(f"Error fetching balance: {e}")
            return 0.0

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

    def place_order(self, ticker, side, contracts, price):
        """
        Place an order on Kalshi
        side: 'yes' or 'no'
        price: in cents (e.g., 55 for $0.55)
        """
        if not LIVE_TRADING:
            print(f"[DRY RUN] Would place: {side} {contracts} {ticker} @ ${price/100:.2f}")
            return {"order_id": "DRY_RUN", "success": True}
        
        ts = str(int(time.time() * 1000))
        path = f"/portfol io/orders"
        
        payload = {
            "ticker": ticker,
            "action": "buy",
            "side": side,
            "count": contracts,
            "type": "limit",
            "yes_price": price if side == "yes" else None,
            "no_price": price if side == "no" else None
        }
        
        headers = {
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": self.sign_request("POST", path, ts),
            "KALSHI-ACCESS-TIMESTAMP": ts,
            "Content-Type": "application/json"
        }
        
        try:
            resp = requests.post(f"{self.api_base}{path}", json=payload, headers=headers)
            if resp.status_code in [200, 201]:
                return {"order_id": resp.json().get('order_id'), "success": True}
            else:
                print(f"❌ Order failed: {resp.status_code} - {resp.text}")
                return {"error": resp.text, "success": False}
        except Exception as e:
            print(f"❌ Order exception: {e}")
            return {"error": str(e), "success": False}


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


# --- ENHANCED BOT ---
class TradingBot:
    def __init__(self, kalshi_ticker, bankroll=BANKROLL):
        self.kalshi = KalshiClient()
        self.db = TradeDB()
        self.breaker = CircuitBreaker(
            max_drawdown=0.15,      # 15% max drawdown
            max_daily_loss=2.00,    # $2 daily loss limit (conservative for $9.80)
            max_consecutive_losses=3  # 3 losses in a row
        )
        self.ticker = kalshi_ticker
        self.bankroll = bankroll
        self.trade_count = 0
    
    def estimate_win_probability(self, market_price):
        """Simple model: market price + 5% edge"""
        return min(market_price + 0.05, 0.95)  # Cap at 95%

    def run(self):
        print(f"🤖 Enhanced Kalshi Bot Started")
        print(f"📊 Mode: {'LIVE TRADING' if LIVE_TRADING else 'DRY RUN'}")
        print(f"💰 Bankroll: ${self.bankroll:.2f}")
        print(f"🎯 Market: {self.ticker}")
        print(f"⚡ Min Edge: {MIN_EDGE:.1%}")
        print("="*50)

        while True:
            try:
                # Check circuit breaker
                if self.breaker.is_halted:
                    print(f"\n⛔ TRADING HALTED: {self.breaker.halt_reason}")
                    print("💤 Sleeping for 5 minutes before retry...")
                    time.sleep(300)
                    continue

                # Get current price
                k_price = self.kalshi.get_price(self.ticker)
                if k_price == 0.0:
                    print("⚠️ Unable to fetch price, skipping...")
                    time.sleep(CHECK_INTERVAL)
                    continue

                # Use sophisticated model
                prediction = self.model.estimate_win_probability(self.ticker, k_price)
                win_prob = prediction['win_prob']
                edge = prediction['edge']
                confidence = prediction['confidence']


                # Display status
                now = datetime.now().strftime('%H:%M:%S')
                print(f"\n[{now}] ${k_price:.2f} | Est Win: {win_prob:.1%} | Edge: {edge:+.1%} | Conf: {confidence:.0%}")
                print(f"   {prediction['reasoning']}")
                
                if edge >= MIN_EDGE and confidence >= 0.5:  # Require both edge AND confidence
                    # Calculate Kelly bet size
                    bet_size = calculate_kelly_bet(
                        win_probability=win_prob,
                        market_price=k_price,
                        bankroll=self.bankroll,
                        max_fraction=0.10  # Ultra conservative
                    )
                    contracts = int(bet_size / k_price) if k_price > 0 else 0
                    
                    if contracts > 0:
                        print(f"🎯 SIGNAL: Kelly ${bet_size:.2f} ({contracts} contracts)")
                    
                    # Place order
                    result = self.kalshi.place_order(
                        self.ticker,
                        "yes",
                        contracts,
                        int(k_price * 100)  # Convert to cents
                    )
                    
                    if result.get("success"):
                        # Log trade
                        trade_id = self.db.log_trade(
                            market=self.ticker,
                            side="BUY",
                            size=contracts,
                            price=k_price,
                            pnl=0
                        )
                        
                        # Update bankroll
                        self.bankroll -= (contracts * k_price)
                        self.trade_count += 1
                        
                        print(f"✅ Order placed! Remaining: ${self.bankroll:.2f}")
                        
                        # Save performance snapshot
                        self.db.save_performance_snapshot()
                else:
                    print(f"⏸️  No trade: Edge {edge:.1%} < {MIN_EDGE:.1%} or size too small")

                # Sleep before next check
                time.sleep(CHECK_INTERVAL)

            except KeyboardInterrupt:
                print("\n👋 Bot stopped by user")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(CHECK_INTERVAL)

        # Final stats
        print("\n" + "="*50)
        print("📊 Final Statistics:")
        stats = self.db.get_performance_stats()
        print(f"Total Trades: {stats['total_trades']}")
        print(f"Total P&L: ${stats['total_pnl']:.2f}")
        print(f"Win Rate: {stats['win_rate']:.1%}")
        print(f"Final Bankroll: ${self.bankroll:.2f}")


if __name__ == "__main__":
    # Create bot instance
    bot = TradingBot("KXELONMARS-99", bankroll=BANKROLL)
    
    # Run
    bot.run()
