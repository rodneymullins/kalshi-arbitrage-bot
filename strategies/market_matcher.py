"""
Market Matcher

Matches equivalent markets across Kalshi and Polymarket platforms.
Uses fuzzy text matching and manual overrides.
"""
import json
import os
from typing import Dict, List, Optional, Tuple
from fuzzywuzzy import fuzz
from datetime import datetime, timedelta


class MarketMatcher:
    """Match markets across Kalshi and Polymarket."""
    
    def __init__(self, override_file: str = "config/market_matches.json"):
        """
        Initialize market matcher.
        
        Args:
            override_file: Path to manual market pair overrides
        """
        self.override_file = override_file
        self.manual_matches = self._load_manual_matches()
    
    def _load_manual_matches(self) -> Dict:
        """Load manual market pair overrides from JSON file."""
        if os.path.exists(self.override_file):
            try:
                with open(self.override_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading manual matches: {e}")
        
        return {}
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching."""
        return text.lower().strip().replace("?", "").replace("!", "")
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from market text."""
        # Remove common words
        stop_words = {"will", "the", "a", "an", "in", "on", "at", "to", "by", "for"}
        
        words = self._normalize_text(text).split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords
    
    def _calculate_match_score(self, kalshi_market: Dict, poly_market: Dict) -> float:
        """
        Calculate match confidence score (0.0 to 1.0).
        
        Args:
            kalshi_market: Kalshi market dict
            poly_market: Polymarket market dict
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        k_title = kalshi_market.get("title", "")
        p_question = poly_market.get("question", "")
        
        # Overall text similarity
        overall_score = fuzz.ratio(
            self._normalize_text(k_title),
            self._normalize_text(p_question)
        ) / 100.0
        
        # Keyword overlap
        k_keywords = set(self._extract_keywords(k_title))
        p_keywords = set(self._extract_keywords(p_question))
        
        if k_keywords and p_keywords:
            keyword_overlap = len(k_keywords & p_keywords) / len(k_keywords | p_keywords)
        else:
            keyword_overlap = 0.0
        
        # Time proximity (closer expiration = higher confidence match)
        time_score = self._calculate_time_proximity(kalshi_market, poly_market)
        
        # Weighted average
        final_score = (
            overall_score * 0.5 +
            keyword_overlap * 0.35 +
            time_score * 0.15
        )
        
        return min(1.0, final_score)
    
    def _calculate_time_proximity(self, kalshi_market: Dict, poly_market: Dict) -> float:
        """
        Calculate time proximity score.
        
        Markets with similar expiration times are more likely to be matches.
        """
        try:
            k_close = kalshi_market.get("close_time", "")
            p_close = poly_market.get("end_date", "")
            
            if not k_close or not p_close:
                return 0.5  # neutral if time missing
            
            k_time = datetime.fromisoformat(k_close.replace('Z', '+00:00'))
            p_time = datetime.fromisoformat(p_close.replace('Z', '+00:00'))
            
            time_diff = abs((k_time - p_time).total_seconds())
            
            # Within 1 day = 1.0, 1 week = 0.5, 1 month+ = 0.0
            if time_diff < 86400:  # 1 day
                return 1.0
            elif time_diff < 604800:  # 1 week
                return 0.7
            elif time_diff < 2592000:  # 30 days
                return 0.3
            else:
                return 0.0
        
        except Exception:
            return 0.5
    
    def find_match(self, kalshi_market: Dict, polymarket_markets: List[Dict],
                   min_confidence: float = 0.75) -> Optional[Tuple[Dict, float]]:
        """
        Find matching Polymarket market for a Kalshi market.
        
        Args:
            kalshi_market: Kalshi market dictionary
            polymarket_markets: List of Polymarket markets
            min_confidence: Minimum confidence threshold (0.0 to 1.0)
            
        Returns:
            Tuple of (matched_market, confidence_score) or None
        """
        # Check manual overrides first
        k_ticker = kalshi_market.get("ticker", "")
        if k_ticker in self.manual_matches:
            condition_id = self.manual_matches[k_ticker]
            
            for pm_market in polymarket_markets:
                if pm_market.get("condition_id") == condition_id:
                    return (pm_market, 1.0)  # Manual override = 100% confidence
        
        # Find best match
        best_match = None
        best_score = 0.0
        
        for pm_market in polymarket_markets:
            # Skip closed markets
            if pm_market.get("closed", False):
                continue
            
            score = self._calculate_match_score(kalshi_market, pm_market)
            
            if score > best_score:
                best_score = score
                best_match = pm_market
        
        # Return match if above threshold
        if best_score >= min_confidence:
            return (best_match, best_score)
        
        return None
    
    def batch_match(self, kalshi_markets: List[Dict], polymarket_markets: List[Dict],
                    min_confidence: float = 0.75) -> List[Dict]:
        """
        Batch match multiple Kalshi markets to Polymarket.
        
        Args:
            kalshi_markets: List of Kalshi markets
            polymarket_markets: List of Polymarket markets
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of matched pairs with metadata
        """
        matches = []
        
        for k_market in kalshi_markets:
            result = self.find_match(k_market, polymarket_markets, min_confidence)
            
            if result:
                pm_market, confidence = result
                
                matches.append({
                    "kalshi_ticker": k_market.get("ticker", ""),
                    "kalshi_title": k_market.get("title", ""),
                    "polymarket_id": pm_market.get("condition_id", ""),
                    "polymarket_question": pm_market.get("question", ""),
                    "confidence": confidence,
                    "kalshi_market": k_market,
                    "polymarket_market": pm_market
                })
        
        return matches
