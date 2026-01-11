"""
Kelly Criterion Position Sizing
Calculate optimal bet size using Kelly Criterion formula
"""

def calculate_kelly_bet(
    win_probability: float,
    market_price: float,
    bankroll: float,
    max_fraction: float = 0.25,
    edge: float = 0.05
) -> float:
    """
    Calculate optimal bet size using Kelly Criterion
    
    Args:
        win_probability: Estimated probability of winning (0-1)
        market_price: Current market price
        bankroll: Total available bankroll
        max_fraction: Maximum fraction of bankroll to bet (default 0.25)
        edge: Estimated edge over market (default 0.05)
    
    Returns:
        Bet size in dollars
    """
    # Kelly formula: f* = (bp - q) / b
    # where: f* = fraction to bet, b = odds, p = win probability, q = 1-p
    
    if market_price <= 0 or market_price >= 1:
        return 0
    
    odds = (1/market_price) - 1
    kelly_fraction = edge / odds
    
    # Apply maximum fraction cap (conservative Kelly)
    kelly_fraction = min(kelly_fraction, max_fraction)
   
    # Never bet negative amounts
    kelly_fraction = max(kelly_fraction, 0)
    
    return kelly_fraction * bankroll


def calculate_win_probability(market_price: float, edge: float) -> float:
    """
    Estimate win probability given market price and edge
    
    Args:
        market_price: Current market price
        edge: Estimated edge (e.g., 0.05 for 5%)
    
    Returns:
        Estimated win probability
    """
    # Simple model: assume edge represents mispricing
    # True probability = market_price + edge
    return min(market_price + edge, 0.99)

    
    return min(market_price + edge, 0.99)


def get_kelly_fraction(edge: float, market_price: float, max_fraction: float = 0.25) -> float:
    """Compatibility wrapper for bot_v3.py"""
    win_prob = calculate_win_probability(market_price, edge)
    # Calculate bet size for $1 bankroll to get fraction
    bet = calculate_kelly_bet(win_prob, market_price, 1.0, max_fraction, edge)
    return bet

def get_bet_size(edge: float, market_price: float, bankroll: float, max_fraction: float = 0.25) -> float:
    """Compatibility wrapper for bot_v3.py"""
    win_prob = calculate_win_probability(market_price, edge)
    return calculate_kelly_bet(win_prob, market_price, bankroll, max_fraction, edge)


if __name__ == "__main__":
    # Test the Kelly calculator
    print("Kelly Criterion Calculator Test")
    print("=" * 50)
    
    # Example: $1000 bankroll, 50 cent market, 5% edge
    bankroll = 1000
    market_price = 0.50
    edge = 0.05
    
    win_prob = calculate_win_probability(market_price, edge)
    bet = calculate_kelly_bet(win_prob, market_price, bankroll, 0.25, edge)
    
    print(f"Bankroll: ${bankroll}")
    print(f"Market Price: ${market_price:.2f}")
    print(f"Edge: {edge:.0%}")
    print(f"Win Probability: {win_prob:.0%}")
    print(f"Kelly Bet Size: ${bet:.2f}")
    print(f"Fraction of Bankroll: {(bet/bankroll):.0%}")
