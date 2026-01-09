#!/usr/bin/env python3
"""
Kalshi Fee Calculator - Accurate fee calculation based on tiered structure
Based on research from vladmeer/kalshi-arbitrage-bot
"""

class FeeCalculator:
    """
    Calculate trading fees on Kalshi with tiered structure
    
    Fee Structure (as of Jan 2026):
    - Volume >= $25,000: 3.5%
    - Volume >= $10,000: 4.5%
    - Volume >= $2,500:  5.5%
    - Volume < $2,500:   7.0% (default)
    
    Maker orders (limit orders): 50% discount
    Taker orders (market orders): Full fee
    """
    
    def __init__(self, volume_30d=0):
        """
        Initialize fee calculator
        
        Args:
            volume_30d: 30-day trading volume in dollars
        """
        self.volume_30d = volume_30d
        self.base_fee_rate = self._get_base_fee_rate()
    
    def _get_base_fee_rate(self):
        """Get base fee rate based on 30-day volume"""
        if self.volume_30d >= 25000:
            return 0.035  # 3.5%
        elif self.volume_30d >= 10000:
            return 0.045  # 4.5%
        elif self.volume_30d >= 2500:
            return 0.055  # 5.5%
        else:
            return 0.07   # 7.0% (default for new traders)
    
    def calculate_trade_fee(self, price, quantity, is_maker=False):
        """
        Calculate fee for a single trade
        
        Args:
            price: Contract price (0.0 to 1.0)
            quantity: Number of contracts
            is_maker: True for limit orders (50% discount), False for market orders
        
        Returns:
            float: Total fee in dollars
        
        Note: Fees are charged on the PAYOUT, not the cost!
        """
        fee_rate = self.base_fee_rate
        
        if is_maker:
            fee_rate = fee_rate * 0.5  # 50% discount for makers
        
        # Fee is on $1.00 payout if contract wins
        max_payout = quantity * 1.00
        fee = max_payout * fee_rate
        
        return fee
    
    def calculate_round_trip_fee(self, buy_price, sell_price, quantity):
        """
        Calculate total fees for a complete trade (buy + sell)
        
        Args:
            buy_price: Entry price (0.0 to 1.0)
            sell_price: Exit price (0.0 to 1.0)
            quantity: Number of contracts
        
        Returns:
            dict: Breakdown of fees
        """
        # Assume buy is taker (market order), sell is maker (limit order)
        buy_fee = self.calculate_trade_fee(buy_price, quantity, is_maker=False)
        sell_fee = self.calculate_trade_fee(sell_price, quantity, is_maker=True)
        
        return {
            'buy_fee': buy_fee,
            'sell_fee': sell_fee,
            'total_fees': buy_fee + sell_fee,
            'fee_rate_buy': self.base_fee_rate,
            'fee_rate_sell': self.base_fee_rate * 0.5
        }
    
    def calculate_net_profit(self, buy_price, sell_price, quantity):
        """
        Calculate net profit after fees
        
        Args:
            buy_price: Entry price (0.0 to 1.0)
            sell_price: Exit price (0.0 to 1.0)
            quantity: Number of contracts
        
        Returns:
            dict: Profit breakdown
        """
        cost = buy_price * quantity
        revenue = sell_price * quantity
        gross_profit = revenue - cost
        
        fees = self.calculate_round_trip_fee(buy_price, sell_price, quantity)
        total_fees = fees['total_fees']
        
        net_profit = gross_profit - total_fees
        
        return {
            'cost': cost,
            'revenue': revenue,
            'gross_profit': gross_profit,
            'fees': total_fees,
            'net_profit': net_profit,
            'fee_breakdown': fees
        }
    
    def calculate_arbitrage_profit(self, yes_price, no_price, quantity):
        """
        Calculate profit from probability arbitrage (YES + NO != 100%)
        
        Args:
            yes_price: YES contract price
            no_price: NO contract price  
            quantity: Number of contracts for each side
        
        Returns:
            dict: Arbitrage opportunity details
        """
        # Total cost to buy both sides
        total_cost = (yes_price + no_price) * quantity
        
        # One side will pay out $1.00 per contract
        guaranteed_payout = quantity * 1.00
        
        # Calculate fees for both sides (both are buys, so taker fees)
        yes_fee = self.calculate_trade_fee(yes_price, quantity, is_maker=False)
        no_fee = self.calculate_trade_fee(no_price, quantity, is_maker=False)
        total_fees = yes_fee + no_fee
        
        # Net profit
        gross_profit = guaranteed_payout - total_cost
        net_profit = gross_profit - total_fees
        
        # Deviation from fair price
        total_probability = yes_price + no_price
        deviation = total_probability - 1.0
        
        return {
            'total_cost': total_cost,
            'guaranteed_payout': guaranteed_payout,
            'gross_profit': gross_profit,
            'total_fees': total_fees,
            'net_profit': net_profit,
            'total_probability': total_probability,
            'deviation_pct': deviation * 100,
            'is_profitable': net_profit > 0
        }
    
    def update_volume(self, new_volume_30d):
        """Update 30-day volume and recalculate fee rate"""
        self.volume_30d = new_volume_30d
        self.base_fee_rate = self._get_base_fee_rate()


if __name__ == "__main__":
    # Example usage
    calc = FeeCalculator(volume_30d=0)  # New trader, 7% fees
    
    print("=== KALSHI FEE CALCULATOR ===\n")
    print(f"30-day volume: ${calc.volume_30d:,.2f}")
    print(f"Base fee rate: {calc.base_fee_rate * 100:.1f}%\n")
    
    # Example 1: Simple trade
    print("Example 1: Buy at 45¢, sell at 50¢, 10 contracts")
    profit = calc.calculate_net_profit(0.45, 0.50, 10)
    print(f"  Cost: ${profit['cost']:.2f}")
    print(f"  Revenue: ${profit['revenue']:.2f}")
    print(f"  Gross profit: ${profit['gross_profit']:.2f}")
    print(f"  Fees: ${profit['fees']:.2f}")
    print(f"  Net profit: ${profit['net_profit']:.2f}\n")
    
    # Example 2: Probability arbitrage
    print("Example 2: YES @ 52¢, NO @ 50¢, 100 contracts")
    arb = calc.calculate_arbitrage_profit(0.52, 0.50, 100)
    print(f"  Total probability: {arb['total_probability']*100:.1f}% (should be 100%)")
    print(f"  Deviation: {arb['deviation_pct']:.2f}%")
    print(f"  Total cost: ${arb['total_cost']:.2f}")
    print(f"  Guaranteed payout: ${arb['guaranteed_payout']:.2f}")
    print(f"  Gross profit: ${arb['gross_profit']:.2f}")
    print(f"  Fees: ${arb['total_fees']:.2f}")
    print(f"  Net profit: ${arb['net_profit']:.2f}")
    print(f"  Profitable: {arb['is_profitable']}")
