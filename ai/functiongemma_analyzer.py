"""
AI Sentiment Analyzer using FunctionGemma

FunctionGemma is optimal for this because:
1. Structured JSON output (perfect for scores/decisions)
2. Function calling (can trigger different analysis types)
3. Lightweight 270M params (extremely fast, <1s inference)
4. Optimized for metadata extraction
"""
import requests
import json
from typing import Dict, Optional

class FunctionGemmaAnalyzer:
    """
    Use FunctionGemma for fast, structured market analysis.
    
    FunctionGemma excels at:
    - Extracting structured data from market text
    - Generating consistent JSON outputs
    - Function calling for different analysis types
    - Fast inference (270M params)
    """
    
    def __init__(self, endpoint="http://192.168.1.176:11434/api/generate"):
        self.endpoint = endpoint
        self.model = "functiongemma:2b"  # Or gemma:2b if FunctionGemma not available
        
        # Define analysis functions for FunctionGemma
        self.functions = {
            "analyze_sentiment": {
                "description": "Analyze market sentiment and bias",
                "parameters": {
                    "market_text": "string",
                    "return": {
                        "sentiment_score": "float (-1 to 1)",
                        "confidence": "float (0 to 1)",
                        "bias_detected": "boolean",
                        "reasoning": "string"
                    }
                }
            },
            "detect_mispricing": {
                "description": "Identify potential mispricing signals",
                "parameters": {
                    "market_text": "string",
                    "return": {
                        "mispricing_likelihood": "float (0 to 1)",
                        "signals": "list of strings",
                        "confidence": "float (0 to 1)"
                    }
                }
            },
            "assess_risk": {
                "description": "Assess resolution and execution risks",
                "parameters": {
                    "kalshi_market": "string",
                    "polymarket_market": "string",
                    "match_confidence": "float",
                    "return": {
                        "resolution_risk": "float (0 to 1)",
                        "execution_risk": "float (0 to 1)",
                        "overall_risk": "float (0 to 1)",
                        "risk_factors": "list of strings"
                    }
                }
            }
        }
    
    def _call_function(self, function_name: str, **kwargs) -> Dict:
        """
        Call a FunctionGemma function with structured output.
        
        FunctionGemma is designed for this - it will return clean JSON.
        """
        func_def = self.functions.get(function_name)
        if not func_def:
            return {}
        
        # Build prompt for FunctionGemma
        prompt = f"""Function: {function_name}
Description: {func_def['description']}

Input:
{json.dumps(kwargs, indent=2)}

Expected output format:
{json.dumps(func_def['parameters']['return'], indent=2)}

Generate output as valid JSON:"""
        
        try:
            response = requests.post(
                self.endpoint,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",  # Force JSON output
                    "temperature": 0.3,  # Low temp for consistent outputs
                },
                timeout=10  # FunctionGemma is FAST
            )
            
            if response.status_code == 200:
                result = response.json()
                output_text = result.get("response", "{}")
                
                # Parse JSON
                try:
                    return json.loads(output_text)
                except json.JSONDecodeError:
                    # FunctionGemma should always return valid JSON
                    print(f"Warning: Invalid JSON from FunctionGemma: {output_text}")
                    return {}
            
        except Exception as e:
            print(f"Error calling FunctionGemma: {e}")
        
        return {}
    
    def analyze_sentiment(self, market_text: str) -> Dict:
        """
        Analyze sentiment using FunctionGemma.
        
        Returns:
            {
                "sentiment_score": float,      # -1.0 (bearish) to 1.0 (bullish)
                "confidence": float,           # 0.0 to 1.0
                "bias_detected": bool,         # True if political/emotional bias
                "reasoning": str               # Brief explanation
            }
        """
        return self._call_function("analyze_sentiment", market_text=market_text)
    
    def detect_mispricing(self, market_text: str, current_price: float = None) -> Dict:
        """
        Detect mispricing signals using FunctionGemma.
        
        Returns:
            {
                "mispricing_likelihood": float,  # 0.0 to 1.0
                "signals": list,                 # ["ambiguous wording", "time-sensitive", ...]
                "confidence": float              # 0.0 to 1.0
            }
        """
        input_data = {"market_text": market_text}
        if current_price:
            input_data["current_price"] = current_price
        
        return self._call_function("detect_mispricing", **input_data)
    
    def assess_risk(self, kalshi_market: str, polymarket_market: str, 
                    match_confidence: float) -> Dict:
        """
        Assess arbitrage risks using FunctionGemma.
        
        Returns:
            {
                "resolution_risk": float,      # Will markets resolve the same?
                "execution_risk": float,       # Will orders fill?
                "overall_risk": float,         # Combined risk score
                "risk_factors": list           # ["markets might resolve differently", ...]
            }
        """
        return self._call_function(
            "assess_risk",
            kalshi_market=kalshi_market,
            polymarket_market=polymarket_market,
            match_confidence=match_confidence
        )
    
    def analyze_opportunity(self, opportunity: Dict) -> Dict:
        """
        Comprehensive analysis of an arbitrage opportunity.
        
        Calls multiple FunctionGemma functions and combines results.
        """
        # 1. Sentiment analysis
        sentiment = self.analyze_sentiment(
            f"{opportunity['kalshi_market']} / {opportunity['polymarket_market']}"
        )
        
        # 2. Mispricing detection
        mispricing = self.detect_mispricing(
            opportunity['kalshi_market']
        )
        
        # 3. Risk assessment
        risk = self.assess_risk(
            opportunity['kalshi_market'],
            opportunity['polymarket_market'],
            opportunity.get('match_confidence', 0.5)
        )
        
        # 4. Combined AI score
        ai_score = self._calculate_combined_score(sentiment, mispricing, risk)
        
        return {
            "sentiment": sentiment,
            "mispricing": mispricing,
            "risk": risk,
            "ai_score": ai_score,
            "recommendation": self._get_recommendation(ai_score, risk)
        }
    
    def _calculate_combined_score(self, sentiment: Dict, mispricing: Dict, risk: Dict) -> float:
        """
        Combine FunctionGemma outputs into single score.
        
        Score interpretation:
        - 0.0 - 0.3: Skip (too risky or unlikely to profit)
        - 0.3 - 0.6: Marginal (watch, maybe execute)
        - 0.6 - 0.8: Good (likely execute)
        - 0.8 - 1.0: Excellent (definitely execute)
        """
        # Weight components
        mispricing_score = mispricing.get("mispricing_likelihood", 0.5) * 0.4
        sentiment_score = (sentiment.get("sentiment_score", 0) + 1) / 2 * 0.3  # Map -1,1 to 0,1
        risk_penalty = (1.0 - risk.get("overall_risk", 0.5)) * 0.3
        
        combined = mispricing_score + sentiment_score + risk_penalty
        
        return min(1.0, max(0.0, combined))
    
    def _get_recommendation(self, ai_score: float, risk: Dict) -> str:
        """Generate execution recommendation."""
        if ai_score >= 0.8 and risk.get("overall_risk", 1.0) < 0.3:
            return "EXECUTE - High confidence, low risk"
        elif ai_score >= 0.6:
            return "CONSIDER - Good opportunity, moderate risk"
        elif ai_score >= 0.3:
            return "MARGINAL - Watch for better conditions"
        else:
            return "SKIP - Insufficient edge or too risky"


# Quick test
if __name__ == "__main__":
    analyzer = FunctionGemmaAnalyzer()
    
    print("Testing FunctionGemma connection...")
    
    # Test sentiment
    result = analyzer.analyze_sentiment(
        "Will Bitcoin hit $100,000 by January 31, 2026?"
    )
    
    print("\nSentiment Analysis:")
    print(json.dumps(result, indent=2))
    
    # Test mispricing
    result = analyzer.detect_mispricing(
        "Will Trump deport more than 500,000 people in 2025?"
    )
    
    print("\nMispricing Detection:")
    print(json.dumps(result, indent=2))
