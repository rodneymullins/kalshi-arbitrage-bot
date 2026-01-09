#!/usr/bin/env python3
"""
Test Fee Integration - Verify bot makes correct decisions with fee calculator
"""

from bot_config import BotConfig
from core.fee_calculator import FeeCalculator

# Initialize
config = BotConfig
fee_calc = FeeCalculator(volume_30d=config.VOLUME_30D)

print("="*70)
print("🧪 FEE INTEGRATION TEST - Bot Decision Simulation")
print("="*70)
print(f"\nConfiguration:")
print(f"  Bankroll: ${config.BANKROLL:.2f}")
print(f"  Fee Tier: {config.get_fee_tier()}% (Taker) / {config.get_fee_tier()/2}% (Maker)")
print(f"  Min Net Profit: ${config.MIN_NET_PROFIT:.2f}")
print(f"  Target Return: {config.TARGET_RETURN_PCT}%\n")

# Test scenarios
test_cases = [
    # (price, description, expected_decision)
    (0.45, "Medium price, decent volume", "Should trade if position large enough"),
    (0.20, "Min price threshold", "Borderline - depends on quantity"),
    (0.15, "Below min price", "SKIP - below MIN_PRICE"),
    (0.75, "High price, low upside", "SKIP - limited profit potential"),
]

print("="*70)
print("TEST SCENARIOS")
print("="*70 + "\n")

for i, (price, description, expected) in enumerate(test_cases, 1):
    print(f"[{i}] {description}")
    print(f"    Market Price: ${price:.2f}")
    
    # Simulate Kelly calculation
    edge = config.EDGE
    kelly = edge / ((1/price) - 1) if price > 0 else 0
    kelly = min(kelly, config.MAX_KELLY_FRACTION)
    bet = kelly * config.BANKROLL
    n = int(bet / price) if price > 0 else 0
    
    print(f"    Kelly Bet: ${bet:.2f} → {n} contracts")
    
    if price < config.MIN_PRICE:
        print(f"    ❌ DECISION: SKIP (price ${price:.2f} < min ${config.MIN_PRICE:.2f})")
    elif n == 0:
        print(f"    ❌ DECISION: SKIP (position too small)")
    else:
        # Calculate profit with fees
        target_return_pct = config.TARGET_RETURN_PCT / 100
        target_sell_price = min(price * (1 + target_return_pct), 0.99)
        
        profit_analysis = fee_calc.calculate_net_profit(
            buy_price=price,
            sell_price=target_sell_price,
            quantity=n
        )
        
        gross_profit = profit_analysis['gross_profit']
        total_fees = profit_analysis['fees']
        net_profit = profit_analysis['net_profit']
        
        print(f"    Target Sell: ${target_sell_price:.2f} ({target_return_pct*100:.0f}% return)")
        print(f"    Gross Profit: ${gross_profit:.2f}")
        print(f"    Fees: ${total_fees:.2f}")
        print(f"    Net Profit: ${net_profit:.2f}")
        
        if net_profit >= config.MIN_NET_PROFIT:
            print(f"    ✅ DECISION: TRADE (net ${net_profit:.2f} > min ${config.MIN_NET_PROFIT:.2f})")
        else:
            print(f"    ❌ DECISION: SKIP (net ${net_profit:.2f} < min ${config.MIN_NET_PROFIT:.2f})")
    
    print(f"    Expected: {expected}\n")

print("="*70)
print("SUMMARY")
print("="*70)
print("The bot will only trade when:")
print("  1. Price >= $0.20 (MIN_PRICE)")
print("  2. Position size > 0 (Kelly calculation)")
print("  3. Net profit after fees >= $0.50 (MIN_NET_PROFIT)")
print("\nThis prevents fee-negative trades and ensures profitability! ✅")
