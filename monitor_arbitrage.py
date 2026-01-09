#!/usr/bin/env python3
"""
Continuous Probability Arbitrage Monitor
Runs in a loop, scanning for YES+NO price mismatches every 30 seconds
"""

import time
import sys
from datetime import datetime

sys.path.insert(0, '/Users/rod/Antigravity/kalshi_bot')
from strategies.probability_arb import ProbabilityArbitrageDetector

def main():
    print("="*70)
    print("🔄 CONTINUOUS PROBABILITY ARBITRAGE MONITOR")
    print("="*70)
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Press Ctrl+C to stop\n")
    
    # Initialize detector with aggressive settings
    detector = ProbabilityArbitrageDetector(
        min_deviation_pct=0.5,  # Look for 0.5%+ deviations (aggressive)
        volume_30d=0  # New trader fees
    )
    
    scan_count = 0
    total_opportunities = 0
    
    while True:
        try:
            scan_count += 1
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            print(f"[{timestamp}] Scan #{scan_count}: Checking markets...")
            
            # Find opportunities
            opportunities = detector.find_opportunities(
                min_volume=100,  # Very low volume filter for more opportunities
                max_days_to_expiration=365
            )
            
            if opportunities:
                print(f"\n{'='*70}")
                print(f"🎯 FOUND {len(opportunities)} OPPORTUNITIES!")
                print(f"{'='*70}\n")
                
                detector.print_opportunities(opportunities)
                
                total_opportunities += len(opportunities)
                
                print(f"\n💡 Best opportunity:")
                best = opportunities[0]
                print(f"   {best['title'][:60]}")
                print(f"   Net Profit: ${best['arb_result']['net_profit']:.2f}")
                print(f"   Total Cost: ${best['arb_result']['total_cost']:.2f}")
                print(f"   Deviation: {best['deviation_pct']:.2f}%")
                
                print(f"\n🔔 ALERT: Profitable arbitrage detected!")
                print(f"   Review the opportunity above and execute manually if desired.")
                
            else:
                print(f"   No opportunities (markets efficient)")
            
            print(f"\n   Total found today: {total_opportunities}")
            print(f"   Next scan in 30 seconds...\n")
            
            time.sleep(30)
            
        except KeyboardInterrupt:
            print(f"\n\n{'='*70}")
            print(f"Monitor stopped by user")
            print(f"Total scans: {scan_count}")
            print(f"Total opportunities found: {total_opportunities}")
            print(f"{'='*70}\n")
            break
        except Exception as e:
            print(f"   Error: {e}")
            print(f"   Retrying in 30 seconds...")
            time.sleep(30)

if __name__ == "__main__":
    main()
