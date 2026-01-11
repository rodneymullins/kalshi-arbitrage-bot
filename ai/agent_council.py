"""
Agent Council for Kalshi Bot - Phase 6
Multiple specialized agents vote on trade execution
"""

from enum import Enum
from typing import Dict, List, Optional

class Vote(Enum):
    STRONG_YES = 2
    YES = 1
    ABSTAIN = 0
    NO = -1
    STRONG_NO = -2


class RiskAgent:
    """Evaluates risk of execution"""
    weight = 1.5
    
    def vote(self, opportunity: Dict, market_data: Dict, bot_state: Dict) -> Vote:
        # Check circuit breaker status
        if bot_state.get('consecutive_losses', 0) >= 2:
            return Vote.STRONG_NO
        
        # Check position concentration
        if opportunity.get('market_category') == bot_state.get('last_category'):
            return Vote.NO  # Avoid concentration
        
        # Check volatility
        if market_data.get('volatility', 0) > 0.15:
            return Vote.NO
        
        return Vote.YES


class ValueAgent:
    """Evaluates profit potential"""
    weight = 2.0
    
    def vote(self, opportunity: Dict, market_data: Dict, bot_state: Dict) -> Vote:
        profit = opportunity.get('net_profit', 0)
        
        if profit > 0.20:
            return Vote.STRONG_YES
        elif profit > 0.10:
            return Vote.YES
        elif profit < 0.03:
            return Vote.STRONG_NO
        else:
            return Vote.ABSTAIN


class TimingAgent:
    """Evaluates market timing"""
    weight = 1.0
    
    def vote(self, opportunity: Dict, market_data: Dict, bot_state: Dict) -> Vote:
        # Simple timing check without import
        spread = opportunity.get('spread', 0)
        volatility = market_data.get('volatility', 0)
        
        # Fast execution if good conditions
        if spread < 0.03 and volatility < 0.10:
            return Vote.YES
        elif spread > 0.05 or volatility > 0.15:
            return Vote.NO
        else:
            return Vote.ABSTAIN


class SentimentAgent:
    """Evaluates AI sentiment analysis"""
    weight = 1.2
    
    def vote(self, opportunity: Dict, market_data: Dict, bot_state: Dict) -> Vote:
        # Use existing FunctionGemma analysis if available
        ai_score = opportunity.get('ai_score', 0.5)
        
        if ai_score > 0.75:
            return Vote.STRONG_YES
        elif ai_score > 0.60:
            return Vote.YES
        elif ai_score < 0.40:
            return Vote.NO
        else:
            return Vote.ABSTAIN


class AgentCouncil:
    """Coordinate multi-agent voting"""
    
    def __init__(self):
        self.agents = [
            RiskAgent(),
            ValueAgent(),
            TimingAgent(),
            SentimentAgent()
        ]
    
    def decide(self, opportunity: Dict, market_data: Dict, bot_state: Dict) -> Dict:
        """
        Get collective decision from all agents
        
        Returns:
            decision: bool (execute or not)
            confidence: float (0-1)
            breakdown: dict (individual votes)
        """
        votes = {}
        weighted_sum = 0
        total_weight = 0
        
        for agent in self.agents:
            vote = agent.vote(opportunity, market_data, bot_state)
            votes[agent.__class__.__name__] = vote.name
            
            weighted_sum += vote.value * agent.weight
            total_weight += agent.weight
        
        # Calculate weighted average
        score = weighted_sum / total_weight
        
        # Decision threshold
        execute = score > 0.5
        confidence = abs(score) / 2.0  # Normalize to 0-1
        
        return {
            'execute': execute,
            'confidence': confidence,
            'votes': votes,
            'weighted_score': round(score, 2)
        }


if __name__ == "__main__":
    # Test the agent council
    print("Agent Council Test")
    print("=" * 60)
    
    council = AgentCouncil()
    
    # Example opportunity
    opportunity = {
        'net_profit': 0.15,
        'ai_score': 0.70,
        'market_category': 'politics'
    }
    
    # Example market data
    market_data = {
        'volatility': 0.08,
        'volume_1h': 500,
        'close_time_hours': 12
    }
    
    # Bot state
    bot_state = {
        'consecutive_losses': 0,
        'last_category': 'sports'
    }
    
    decision = council.decide(opportunity, market_data, bot_state)
    
    print(f"Execute: {decision['execute']}")
    print(f"Confidence: {decision['confidence']:.0%}")
    print(f"Weighted Score: {decision['weighted_score']}")
    print(f"\nAgent Votes:")
    for agent, vote in decision['votes'].items():
        print(f"  {agent}: {vote}")
