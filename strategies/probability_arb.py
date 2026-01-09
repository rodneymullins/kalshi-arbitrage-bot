#!/usr/bin/env python3
"""
Probability Arbitrage Detector
Finds markets where YES + NO prices != 100%, creating risk-free profit opportunities
Based on vladmeer/kalshi-arbitrage-bot strategy
"""

import os
import time
import requests
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# Import our fee calculator
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.fee_calculator import FeeCalculator

load_dotenv()


class ProbabilityArbitrageDetector:
    """
    Detect probability arbitrage opportunities on Kalshi
    
    Strategy: When YES + NO prices != 100%, you can buy/sell both sides
    and lock in guaranteed profit regardless of outcome.
    """
    
    def __init__(self, min_deviation_pct=1.0, volume_30d=0):
        """
        Initialize detector
        
        Args:
            min_deviation_pct: Minimum price deviation to consider (default 1%)
            volume_30d: Your 30-day trading volume for fee calculation
        """
        self.min_deviation = min_deviation_pct / 100  # Convert to decimal
        self.fee_calc = FeeCalculator(volume_30d)
        
        # Kalshi API setup
        self.base = "https://api.elections.kalshi.com/trade-api/v2"
        self.key = os.getenv("KALSHI_KEY_ID")
        
        try:
            with open("/Users/rod/Antigravity/kalshi_bot/kalshi.key", "rb") as f:
                self.pk = serialization.load_pem_private_key(f.read(), password=None)
        except:
            self.pk = None
    
    def sign(self, method, path, ts):
        """Sign API request"""
        if not self.pk:
            return "NONE"
        msg = f"{ts}{method}{path}"
        sig = self.pk.sign(
            msg.encode(),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )
        return base64.b64encode(sig).decode()
    
    def get_all_markets(self, limit=200, status="open"):
        """Fetch all open markets from Kalshi"""
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
            print(f"Error fetching markets: {e}")
        
        return []
    
    def get_orderbook(self, ticker):
        """Get orderbook for a specific market"""
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
        
        return None
    
    def get_best_prices(self, orderbook):
        """Extract best YES and NO prices from orderbook"""
        yes_asks = orderbook.get("yes", [])
        no_asks = orderbook.get("no", [])
        
        if not yes_asks or not no_asks:
            return None, None
        
        # Best ask = lowest price someone is willing to sell at
        yes_price = min([ask[0] for ask in yes_asks]) / 100  # Convert cents to dollars
        no_price = min([ask[0] for ask in no_asks]) / 100
        
        return yes_price, no_price
    
    def calculate_days_to_expiration(self, close_time_str):
        """Calculate days until market expiration"""
        try:
            close_time = datetime.fromisoformat(close_time_str.replace("Z", "+00:00"))
            now = datetime.now(close_time.tzinfo)
            delta = close_time - now
            return delta.total_seconds() / 86400  # Convert to days
        except:
            return 0
    
    def find_opportunities(self, min_volume=0, max_days_to_expiration=30):
        """
        Scan all markets for probability arbitrage opportunities
        
        Args:
            min_volume: Minimum 24h volume filter
            max_days_to_expiration: Only consider markets closing within N days
        
        Returns:
            list: Sorted opportunities by profit per day
        """
        print(f"🔍 Scanning Kalshi markets for probability arbitrage...")
        markets = self.get_all_markets(limit=200)
        
        if not markets:
            print("❌ No markets found")
            return []
        
        print(f"📊 Checking {len(markets)} markets...")
        opportunities = []
        
        for market in markets:
            # Filter by volume
            if market.get("volume", 0) < min_volume:
                continue
            
            # Filter by expiration
            days_left = self.calculate_days_to_expiration(market.get("close_time", ""))
            if days_left <= 0 or days_left > max_days_to_expiration:
                continue
            
            # Get orderbook
            ticker = market.get("ticker")
            orderbook = self.get_orderbook(ticker)
            
            if not orderbook:
                continue
            
            # Get best prices
            yes_price, no_price = self.get_best_prices(orderbook)
            
            if yes_price is None or no_price is None:
                continue
            
            # Check for arbitrage
            total_prob = yes_price + no_price
            deviation = abs(total_prob - 1.0)
            
            if deviation >= self.min_deviation:
                # Calculate profit potential
                quantity = 100  # Standard lot size
                arb_result = self.fee_calc.calculate_arbitrage_profit(yes_price, no_price, quantity)
                
                if arb_result['is_profitable']:
                    opportunities.append({
                        'market': market,
                        'ticker': ticker,
                        'title': market.get('title', '')[:75],
                        'yes_price': yes_price,
                        'no_price': no_price,
                        'total_probability': total_prob,
                        'deviation_pct': deviation * 100,
                        'days_to_expiration': days_left,
                        'volume': market.get('volume', 0),
                        'close_time': market.get('close_time'),
                        'arb_result': arb_result,
                        'profit_per_day': arb_result['net_profit'] / days_left if days_left > 0 else 0
                    })
                    
                    # Rate limit
                    time.sleep(0.2)
        
        # Sort by profit per day
        opportunities.sort(key=lambda x: x['profit_per_day'], reverse=True)
        
        return opportunities
    
    def print_opportunities(self, opportunities):
        """Print opportunities in a nice format"""
        if not opportunities:
            print("\n❌ No profitable arbitrage opportunities found")
            print("   This could mean:")
            print("   - Markets are efficient right now")
            print("   - Liquidity is too low")
            print("   - Try lowering min_deviation threshold")
            return
        
        print(f"\n{'='*80}")
        print(f"✨ PROBABILITY ARBITRAGE OPPORTUNITIES: Found {len(opportunities)}!")
        print(f"{'='*80}\n")
        
        for i, opp in enumerate(opportunities, 1):
            print(f"[{i}] {'='*76}")
            print(f"Market: {opp['title']}")
            print(f"Ticker: {opp['ticker']}")
            print(f"Volume: ${opp['volume']:,}")
            print(f"Closes: {opp['close_time']} ({opp['days_to_expiration']:.1f} days)")
            print(f"\nPricing:")
            print(f"  YES: ${opp['yes_price']:.2f}")
            print(f"  NO:  ${opp['no_price']:.2f}")
            print(f"  Total: {opp['total_probability']*100:.1f}% (should be 100%)")
            print(f"  Deviation: {opp['deviation_pct']:.2f}%")
            print(f"\nProfit Analysis (100 contracts):")
            arb = opp['arb_result']
            print(f"  Total Cost: ${arb['total_cost']:.2f}")
            print(f"  Guaranteed Payout: ${arb['guaranteed_payout']:.2f}")
            print(f"  Gross Profit: ${arb['gross_profit']:.2f}")
            print(f"  Fees: ${arb['total_fees']:.2f}")
            print(f"  Net Profit: ${arb['net_profit']:.2f}")
            print(f"  Profit per Day: ${opp['profit_per_day']:.2f}")
            print(f"{'='*76}\n")


if __name__ == "__main__":
    # Run detector
    detector = ProbabilityArbitrageDetector(
        min_deviation_pct=0.5,  # Look for 0.5%+ deviations
        volume_30d=0  # New trader fees
    )
    
    opportunities = detector.find_opportunities(
        min_volume=100,  # At least $100 volume
        max_days_to_expiration=30
    )
    
    detector.print_opportunities(opportunities)
    
    if opportunities:
        print(f"\n💡 Best Opportunity:")
        best = opportunities[0]
        print(f"   Market: {best['title']}")
        print(f"   Net Profit: ${best['arb_result']['net_profit']:.2f}")
        print(f"   Profit per Day: ${best['profit_per_day']:.2f}")
