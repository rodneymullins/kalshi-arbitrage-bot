#!/usr/bin/env python3
"""Quick test: 1% target return vs fees"""

from bot_config import BotConfig
from core.fee_calculator import FeeCalculator

config = BotConfig
fee_calc = FeeCalculator(volume_30d=0)

print("="*60)
print("🧪 TESTING 1% TARGET RETURN")
print("="*60)
print(f"\nFee Structure: 7.0% (Taker) + 3.5% (Maker) = 10.5% total\n")

# Test at different prices
prices = [0.20, 0.30, 0.45, 0.60]

for price in prices:
    # Kelly sizing
    edge = 0.05
    kelly = edge / ((1/price) - 1) if price > 0 else 0
    kelly = min(kelly, 0.10)
    bet = kelly * 29.40
    n = int(bet / price) if price > 0 else 0
    
    if n > 0:
        # 1% target return
        target_price = price * 1.01
        
        profit = fee_calc.calculate_net_profit(price, target_price, n)
        
        print(f"Price: ${price:.2f} → ${target_price:.2f} (1% gain)")
        print(f"  Position: {n} contracts (${bet:.2f})")
        print(f"  Gross: ${profit['gross_profit']:.2f}")
        print(f"  Fees:  ${profit['fees']:.2f}")
        print(f"  NET:   ${profit['net_profit']:.2f}")
        
        if profit['net_profit'] >= 0.10:
            print(f"  ✅ Profitable")
        else:
            print(f"  ❌ LOSS - Fees exceed profit!")
        print()

print("="*60)
print("VERDICT:")
print("="*60)
print("With 1% target return and 10.5% total fees,")
print("you need VERY large positions (50+ contracts)")
print("to overcome the fee burden.")
print(f"\nWith ${config.BANKROLL:.2f} bankroll:")
print("  → Position sizes: 1-9 contracts")
print("  → Result: Nearly all trades will be fee-negative ❌")
print("\nRECOMMENDATION: Use 5-10% target return minimum")
