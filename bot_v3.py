#!/usr/bin/env python3
"""Kalshi Bot - PRODUCTION v4 - With fee calculator and enhanced profit validation"""
import os, time, requests, base64, json
from datetime import datetime
from dotenv import load_dotenv
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

# Import bot modules
from bot_config import BotConfig
from core.fee_calculator import FeeCalculator
import kelly_criterion
from strategies.timing_optimizer import TimingOptimizer
from strategies.timing_optimizer import TimingOptimizer
from ai.agent_council import AgentCouncil
from trade_db import TradeDB

load_dotenv()

# Load configuration
config = BotConfig
LIVE = config.MODE == "LIVE"
BANKROLL = config.BANKROLL
CHECK_SEC = config.CHECK_INTERVAL_SEC
MIN_VOLUME = config.MIN_VOLUME
MIN_PRICE = config.MIN_PRICE
MIN_NET_PROFIT = config.MIN_NET_PROFIT
TARGET_RETURN_PCT = config.TARGET_RETURN_PCT / 100

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
    
    def get_market_info(self, ticker):
        """Get market details including volume"""
        if not self.key or not self.pk: return None
        ts = str(int(time.time() * 1000))
        path = f"/trade-api/v2/markets/{ticker}"
        h = {"KALSHI-ACCESS-KEY": self.key, "KALSHI-ACCESS-SIGNATURE": self.sign("GET", path, ts), "KALSHI-ACCESS-TIMESTAMP": ts}
        try:
            r = requests.get(f"{self.base}/markets/{ticker}", headers=h, timeout=8)
            if r.status_code == 200:
                return r.json().get("market", {})
        except:
            pass
        return None
    
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

# Display configuration
config.print_config()

# Validate configuration
warnings = config.validate()
if warnings:
    print("⚠️  Configuration Warnings:")
    for warning in warnings:
        print(f"   {warning}")
    print()

# Initialize fee calculator
fee_calc = FeeCalculator(volume_30d=config.VOLUME_30D)
print(f"💰 Fee Calculator Initialized")
print(f"   30-day Volume: ${config.VOLUME_30D:,.2f}")
print(f"   Fee Tier: {config.get_fee_tier()}% (Taker) / {config.get_fee_tier()/2}% (Maker)")
print(f"   Min Net Profit: ${MIN_NET_PROFIT:.2f}")

# Initialize AI decision system
timing_optimizer = TimingOptimizer()
agent_council = AgentCouncil()
print(f"\n🤖 AI Decision System Initialized")
print(f"   Kelly Criterion: Enabled (Bankroll: ${BANKROLL:,.2f})")
print(f"   Timing Optimizer: Enabled")
print(f"   Agent Council: 4 agents (Risk, Value, Timing, Sentiment)")
print("="*60)

# Initialize Database
try:
    db = TradeDB()
    print("✅ TradeDB Connected")
except Exception as e:
    print(f"⚠️  TradeDB Failed: {e}")
    db = None

k = Kalshi()
ticker = "KXMVESPORTSMULTIGAMEEXTENDED-S20256C509BBBCA5-1F88D9ED2AC"  # Updated by daily scan
losses = 0
no_price_count = 0

# Pre-flight check: Verify market volume
print(f"\n🔍 Pre-flight check for {ticker[:50]}...")
market_info = k.get_market_info(ticker)
if market_info:
    volume = market_info.get('volume', 0)
    title = market_info.get('title', '')[:70]
    print(f"   Market: {title}")
    print(f"   Volume: ${volume:,}")
    
    if volume < MIN_VOLUME:
        print(f"\n⚠️  HALTED: Market volume (${volume:,}) below minimum (${MIN_VOLUME:,})")
        print(f"   This market is too illiquid for reliable trading.")
        print(f"   Run './daily_scan.sh' to find a better market.")
        exit(0)
    else:
        print(f"   ✅ Volume check passed!")
else:
    print(f"   ⚠️  Could not verify market info, proceeding with caution...")

print("\n🚀 Starting trading loop...\n")

while True:
    try:
        p = k.price(ticker)
        if not p:
            no_price_count += 1
            print(f"[{datetime.now().strftime('%H:%M:%S')}] No price (#{no_price_count})")
            if no_price_count >= config.MAX_NO_PRICE_COUNT:
                print("\n⛔ HALTED: Market has no pricing for 5+ minutes. Empty orderbook.")
                print("   This usually means we're outside trading hours or the market is illiquid.")
                print("   Recommendation: Run during peak hours (12pm-8pm ET) or find a liquid market.")
                break
            time.sleep(CHECK_SEC)
            continue
        
        no_price_count = 0  # Reset counter when we get a price
        
        # Skip markets below minimum price
        if p < MIN_PRICE:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Price ${p:.2f} below min ${MIN_PRICE:.2f} - skipping")
            time.sleep(CHECK_SEC)
            continue
        
        t = datetime.now().strftime('%H:%M:%S')
        
        # Prepare opportunity data for AI decision system
        opportunity = {
            'spread': 0.03,  # Placeholder - would calculate from orderbook
            'net_profit': 0,  # Will be calculated
            'price': p,
            'market_category': 'sports',  # Would extract from market title
            'ai_score': 0.65  # Placeholder - would come from FunctionGemma
        }
        
        # Prepare market data for agents
        market_data = {
            'volatility': 0.08,  # Placeholder
            'volume_1h': market_info.get('volume', 0) if market_info else 0,
            'close_time_hours': 12,  # Placeholder
            'orderbook': [],  # Placeholder
            'recent_prices': [p]  # Placeholder
        }
        
        # Bot state for risk assessment
        bot_state = {
            'consecutive_losses': losses,
            'last_category': 'sports'  # Placeholder
        }
        
        # Step 1: Agent Council Decision
        council_decision = agent_council.decide(opportunity, market_data, bot_state)
        
        if not council_decision['execute']:
            print(f"[{t}] Council VETOED trade - Confidence: {council_decision['confidence']:.0%}")
            print(f"  Votes: {council_decision['votes']}")
            time.sleep(CHECK_SEC)
            continue
        
        print(f"[{t}] Council APPROVED trade - Confidence: {council_decision['confidence']:.0%}")
        
        # Step 2: Timing Check
        timing_rec = timing_optimizer.get_execution_recommendation(opportunity, market_data)
        
        if not timing_rec['execute_now']:
            print(f"  ⏰ Timing: WAIT {timing_rec['recommended_delay_human']}")
            print(f"     Reasons: {', '.join(timing_rec['reasons'])}")
            time.sleep(CHECK_SEC)
            continue
        
        print(f"  ⏰ Timing: EXECUTE NOW (optimal)")
        
        # Step 3: Kelly Position Sizing
        edge = config.EDGE
        kelly_fraction = kelly_criterion.get_kelly_fraction(edge, p)
        bet = kelly_criterion.get_bet_size(edge, p, BANKROLL)
        n = int(bet / p) if p > 0 else 0
        
        if n > 0 and losses < config.MAX_CONSECUTIVE_LOSSES:
            # Calculate expected profit with fees
            # Assume we'll sell at target return price
            target_sell_price = min(p * (1 + TARGET_RETURN_PCT), 0.99)  # Cap at $0.99
            
            # Get profit analysis
            profit_analysis = fee_calc.calculate_net_profit(
                buy_price=p,
                sell_price=target_sell_price,
                quantity=n
            )
            
            gross_profit = profit_analysis['gross_profit']
            total_fees = profit_analysis['fees']
            net_profit = profit_analysis['net_profit']
            
            # Display analysis
            print(f"\n[{t}] 🤖 AI-ENHANCED TRADE")
            print(f"  Price: ${p:.2f} | Edge: {edge:.0%} | Kelly: {kelly_fraction:.1%} | Qty: {n}")
            print(f"  Council: {council_decision['confidence']:.0%} confidence (Score: {council_decision['weighted_score']:.2f})")
            print(f"  Buy @ ${p:.2f} → Sell @ ${target_sell_price:.2f} ({TARGET_RETURN_PCT*100:.0f}% target)")
            print(f"  Gross: ${gross_profit:.2f} - Fees: ${total_fees:.2f} = Net: ${net_profit:.2f}")
            
            # Check if profitable after fees
            if net_profit >= MIN_NET_PROFIT:
                print(f"  ✅ Profitable after fees (>${MIN_NET_PROFIT:.2f})")
                
                if k.buy(ticker, n, int(p * 100)):
                    if db:
                        try:
                            trade_id = db.log_trade(
                                market=ticker,
                                side="YES", # Assuming YES for now as per logic
                                size=n,
                                price=p,
                                pnl=0 # Initial PnL
                            )
                            print(f"  📝 Logged trade ID: {trade_id}")
                        except Exception as e:
                            print(f"  ⚠️  Failed to log trade: {e}")
                            
                    losses = 0  # Reset on success
                else:
                    losses += 1
                    print(f"  ⚠️  Order failed ({losses}/{config.MAX_CONSECUTIVE_LOSSES})")
            else:
                print(f"  ⏸️  SKIP: Net profit ${net_profit:.2f} < minimum ${MIN_NET_PROFIT:.2f}")
                print(f"       Fees (${total_fees:.2f}) too high for this position size")
        else:
            why = "breaker" if losses >= config.MAX_CONSECUTIVE_LOSSES else "small position"
            print(f"\n[{t}] Price: ${p:.2f} | Skip ({why})")
        
        time.sleep(CHECK_SEC)
    except KeyboardInterrupt:
        print("\n👋 Stopped by user")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(CHECK_SEC)
