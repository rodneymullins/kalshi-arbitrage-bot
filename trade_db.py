"""
Trade Database for Kalshi Bot - PostgreSQL Version
Centralized on Gandalf (192.168.1.211)
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import List, Dict, Optional


class TradeDB:
    """Manages trade history and performance data in PostgreSQL"""
    
    def __init__(self):
        self.db_config = {
            'host': '192.168.1.211',
            'database': 'postgres',
            'user': 'rod',
            'password': ''  # Assuming no password like casino DB
        }
        self.init_db()
    
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    def init_db(self):
        """Initialize database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kalshi_trades (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                market TEXT NOT NULL,
                side TEXT NOT NULL,
                size REAL NOT NULL,
                price REAL NOT NULL,
                pnl REAL DEFAULT 0,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Performance metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kalshi_performance (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                total_pnl REAL NOT NULL,
                win_rate REAL NOT NULL,
                sharpe_ratio REAL NOT NULL,
                max_drawdown REAL NOT NULL,
                total_trades INTEGER NOT NULL,
                active_positions INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_timestamp 
            ON kalshi_trades(timestamp DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_market 
            ON kalshi_trades(market)
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ PostgreSQL database initialized on Gandalf")
    
    def log_trade(self, market: str, side: str, size: float, price: float, pnl: float = 0):
        """Log a new trade"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        timestamp = datetime.now()
        cursor.execute("""
            INSERT INTO kalshi_trades (timestamp, market, side, size, price, pnl)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (timestamp, market, side, size, price, pnl))
        
        trade_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"📝 Trade logged: {side} {size} {market} @ ${price:.2f}")
        return trade_id
    
    def update_trade_pnl(self, trade_id: int, pnl: float, status: str = "closed"):
        """Update trade P&L when position is closed"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE kalshi_trades SET pnl = %s, status = %s WHERE id = %s
        """, (pnl, status, trade_id))
        
        conn.commit()
        cursor.close()
        conn.close()
    
    def get_recent_trades(self, limit: int = 20) -> List[Dict]:
        """Get recent trades"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT timestamp, market, side, size, price, pnl
            FROM kalshi_trades
            ORDER BY id DESC
            LIMIT %s
        """, (limit,))
        
        trades = []
        for row in cursor.fetchall():
            trades.append({
                "timestamp": row['timestamp'].strftime("%Y-%m-%d %H:%M:%S"),
                "market": row['market'],
                "side": row['side'],
                "size": float(row['size']),
                "price": float(row['price']),
                "pnl": float(row['pnl'])
            })
        
        cursor.close()
        conn.close()
        return trades
    
    def get_performance_stats(self) -> Dict:
        """Calculate current performance metrics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Total P&L
        cursor.execute("SELECT COALESCE(SUM(pnl), 0) FROM kalshi_trades")
        total_pnl = float(cursor.fetchone()[0])
        
        # Total trades
        cursor.execute("SELECT COUNT(*) FROM kalshi_trades")
        total_trades = cursor.fetchone()[0]
        
        # Win rate
        cursor.execute("SELECT COUNT(*) FROM kalshi_trades WHERE pnl > 0")
        winning_trades = cursor.fetchone()[0]
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Active positions
        cursor.execute("SELECT COUNT(*) FROM kalshi_trades WHERE status = 'open'")
        active_positions = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return {
            "total_pnl": total_pnl,
            "win_rate": win_rate,
            "sharpe_ratio": 0.0,  # TODO: Calculate from returns
            "max_drawdown": 0.0,  # TODO: Calculate from equity curve
            "total_trades": total_trades,
            "active_positions": active_positions
        }
    
    def save_performance_snapshot(self):
        """Save current performance snapshot"""
        stats = self.get_performance_stats()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        timestamp = datetime.now()
        cursor.execute("""
            INSERT INTO kalshi_performance 
            (timestamp, total_pnl, win_rate, sharpe_ratio, max_drawdown, total_trades, active_positions)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            timestamp,
            stats["total_pnl"],
            stats["win_rate"],
            stats["sharpe_ratio"],
            stats["max_drawdown"],
            stats["total_trades"],
            stats["active_positions"]
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
    
    def get_equity_curve(self, days: int = 30) -> List[Dict]:
        """Get equity curve data for charts"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                timestamp,
                SUM(pnl) OVER (ORDER BY timestamp) as cumulative_pnl
            FROM kalshi_trades
            WHERE timestamp >= NOW() - INTERVAL '%s days'
            ORDER BY timestamp
        """, (days,))
        
        data = []
        for row in cursor.fetchall():
            data.append({
                "timestamp": row['timestamp'].strftime("%Y-%m-%d %H:%M"),
                "pnl": float(row['cumulative_pnl'])
            })
        
        cursor.close()
        conn.close()
        return data


# Example usage
if __name__ == "__main__":
    db = TradeDB()
    
    # Log sample trade
    print("\n📊 Testing PostgreSQL Trade DB...")
    trade_id = db.log_trade("KXELONMARS-99", "BUY", 5, 0.55, 0)
    
    # Simulate close
    db.update_trade_pnl(trade_id, 2.50, "closed")
    
    # Check stats
    print(f"\n✅ Performance: {db.get_performance_stats()}")
    print(f"\n📈 Recent Trades:")
    for trade in db.get_recent_trades(5):
        print(f"  {trade['timestamp']} - {trade['side']} {trade['size']} {trade['market']} @ ${trade['price']:.2f} → P&L: ${trade['pnl']:.2f}")
