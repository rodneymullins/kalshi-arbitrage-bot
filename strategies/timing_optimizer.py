"""
Timing Optimizer for Kalshi Bot
Determines optimal execution timing for arbitrage opportunities
"""

from datetime import datetime, timedelta
import numpy as np
from typing import Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)

class TimingOptimizer:
    """Determine optimal moment to execute trade"""
    
    def __init__(self):
        self.model = None  # Placeholder for ML model
    
    def extract_features(self, opportunity: Dict, market_data: Dict) -> Dict:
        """Extract features for timing decision"""
        return {
            'spread': opportunity.get('spread', 0),
            'volume_last_hour': market_data.get('volume_1h', 0),
            'time_of_day': datetime.now().hour,
            'day_of_week': datetime.now().weekday(),
            'time_to_close': market_data.get('close_time_hours', 24),
            'orderbook_depth': len(market_data.get('orderbook', [])),
            'volatility_5min': market_data.get('volatility', 0),
            'trend': self.calculate_trend(market_data)
        }
    
    def calculate_trend(self, market_data: Dict) -> int:
        """Calculate price trend direction"""
        prices = market_data.get('recent_prices', [])
        if len(prices) < 2:
            return 0
        return 1 if prices[-1] > prices[0] else -1
    
    def predict_optimal_delay(self, opportunity: Dict, market_data: Dict) -> int:
        """
        Predict optimal delay in seconds before executing
        
        Returns:
            delay_seconds: 0 = execute now, 60 = wait 1 min, etc.
        """
        features = self.extract_features(opportunity, market_data)
        
        # Use rule-based timing (ML model placeholder)
        return self.rule_based_timing(features)
    
    def rule_based_timing(self, features: Dict) -> int:
        """Fallback rule-based timing logic"""
        delay = 0
        
        # Wide spread = wait for tightening
        if features['spread'] > 0.05:
            delay += 30
        
        # Low volume = wait for liquidity
        if features['volume_last_hour'] < 100:
            delay += 60
        
        # Off-peak hours = wait
        if features['time_of_day'] < 9 or features['time_of_day'] > 20:
            delay += 45
        
        # Close to expiry = act fast
        if features['time_to_close'] < 1:
            delay = 0
        
        # High volatility = wait for stability
        if features['volatility_5min'] > 0.10:
            delay += 30
        
        return min(delay, 300)  # Cap at 5 minutes
    
    def should_execute_now(self, opportunity: Dict, market_data: Dict) -> bool:
        """Binary decision: execute now or wait"""
        delay = self.predict_optimal_delay(opportunity, market_data)
        return delay == 0
    
    def get_execution_recommendation(self, opportunity: Dict, market_data: Dict) -> Dict:
        """Get detailed execution recommendation"""
        delay = self.predict_optimal_delay(opportunity, market_data)
        features = self.extract_features(opportunity, market_data)
        
        reasons = []
        if features['spread'] > 0.05:
            reasons.append(f"Wide spread ({features['spread']:.2%})")
        if features['volume_last_hour'] < 100:
            reasons.append(f"Low volume (${features['volume_last_hour']})")
        if features['time_of_day'] < 9 or features['time_of_day'] > 20:
            reasons.append(f"Off-peak hours ({features['time_of_day']}:00)")
        if features['volatility_5min'] > 0.10:
            reasons.append(f"High volatility ({features['volatility_5min']:.2%})")
        
        return {
            'execute_now': delay == 0,
            'recommended_delay_seconds': delay,
            'recommended_delay_human': f"{delay // 60}m {delay % 60}s" if delay > 0 else "Now",
            'confidence': 0.7,  # Placeholder
            'reasons': reasons if reasons else ['Optimal timing']
        }


if __name__ == "__main__":
    # Test the timing optimizer
    print("Timing Optimizer Test")
    print("=" * 60)
    
    optimizer = TimingOptimizer()
    
    # Example opportunity
    opportunity = {
        'spread': 0.03,
        'net_profit': 1.50
    }
    
    # Example market data
    market_data = {
        'volume_1h': 500,
        'close_time_hours': 12,
        'orderbook': [0.48, 0.49, 0.50, 0.51, 0.52],
        'volatility': 0.08,
        'recent_prices': [0.48, 0.49, 0.50]
    }
    
    recommendation = optimizer.get_execution_recommendation(opportunity, market_data)
    
    print(f"Execute Now: {recommendation['execute_now']}")
    print(f"Recommended Delay: {recommendation['recommended_delay_human']}")
    print(f"Confidence: {recommendation['confidence']:.0%}")
    print(f"Reasons: {', '.join(recommendation['reasons'])}")
