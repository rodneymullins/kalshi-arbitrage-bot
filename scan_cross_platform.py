"""
Cross-Platform Arbitrage Scanner

Scans both Kalshi and Polymarket for arbitrage opportunities.
"""
import sys
import os
import time
from datetime import datetime
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.polymarket_client import PolymarketClient
from strategies.market_matcher import MarketMatcher
from config.cross_platform_config import CROSS_PLATFORM, POLYMARKET_FEES
from ai.functiongemma_analyzer import FunctionGemmaAnalyzer
from db.opportunity_logger import OpportunityLogger
import requests


class CrossPlatformScanner:
    """Scan for arbitrage opportunities across Kalshi and Polymarket."""
    
    def __init__(self):
        self.polymarket = PolymarketClient()
        self.matcher = MarketMatcher()
        self.kalshi_api_base = "https://api.elections.kalshi.com/trade-api/v2"
        
        # Initialize AI analyzer (FunctionGemma)
        try:
            self.ai_analyzer = FunctionGemmaAnalyzer()
            self.ai_enabled = True
            print("✅ AI Analysis enabled (FunctionGemma)")
        except Exception as e:
            print(f"⚠️  AI Analysis disabled: {e}")
            self.ai_analyzer = None
            self.ai_enabled = False
        
        # Initialize database logger
        try:
            self.db_logger = OpportunityLogger()
            self.db_enabled = True
            print("✅ Database logging enabled (PostgreSQL)")
        except Exception as e:
            print(f"⚠️  Database logging disabled: {e}")
            self.db_logger = None
            self.db_enabled = False
        
        self.config = CROSS_PLATFORM
        self.position_size = self.config["position_size"]
        self.min_profit = self.config["min_profit_threshold"]
    
    def get_kalshi_markets(self, limit=100):
        """Fetch Kalshi markets (simplified)."""
        try:
            url = f"{self.kalshi_api_base}/markets"
            response = requests.get(url, params={"limit": limit}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                markets = data.get("markets", [])
                # Filter for active, non-sports markets
                return [m for m in markets if m.get("status") == "active" and
                       "SINGLEGAME" not in m.get("ticker", "") and
                       "MULTIGAME" not in m.get("ticker", "")]
            return []
        except Exception as e:
            print(f"Error fetching Kalshi markets: {e}")
            return []
    
    def calculate_kalshi_fee(self, price_cents, quantity):
        """Simple Kalshi fee calculation."""
        # Approximate fee: 2-3.5% based on price
        if price_cents < 10 or price_cents > 90:
            fee_rate = 0.01  # 1% at extremes
        elif 40 <= price_cents <= 60:
            fee_rate = 0.035  # 3.5% near 50 cents
        else:
            fee_rate = 0.025  # 2.5% otherwise
        
        cost = (price_cents / 100) * quantity
        return cost * fee_rate
    
    def calculate_arb_opportunity(self, k_market: Dict, pm_market: Dict) -> Dict:
        """
        Calculate arbitrage opportunity between matched markets.
        
        Returns dict with opportunity details or empty dict if no opportunity.
        """
        # Get Kalshi YES price
        k_yes_price = k_market.get("yes_ask", 0) / 100.0  # Convert cents to dollars
        k_no_price = k_market.get("no_ask", 0) / 100.0
        
        # Get Polymarket prices (need to fetch from orderbook)
        # For now, use simplified approach
        pm_tokens = pm_market.get("tokens", [])
        if len(pm_tokens) < 2:
            return {}
        
        # Get YES token price
        yes_token_id = pm_tokens[0].get("token_id", "") if len(pm_tokens) > 0 else ""
        pm_yes_price = self.polymarket.get_price(yes_token_id, "BUY") if yes_token_id else 0.0
        pm_no_price = 1.0 - pm_yes_price  # NO is inverse of YES
        
        if pm_yes_price == 0.0:
            return {}
        
        # Calculate all possible arbitrage combinations
        opportunities = []
        
        # Opportunity 1: Buy YES on one, NO on other
        # Buy YES on Kalshi, NO on Polymarket
        cost_1 = k_yes_price + pm_no_price
        profit_1 = 1.0 - cost_1
        
        # Buy NO on Kalshi, YES on Polymarket
        cost_2 = k_no_price + pm_yes_price
        profit_2 = 1.0 - cost_2
        
        # Buy YES on Polymarket, NO on Kalshi
        cost_3 = pm_yes_price + k_no_price
        profit_3 = 1.0 - cost_3
        
        # Buy NO on Polymarket, YES on Kalshi
        cost_4 = pm_no_price + k_yes_price
        profit_4 = 1.0 - cost_4
        
        # Find best opportunity
        opportunities = [
            {"strategy": f"Buy YES on Kalshi (${k_yes_price:.2f}), NO on Polymarket (${pm_no_price:.2f})", 
             "gross_profit": profit_1, "cost": cost_1},
            {"strategy": f"Buy NO on Kalshi (${k_no_price:.2f}), YES on Polymarket (${pm_yes_price:.2f})", 
             "gross_profit": profit_2, "cost": cost_2},
        ]
        
        best_opp = max(opportunities, key=lambda x: x["gross_profit"])
        
        # Calculate fees
        # Kalshi fee
        k_price = int(k_yes_price * 100 if "YES on Kalshi" in best_opp["strategy"] else k_no_price * 100)
        k_qty = int(self.position_size / (k_price / 100)) if k_price > 0 else 0
        k_fee = self.calculate_kalshi_fee(k_price, k_qty)
        
        # Polymarket fee (2% on profits)
        pm_fee = max(0, best_opp["gross_profit"] * self.position_size * POLYMARKET_FEES["trading_fee_rate"])
        
        total_fees = k_fee + pm_fee + POLYMARKET_FEES["gas_fee_estimate"]
        
        # Net profit
        gross_profit_dollars = best_opp["gross_profit"] * self.position_size
        net_profit = gross_profit_dollars - total_fees
        
        # Check if profitable
        if net_profit >= self.min_profit:
            opportunity = {
                "kalshi_market": k_market.get("title", ""),
                "polymarket_market": pm_market.get("question", ""),
                "strategy": best_opp["strategy"],
                "gross_profit": gross_profit_dollars,
                "total_fees": total_fees,
                "net_profit": net_profit,
                "roi": (net_profit / (best_opp["cost"] * self.position_size)) * 100 if best_opp["cost"] > 0 else 0,
                "kalshi_prices": f"YES: ${k_yes_price:.2f}, NO: ${k_no_price:.2f}",
                "polymarket_prices": f"YES: ${pm_yes_price:.2f}, NO: ${pm_no_price:.2f}",
            }
            
            # Add AI analysis if enabled
            if self.ai_enabled and self.ai_analyzer:
                try:
                    print(f"  🤖 Analyzing with FunctionGemma...")
                    ai_analysis = self.ai_analyzer.analyze_opportunity({
                        "kalshi_market": opportunity["kalshi_market"],
                        "polymarket_market": opportunity["polymarket_market"],
                        "match_confidence": 0.8,  # Would come from matcher
                        "net_profit": net_profit,
                        "roi": opportunity["roi"]
                    })
                    
                    opportunity["ai_analysis"] = ai_analysis
                    opportunity["ai_score"] = ai_analysis.get("ai_score", 0.5)
                    opportunity["ai_recommendation"] = ai_analysis.get("recommendation", "UNKNOWN")
                    
                except Exception as e:
                    print(f"  ⚠️  AI analysis failed: {e}")
                    opportunity["ai_analysis"] = None
                    opportunity["ai_score"] = 0.5
                    opportunity["ai_recommendation"] = "AI_ERROR"
            
            return opportunity
        
        return {}
    
    def scan_once(self) -> List[Dict]:
        """
        Perform a single scan for arbitrage opportunities.
        
        Returns list of opportunities found.
        """
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting scan...")
        
        # Start database session
        if self.db_enabled:
            self.db_logger.start_session(
                ai_enabled=self.ai_enabled,
                config={"position_size": self.position_size, "min_profit": self.min_profit}
            )
        
        # Fetch markets
        print("  Fetching Kalshi markets...")
        k_markets = self.get_kalshi_markets(limit=100)
        
        print("  Fetching Polymarket markets...")
        pm_markets = self.polymarket.get_simplified_markets(limit=100)
        
        print(f"  Found {len(k_markets)} Kalshi markets, {len(pm_markets)} Polymarket markets")
        
        if not k_markets:
            print("  ⚠️  No Kalshi markets available (likely all sports parlays)")
            if self.db_enabled:
                self.db_logger.end_session("No Kalshi markets available")
            return []
        
        # Match markets
        print("  Matching markets...")
        matches = self.matcher.batch_match(k_markets, pm_markets, min_confidence=0.75)
        
        print(f"  Found {len(matches)} matched market pairs")
        
        # Find arbitrage opportunities
        opportunities = []
        
        for match in matches:
            opp = self.calculate_arb_opportunity(
                match["kalshi_market"],
                match["polymarket_market"]
            )
            
            if opp:
                opp["match_confidence"] = match["confidence"]
                opportunities.append(opp)
                
                # Log to database
                if self.db_enabled:
                    self.db_logger.log_opportunity(opp)
        
        # End session
        if self.db_enabled:
            notes = f"Found {len(opportunities)} opportunities"
            self.db_logger.end_session(notes)
        
        return opportunities
    
    def display_opportunities(self, opportunities: List[Dict]):
        """Display found opportunities in a readable format."""
        if not opportunities:
            print("\n❌ No arbitrage opportunities found.\n")
            return
        
        print(f"\n{'='*100}")
        print(f"🎯 FOUND {len(opportunities)} ARBITRAGE OPPORTUNITIES!")
        print(f"{'='*100}\n")
        
        for i, opp in enumerate(opportunities, 1):
            print(f"[{i}] {'='*90}")
            print(f"Kalshi:      {opp['kalshi_market']}")
            print(f"Polymarket:  {opp['polymarket_market']}")
            print(f"\nStrategy: {opp['strategy']}")
            print(f"\nPrices:")
            print(f"  Kalshi:      {opp['kalshi_prices']}")
            print(f"  Polymarket:  {opp['polymarket_prices']}")
            print(f"\nProfit Analysis (Position: ${self.position_size}):")
            print(f"  Gross Profit: ${opp['gross_profit']:.4f}")
            print(f"  Fees:         ${opp['total_fees']:.4f}")
            print(f"  NET PROFIT:   ${opp['net_profit']:.4f}")
            print(f"  ROI:          {opp['roi']:.2f}%")
            
            # Display AI analysis if available
            if 'ai_analysis' in opp and opp['ai_analysis']:
                print(f"\n🤖 AI Analysis (FunctionGemma):")
                print(f"  Overall Score:    {opp['ai_score']*100:.1f}/100")
                print(f"  Recommendation:   {opp['ai_recommendation']}")
                
                ai = opp['ai_analysis']
                if 'sentiment' in ai and ai['sentiment']:
                    sent = ai['sentiment']
                    print(f"  Sentiment:        {sent.get('sentiment_score', 0):.2f} (confidence: {sent.get('confidence', 0):.2f})")
                
                if 'mispricing' in ai and ai['mispricing']:
                    mis = ai['mispricing']
                    print(f"  Mispricing:       {mis.get('mispricing_likelihood', 0):.2f}")
                
                if 'risk' in ai and ai['risk']:
                    risk = ai['risk']
                    print(f"  Risk Score:       {risk.get('overall_risk', 0):.2f}")
                    if risk.get('risk_factors'):
                        print(f"  Risk Factors:     {', '.join(risk['risk_factors'][:2])}")
            
            print(f"{'='*90}\n")
    
    def run_continuous(self, interval_seconds: int = 900):
        """
        Run continuous scanning mode.
        
        Args:
            interval_seconds: Time between scans (default 900 = 15 minutes)
        """
        print(f"\n🔄 Starting continuous scanning mode...")
        print(f"   Position size: ${self.position_size}")
        print(f"   Min profit threshold: ${self.min_profit}")
        print(f"   Scan interval: {interval_seconds // 60} minutes\n")
        
        scan_count = 0
        
        try:
            while True:
                scan_count += 1
                print(f"\n{'#'*100}")
                print(f"SCAN #{scan_count}")
                print(f"{'#'*100}\n")
                
                # Perform scan
                opportunities = self.scan_once()
                
                # Display results
                self.display_opportunities(opportunities)
                
                # Wait for next scan
                print(f"⏰ Next scan in {interval_seconds // 60} minutes...")
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print(f"\n\n⏹️  Scanning stopped by user. Total scans: {scan_count}\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Cross-platform arbitrage scanner")
    parser.add_argument("--continuous", action="store_true", help="Run continuous scanning")
    parser.add_argument("--interval", type=int, default=900, help="Scan interval in seconds (default: 900)")
    parser.add_argument("--position-size", type=float, help="Override position size")
    parser.add_argument("--min-profit", type=float, help="Override min profit threshold")
    
    args = parser.parse_args()
    
    # Create scanner
    scanner = CrossPlatformScanner()
    
    # Override config if specified
    if args.position_size:
        scanner.position_size = args.position_size
    if args.min_profit:
        scanner.min_profit = args.min_profit
    
    # Run
    if args.continuous:
        scanner.run_continuous(interval_seconds=args.interval)
    else:
        # Single scan
        opportunities = scanner.scan_once()
        scanner.display_opportunities(opportunities)


if __name__ == "__main__":
    main()
