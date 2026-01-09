"""
Cross-Platform Configuration

Add Polymarket settings to existing bot configuration.
"""

# ... (keep all existing Kalshi config) ...

# Polymarket Configuration
POLYMARKET = {
    "api_base": "https://clob.polymarket.com",
    "gamma_api": "https://gamma-api.polymarket.com",
    "rate_limit_delay": 0.5,  # seconds between requests
    "timeout": 10,
    "min_liquidity": 100,  # minimum $100 liquidity
}

# Cross-Platform Arbitrage Settings
CROSS_PLATFORM = {
    "position_size": 5.0,  # $5 per arbitrage trade
    "min_profit_threshold": 0.02,  # $0.02 minimum profit
    "max_position_per_platform": 10,  # max contracts per side
    "match_confidence_threshold": 0.75,  # 75% confidence for auto-match
    "enable_auto_matching": False,  # manual review by default
    "scan_interval": 900,  # 15 minutes in seconds
    "alert_only": True,  # no auto-execution
}

# Polymarket Fee Structure (simpler than Kalshi)
POLYMARKET_FEES = {
    "trading_fee_rate": 0.02,  # 2% on profits
    "gas_fee_estimate": 0.01,  # ~$0.01 per trade (Polygon is cheap)
}
