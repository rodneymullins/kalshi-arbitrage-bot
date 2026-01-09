"""
Circuit Breaker Pattern for Risk Management
Auto-halt trading when risk thresholds are exceeded
"""

from datetime import datetime
from typing import Dict


class CircuitBreaker:
    """Risk management circuit breaker"""
    
    def __init__(self, 
                 max_drawdown: float = 0.20,
                 max_daily_loss: float = 500,
                 max_consecutive_losses: int = 5):
        """
        Args:
            max_drawdown: Maximum allowed drawdown (e.g., 0.20 = 20%)
            max_daily_loss: Maximum daily loss in dollars
            max_consecutive_losses: Max consecutive losing trades
        """
        self.max_drawdown = max_drawdown
        self.max_daily_loss = max_daily_loss
        self.max_consecutive_losses = max_consecutive_losses
        
        self.is_halted = False
        self.halt_reason = None
        self.consecutive_losses = 0
        self.daily_pnl = {}
    
    def check_drawdown(self, current_drawdown: float) -> bool:
        """Check if drawdown exceeds threshold"""
        if current_drawdown > self.max_drawdown:
            self.halt(f"Max drawdown exceeded: {current_drawdown:.1%}")
            return True
        return False
    
    def check_daily_loss(self, date: str, loss: float) -> bool:
        """Check if daily loss exceeds threshold"""
        if date not in self.daily_pnl:
            self.daily_pnl[date] = 0
        
        self.daily_pnl[date] += loss
        
        if self.daily_pnl[date] < -self.max_daily_loss:
            self.halt(f"Daily loss limit hit: ${self.daily_pnl[date]:.2f}")
            return True
        return False
    
    def record_trade(self, pnl: float) -> bool:
        """
        Record trade result and check consecutive losses
        
        Returns:
            True if should halt, False otherwise
        """
        if pnl < 0:
            self.consecutive_losses += 1
            if self.consecutive_losses >= self.max_consecutive_losses:
                self.halt(f"{self.consecutive_losses} consecutive losses")
                return True
        else:
            self.consecutive_losses = 0
        
        return False
    
    def halt(self, reason: str):
        """Trigger circuit breaker halt"""
        self.is_halted = True
        self.halt_reason = reason
        print(f"⛔ CIRCUIT BREAKER ACTIVATED: {reason}")
    
    def reset(self):
        """Manually reset circuit breaker"""
        self.is_halted = False
        self.halt_reason = None
        self.consecutive_losses = 0
        self.daily_pnl = {}
        print("✅ Circuit breaker reset")
    
    def status(self) -> Dict:
        """Get current status"""
        return {
            "is_halted": self.is_halted,
            "halt_reason": self.halt_reason,
            "consecutive_losses": self.consecutive_losses,
            "daily_pnl": sum(self.daily_pnl.values())
        }


# Example usage
if __name__ == "__main__":
    breaker = CircuitBreaker(
        max_drawdown=0.15,      # 15% max drawdown
        max_daily_loss=300,      # $300 daily loss limit
        max_consecutive_losses=3  # 3 losses in a row
    )
    
    print("Circuit Breaker Test")
    print("="*50)
    
    # Simulate trades
    trades = [-50, -40, -35]  # 3 consecutive losses
    
    for i, trade in enumerate(trades, 1):
        print(f"Trade {i}: ${trade:.2f}")
        if breaker.record_trade(trade):
            print("Trading halted!")
            break
    
    print(f"\nStatus: {breaker.status()}")
