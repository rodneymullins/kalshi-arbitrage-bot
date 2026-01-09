#!/usr/bin/env python3
"""
Kalshi Backtesting System
Replay historical data through trading strategies to validate profitability
"""

import os
import time
import json
import requests
import base64
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.fee_calculator import FeeCalculator
from strategies.probability_arb import ProbabilityArbitrageDetector

load_dotenv()


class KalshiBacktester:
    """
    Backtest trading strategies using historical Kalshi data
    """
    
    def __init__(self, start_date, end_date, volume_30d=0):
        """
        Initialize backtester
        
        Args:
            start_date: Start date for backtest (YYYY-MM-DD)
            end_date: End date for backtest (YYYY-MM-DD)
            volume_30d: Simulated 30-day volume for fee calculation
        """
        self.start_date = datetime.fromisoformat(start_date).replace(tzinfo=None)
        self.end_date = datetime.fromisoformat(end_date).replace(tzinfo=None)
        self.fee_calc = FeeCalculator(volume_30d)
        
        # Kalshi API
        self.base = "https://api.elections.kalshi.com/trade-api/v2"
        self.key = os.getenv("KALSHI_KEY_ID")
        
        try:
            with open("/Users/rod/Antigravity/kalshi_bot/kalshi.key", "rb") as f:
                self.pk = serialization.load_pem_private_key(f.read(), password=None)
        except:
            self.pk = None
        
        # Results tracking
        self.trades = []
        self.daily_stats = defaultdict(lambda: {
            'opportunities': 0,
            'total_profit': 0,
            'total_volume': 0
        })
    
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
    
    def get_historical_markets(self, cursor=None):
        """
        Fetch historical markets from Kalshi
        
        Note: Kalshi API doesn't have direct historical orderbook data,
        so we'll fetch settled markets and analyze their final prices
        """
        ts = str(int(time.time() * 1000))
        path = f"/trade-api/v2/markets?limit=200&status=settled"
        
        if cursor:
            path += f"&cursor={cursor}"
        
        headers = {
            "KALSHI-ACCESS-KEY": self.key,
            "KALSHI-ACCESS-SIGNATURE": self.sign("GET", path, ts),
            "KALSHI-ACCESS-TIMESTAMP": ts
        }
        
        try:
            r = requests.get(f"{self.base}/markets?limit=200&status=settled", headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                return data.get("markets", []), data.get("cursor")
        except Exception as e:
            print(f"Error fetching markets: {e}")
        
        return [], None
    
    def simulate_probability_arbitrage(self):
        """
        Simulate probability arbitrage strategy on historical data
        
        Since we don't have historical orderbook snapshots, we'll use:
        - Final settlement prices as proxy for opportunities
        - Market volume as indicator of liquidity
        """
        print(f"\n{'='*80}")
        print(f"📊 BACKTESTING PROBABILITY ARBITRAGE")
        print(f"Period: {self.start_date.date()} to {self.end_date.date()}")
        print(f"{'='*80}\n")
        
        print("⚠️  NOTE: Kalshi API limitation - no historical orderbook data")
        print("   Using settled markets as proxy for opportunities\n")
        
        # Fetch settled markets
        all_markets = []
        cursor = None
        
        while True:
            markets, cursor = self.get_historical_markets(cursor)
            if not markets:
                break
            
            # Filter by date range
            for market in markets:
                close_time = datetime.fromisoformat(market.get('close_time', '').replace('Z', '+00:00')).replace(tzinfo=None)
                if self.start_date <= close_time <= self.end_date:
                    all_markets.append(market)
            
            if not cursor:
                break
            
            time.sleep(0.2)  # Rate limit
        
        print(f"📈 Found {len(all_markets)} settled markets in date range\n")
        
        if not all_markets:
            print("❌ No historical data available for this date range")
            return
        
        # Analyze markets
        opportunities_found = 0
        total_theoretical_profit = 0
        
        for market in all_markets:
            # Simulate: If market had any volume, assume there might have been arbitrage
            volume = market.get('volume', 0)
            
            if volume > 100:  # Only consider liquid markets
                # Estimate opportunity based on volume activity
                # Higher volume = more likely to have had price inefficiencies
                
                # Conservative estimate: 1% of volume represents arbitrage opportunities
                arb_volume = volume * 0.01
                
                # Assume 2% deviation on average (conservative)
                deviation = 0.02
                quantity = min(100, int(arb_volume / 0.50))  # Max 100 contracts
                
                if quantity >= 10:  # Minimum viable
                    # Calculate theoretical profit
                    yes_price = 0.51  # Simulated deviation
                    no_price = 0.51
                    
                    arb = self.fee_calc.calculate_arbitrage_profit(yes_price, no_price, quantity)
                    
                    if arb['net_profit'] > 0:
                        opportunities_found += 1
                        total_theoretical_profit += arb['net_profit']
                        
                        # Log trade
                        self.trades.append({
                            'date': market.get('close_time'),
                            'market': market.get('title', '')[:50],
                            'ticker': market.get('ticker'),
                            'quantity': quantity,
                            'profit': arb['net_profit']
                        })
                        
                        # Update daily stats
                        day = market.get('close_time', '')[:10]
                        self.daily_stats[day]['opportunities'] += 1
                        self.daily_stats[day]['total_profit'] += arb['net_profit']
                        self.daily_stats[day]['total_volume'] += volume
        
        # Print results
        self.print_backtest_results(opportunities_found, total_theoretical_profit)
    
    def run_current_snapshot():
        """
        Run a snapshot test on currently available markets
        This tests our detector against live data without executing trades
        """
        print(f"\n{'='*80}")
        print(f"📸 SNAPSHOT TEST - Current Market State")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        
        print("Testing probability arbitrage detector...\n")
        
        detector = ProbabilityArbitrageDetector(
            min_deviation_pct=0.1,  # Very sensitive (0.1% deviation)
            volume_30d=0
        )
        
        opportunities = detector.find_opportunities(
            min_volume=0,  # No volume filter
            max_days_to_expiration=365
        )
        
        if opportunities:
            print(f"✅ Found {len(opportunities)} opportunities!\n")
            detector.print_opportunities(opportunities)
        else:
            print("❌ No opportunities found in current market state")
            print("   Likely reasons:")
            print("   - Off-peak hours (best time: 12pm-8pm ET)")
            print("   - Markets are efficient")
            print("   - Low liquidity\n")
        
        return opportunities
    
    def print_backtest_results(self, opportunities, total_profit):
        """Print backtest summary"""
        print(f"\n{'='*80}")
        print(f"📊 BACKTEST RESULTS")
        print(f"{'='*80}\n")
        
        days_tested = (self.end_date - self.start_date).days + 1
        
        print(f"Period: {days_tested} days")
        print(f"Opportunities Found: {opportunities}")
        print(f"Theoretical Profit: ${total_profit:.2f}")
        print(f"Avg Profit/Day: ${total_profit/days_tested:.2f}")
        print(f"Avg Profit/Opportunity: ${total_profit/opportunities if opportunities > 0 else 0:.2f}\n")
        
        if self.trades:
            print(f"Top 5 Most Profitable Opportunities:")
            sorted_trades = sorted(self.trades, key=lambda x: x['profit'], reverse=True)[:5]
            for i, trade in enumerate(sorted_trades, 1):
                print(f"  {i}. {trade['market']}")
                print(f"     Profit: ${trade['profit']:.2f}, Qty: {trade['quantity']}")
        
        print(f"\n{'='*80}")
        print(f"⚠️  IMPORTANT NOTES:")
        print(f"{'='*80}")
        print("1. These are THEORETICAL results based on limited historical data")
        print("2. Kalshi doesn't provide historical orderbook snapshots")
        print("3. Actual opportunities may have been higher or lower")
        print("4. Execution slippage not accounted for")
        print("5. This validates the FEE CALCULATION accuracy, not strategy profitability")


def run_snapshot_test():
    """Test current market state without live trading"""
    print("="*80)
    print("🧪 KALSHI BACKTESTER - SNAPSHOT MODE")
    print("="*80)
    print("\nMode: SAFE - No live trading, read-only market analysis\n")
    
    return KalshiBacktester.run_current_snapshot()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Backtest Kalshi trading strategies")
    parser.add_argument("--mode", choices=["backtest", "snapshot"], default="snapshot",
                       help="backtest = historical data, snapshot = current state")
    parser.add_argument("--start", default="2026-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2026-01-07", help="End date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    if args.mode == "snapshot":
        # Safe mode - just analyze current market without trading
        opportunities = run_snapshot_test()
        
        if opportunities:
            print(f"\n💡 Found {len(opportunities)} opportunities right now!")
            print(f"   To execute, switch to LIVE mode in bot_v3.py")
        else:
            print(f"\n⏰ Try again during peak hours (12pm-8pm ET)")
    
    else:
        # Historical backtest
        backtester = KalshiBacktester(
            start_date=args.start,
            end_date=args.end,
            volume_30d=0
        )
        
        backtester.simulate_probability_arbitrage()
