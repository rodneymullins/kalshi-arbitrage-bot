"""
Polymarket API Client (Simplified)

A lightweight client for fetching market data from Polymarket.
No authentication needed for read-only operations.

Based on official py_clob_client but simplified to avoid dependency issues.
"""
import requests
import time
from typing import Dict, List, Optional


class PolymarketClient:
    """Simplified Polymarket client for read-only market data."""
    
    def __init__(self, base_url: str = "https://clob.polymarket.com",
                 gamma_url: str = "https://gamma-api.polymarket.com"):
        """
        Initialize Polymarket client.
        
        Args:
            base_url: CLOB API endpoint (for orderbooks, prices)
            gamma_url: Gamma API endpoint (for market data)
        """
        self.base_url = base_url
        self.gamma_url = gamma_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Kalshi-Polymarket-Arbitrage-Bot/1.0'
        })
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.5  # 500ms between requests
    
    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
    
    def _get(self, url: str, params: Optional[Dict] = None) -> Dict:
        """
        Make a GET request with error handling and rate limiting.
        
        Args:
            url: Full URL to request
            params: Query parameters
            
        Returns:
            JSON response as dict
        """
        self._rate_limit()
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return {}
    
    def get_markets(self, limit: int = 100, active: bool = True) -> List[Dict]:
        """
        Get active markets from Polymarket.
        
        Args:
            limit: Maximum number of markets to return
            active: Filter for active markets only
            
        Returns:
            List of market dictionaries
        """
        url = f"{self.gamma_url}/markets"
        params = {"limit": limit}
        
        if active:
            params["closed"] = "false"
        
        result = self._get(url, params=params)
        return result if isinstance(result, list) else []
    
    def get_market(self, condition_id: str) -> Optional[Dict]:
        """
        Get a specific market by condition ID.
        
        Args:
            condition_id: Market condition ID
            
        Returns:
            Market dictionary or None
        """
        url = f"{self.gamma_url}/markets/{condition_id}"
        return self._get(url)
    
    def get_orderbook(self, token_id: str) -> Dict:
        """
        Get orderbook for a specific token.
        
        Args:
            token_id: Token ID (outcome token)
            
        Returns:
            Orderbook with bids and asks
        """
        url = f"{self.base_url}/book"
        params = {"token_id": token_id}
        return self._get(url, params=params)
    
    def get_price(self, token_id: str, side: str = "BUY") -> float:
        """
        Get best price for a token.
        
        Args:
            token_id: Token ID
            side: "BUY" or "SELL"
            
        Returns:
            Price as float (0.00 to 1.00)
        """
        url = f"{self.base_url}/price"
        params = {"token_id": token_id, "side": side.upper()}
        
        result = self._get(url, params=params)
        
        if isinstance(result, dict) and "price" in result:
            return float(result["price"])
        
        return 0.0
    
    def get_midpoint(self, token_id: str) -> float:
        """
        Get midpoint price for a token.
        
        Args:
            token_id: Token ID
            
        Returns:
            Midpoint price as float
        """
        url = f"{self.base_url}/midpoint"
        params = {"token_id": token_id}
        
        result = self._get(url, params=params)
        
        if isinstance(result, dict) and "mid" in result:
            return float(result["mid"])
        
        return 0.0
    
    def get_simplified_markets(self, limit: int = 100) -> List[Dict]:
        """
        Get simplified market data (easier to parse).
        
        Args:
            limit: Maximum number of markets
            
        Returns:
            List of simplified market dictionaries
        """
        markets = self.get_markets(limit=limit, active=True)
        simplified = []
        
        for market in markets:
            # Extract key info
            simplified.append({
                "condition_id": market.get("condition_id", ""),
                "question": market.get("question", ""),
                "description": market.get("description", ""),
                "end_date": market.get("end_date_iso", ""),
                "active": market.get("active", False),
                "closed": market.get("closed", False),
                "tokens": market.get("tokens", []),
                "outcomes": market.get("outcomes", []),
                "volume": float(market.get("volume", 0)),
                "liquidity": float(market.get("liquidity", 0)),
            })
        
        return simplified
    
    def test_connection(self) -> bool:
        """
        Test connection to Polymarket API.
        
        Returns:
            True if connection successful
        """
        try:
            markets = self.get_markets(limit=1)
            return len(markets) > 0
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False


if __name__ == "__main__":
    # Test the client
    client = PolymarketClient()
    
    print("Testing Polymarket connection...")
    if client.test_connection():
        print("✅ Connection successful!")
        
        print("\nFetching markets...")
        markets = client.get_simplified_markets(limit=5)
        
        print(f"\nFound {len(markets)} markets:")
        for i, market in enumerate(markets[:3], 1):
            print(f"\n{i}. {market['question']}")
            print(f"   Volume: ${market['volume']:,.0f}")
            print(f"   Liquidity: ${market['liquidity']:,.0f}")
            print(f"   Outcomes: {', '.join(market['outcomes'])}")
    else:
        print("❌ Connection failed!")
