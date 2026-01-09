"""
Win Probability Model for Kalshi Markets
More sophisticated than simple market price assumption
"""

import requests
import os
from datetime import datetime, timedelta
from typing import Dict, Optional


class WinProbabilityModel:
    """
    Estimates true win probability vs market price
    Considers: market efficiency, time to expiry, volume, historical accuracy
    """
    
    def __init__(self, kalshi_client):
        self.kalshi = kalshi_client
        self.market_cache = {}
        
    def get_market_details(self, ticker: str) -> Optional[Dict]:
        """Fetch market metadata"""
        if ticker in self.market_cache:
            return self.market_cache[ticker]
        
        ts = str(int(datetime.now().timestamp() * 1000))
        path = f"/markets/{ticker}"
        headers = {
            "KALSHI-ACCESS-KEY": self.kalshi.key_id,
            "KALSHI-ACCESS-SIGNATURE": self.kalshi.sign_request("GET", path, ts),
            "KALSHI-ACCESS-TIMESTAMP": ts
        }
        
        try:
            resp = requests.get(f"{self.kalshi.api_base}{path}", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                self.market_cache[ticker] = data.get('market', {})
                return self.market_cache[ticker]
        except Exception as e:
            print(f"Error fetching market details: {e}")
        
        return None
    
    def get_volume_factor(self, ticker: str) -> float:
        """
        Higher volume = more efficient pricing
        Returns: 0.0 (low confidence) to 1.0 (high confidence in market price)
        """
        details = self.get_market_details(ticker)
        if not details:
            return 0.5  # Medium confidence by default
        
        volume = details.get('volume', 0)
        
        # Volume thresholds (adjust based on observed Kalshi volumes)
        if volume > 10000:
            return 0.95  # Very high confidence
        elif volume > 5000:
            return 0.85  # High confidence
        elif volume > 1000:
            return 0.70  # Medium-high confidence
        elif volume > 100:
            return 0.50  # Medium confidence
        else:
            return 0.30  # Low confidence - market may be mispriced
    
    def get_time_decay_factor(self, ticker: str) -> float:
        """
        Markets closer to expiry are more efficient
        Returns: 0.0 (far away) to 1.0 (imminent)
        """
        details = self.get_market_details(ticker)
        if not details:
            return 0.5
        
        close_time_str = details.get('close_time')
        if not close_time_str:
            return 0.5
        
        try:
            # Parse ISO timestamp
            close_time = datetime.fromisoformat(close_time_str.replace('Z', '+00:00'))
            now = datetime.now(close_time.tzinfo)
            
            hours_remaining = (close_time - now).total_seconds() / 3600
            
            # Efficiency increases as expiry approaches
            if hours_remaining < 24:
                return 0.95  # Very efficient
            elif hours_remaining < 72:
                return 0.85  # High efficiency
            elif hours_remaining < 168:  # 1 week
                return 0.70  # Medium-high
            elif hours_remaining < 720:  # 1 month
                return 0.50  # Medium
            else:
                return 0.30  # Low efficiency - far out markets
        except Exception as e:
            print(f"Error parsing time: {e}")
            return 0.5
    
    def estimate_win_probability(self, ticker: str, market_price: float) -> Dict:
        """
        Main estimation function
        
        Returns:
            {
                'win_prob': float,  # Estimated true probability
                'confidence': float,  # How confident we are (0-1)
                'edge': float,  # Estimated edge vs market
                'reasoning': str  # Explanation
            }
        """
        if market_price <= 0 or market_price >= 1:
            return {
                'win_prob': market_price,
                'confidence': 0.0,
                'edge': 0.0,
                'reasoning': 'Invalid market price'
            }
        
        # Get market factors
        volume_factor = self.get_volume_factor(ticker)
        time_factor = self.get_time_decay_factor(ticker)
        
        # Combined market efficiency
        market_efficiency = (volume_factor + time_factor) / 2
        
        # Base assumption: markets are ~80-90% efficient on average
        # Less efficient markets may have mispricing
        inefficiency = 1.0 - market_efficiency
        
        # Detect potential mispricing patterns
        mispricing_adjustment = 0.0
        reasoning_parts = []
        
        # 1. Extreme prices often mean-revert
        if market_price < 0.10:
            mispricing_adjustment = 0.03 * inefficiency  # Slight upward bias
            reasoning_parts.append("Low price may be undervalued")
        elif market_price > 0.90:
            mispricing_adjustment = -0.03 * inefficiency  # Slight downward bias
            reasoning_parts.append("High price may be overvalued")
        
        # 2. Mid-range prices (0.40-0.60) are often efficient
        elif 0.40 <= market_price <= 0.60:
            mispricing_adjustment = 0.0
            reasoning_parts.append("Fair value range")
        
        # 3. Low volume + far expiry = potential for larger mispricing
        if volume_factor < 0.5 and time_factor < 0.5:
            # Allow for larger potential edge in illiquid, far-dated markets
            mispricing_adjustment *= 2
            reasoning_parts.append("Low liquidity allows larger edges")
        
        # Calculate estimated true probability
        estimated_prob = market_price + mispricing_adjustment
        estimated_prob = max(0.01, min(0.99, estimated_prob))  # Clamp to valid range
        
        edge = estimated_prob - market_price
        
        # Confidence is based on market efficiency
        confidence = market_efficiency
        
        # Build reasoning string
        reasoning = f"Market: ${market_price:.2f} | Vol factor: {volume_factor:.2f} | " \
                   f"Time factor: {time_factor:.2f} | {', '.join(reasoning_parts)}"
        
        return {
            'win_prob': estimated_prob,
            'confidence': confidence,
            'edge': edge,
            'reasoning': reasoning
        }


# Example usage
if __name__ == "__main__":
    from bot_enhanced import KalshiClient
    
    print("🧠 Win Probability Model Test\n")
    
    kalshi = KalshiClient()
    model = WinProbabilityModel(kalshi)
    
    # Test with KXELONMARS-99
    ticker = "KXELONMARS-99"
    market_price = kalshi.get_price(ticker)
    
    if market_price > 0:
        result = model.estimate_win_probability(ticker, market_price)
        
        print(f"Market: {ticker}")
        print(f"Market Price: ${market_price:.2f}")
        print(f"Estimated Win Prob: {result['win_prob']:.1%}")
        print(f"Edge: {result['edge']:+.1%}")
        print(f"Confidence: {result['confidence']:.1%}")
        print(f"Reasoning: {result['reasoning']}")
        
        if abs(result['edge']) >= 0.05:
            print(f"\n✅ TRADEABLE: Edge {result['edge']:+.1%} exceeds 5% threshold")
        else:
            print(f"\n⏸️  NO TRADE: Edge {result['edge']:+.1%} below threshold")
