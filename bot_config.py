#!/usr/bin/env python3
"""
Kalshi Bot Configuration
Centralized settings for trading parameters, risk management, and execution modes
"""

import os
from dotenv import load_dotenv

load_dotenv()


class BotConfig:
    """Centralized bot configuration"""
    
    # ========================
    # Trading Mode
    # ========================
    MODE = os.getenv("BOT_MODE", "DRY")  # DRY, LIVE, BACKTEST
    
    # ========================
    # Financial Parameters
    # ========================
    BANKROLL = float(os.getenv("BANKROLL", "29.40"))
    VOLUME_30D = float(os.getenv("VOLUME_30D", "0"))  # Affects fee tier
    
    # ========================
    # Trading Thresholds
    # ========================
    MIN_VOLUME = int(os.getenv("MIN_VOLUME", "1000"))  # Minimum market volume ($)
    MIN_PRICE = float(os.getenv("MIN_PRICE", "0.20"))  # Minimum price ($)
    MIN_NET_PROFIT = float(os.getenv("MIN_NET_PROFIT", "0.50"))  # After fees ($)
    
    # ========================
    # Strategy Parameters
    # ========================
    EDGE = float(os.getenv("EDGE", "0.05"))  # Expected edge (5%)
    MAX_KELLY_FRACTION = float(os.getenv("MAX_KELLY_FRACTION", "0.10"))  # Max 10% of bankroll
    TARGET_RETURN_PCT = float(os.getenv("TARGET_RETURN_PCT", "10"))  # Target return (10%)
    
    # ========================
    # Risk Management
    # ========================
    MAX_CONSECUTIVE_LOSSES = int(os.getenv("MAX_CONSECUTIVE_LOSSES", "3"))
    CHECK_INTERVAL_SEC = int(os.getenv("CHECK_INTERVAL_SEC", "10"))
    MAX_NO_PRICE_COUNT = int(os.getenv("MAX_NO_PRICE_COUNT", "30"))  # 5 min at 10s intervals
    
    @classmethod
    def print_config(cls):
        """Display current configuration"""
        print(f"\n{'='*60}")
        print(f"🤖 KALSHI BOT CONFIGURATION")
        print(f"{'='*60}")
        print(f"Mode:              {cls.MODE}")
        print(f"Bankroll:          ${cls.BANKROLL:.2f}")
        print(f"30-day Volume:     ${cls.VOLUME_30D:,.2f}")
        print(f"")
        print(f"Trading Thresholds:")
        print(f"  Min Market Vol:  ${cls.MIN_VOLUME:,}")
        print(f"  Min Price:       ${cls.MIN_PRICE:.2f}")
        print(f"  Min Net Profit:  ${cls.MIN_NET_PROFIT:.2f}")
        print(f"")
        print(f"Strategy:")
        print(f"  Edge Target:     {cls.EDGE*100:.0f}%")
        print(f"  Max Kelly:       {cls.MAX_KELLY_FRACTION*100:.0f}%")
        print(f"  Target Return:   {cls.TARGET_RETURN_PCT:.0f}%")
        print(f"")
        print(f"Risk Management:")
        print(f"  Max Losses:      {cls.MAX_CONSECUTIVE_LOSSES}")
        print(f"  Check Interval:  {cls.CHECK_INTERVAL_SEC}s")
        print(f"{'='*60}\n")
    
    @classmethod
    def validate(cls):
        """Validate configuration and return any warnings"""
        warnings = []
        
        if cls.MODE not in ["DRY", "LIVE", "BACKTEST"]:
            warnings.append(f"⚠️  Invalid MODE: {cls.MODE} (should be DRY, LIVE, or BACKTEST)")
        
        if cls.BANKROLL <= 0:
            warnings.append(f"⚠️  Invalid BANKROLL: ${cls.BANKROLL:.2f} (must be > 0)")
        
        if cls.MIN_NET_PROFIT < 0.10:
            warnings.append(f"⚠️  MIN_NET_PROFIT very low: ${cls.MIN_NET_PROFIT:.2f} (fees may eat profit)")
        
        if cls.MAX_KELLY_FRACTION > 0.25:
            warnings.append(f"⚠️  MAX_KELLY_FRACTION high: {cls.MAX_KELLY_FRACTION*100:.0f}% (risky)")
        
        return warnings
    
    @classmethod
    def get_fee_tier(cls):
        """Return current fee tier percentage"""
        if cls.VOLUME_30D >= 25000:
            return 3.5
        elif cls.VOLUME_30D >= 10000:
            return 4.5
        elif cls.VOLUME_30D >= 2500:
            return 5.5
        else:
            return 7.0


if __name__ == "__main__":
    # Display and validate configuration
    BotConfig.print_config()
    
    warnings = BotConfig.validate()
    if warnings:
        print("Configuration Warnings:")
        for warning in warnings:
            print(f"  {warning}")
        print()
    else:
        print("✅ Configuration valid\n")
    
    print(f"Current Fee Tier: {BotConfig.get_fee_tier()}%")
    print(f"  (Taker: {BotConfig.get_fee_tier()}%, Maker: {BotConfig.get_fee_tier()/2}%)\n")
