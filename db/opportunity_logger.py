"""
PostgreSQL Opportunity Logger

Logs all arbitrage opportunities to PostgreSQL for ML training.
Reuses existing PostgreSQL connection from trade_db.py
"""
import psycopg2
from datetime import datetime
import uuid
import json
from typing import Dict, Optional, List


class OpportunityLogger:
    """Log arbitrage opportunities to PostgreSQL"""
    
    def __init__(self, db_config: Dict = None):
        """
        Initialize logger with existing PostgreSQL connection.
        
        Args:
            db_config: Dict with 'host', 'database', 'user', 'password'
                      If None, uses default from trade_db.py config
        """
        if db_config is None:
            # Use same config as trade_db
            db_config = {
                'host': '192.168.1.211',  # Gandalf (from your existing setup)
                'database': 'kalshi_trades',
                'user': 'kalshi_bot',
                'password': 'kalshi_bot'
            }
        
        self.db_config = db_config
        self.session_id = str(uuid.uuid4())[:8]
        self._init_database()
    
    def _get_connection(self):
        """Get PostgreSQL connection"""
        return psycopg2.connect(**self.db_config)
    
    def _init_database(self):
        """Initialize database schema"""
        from db.opportunity_schema import CREATE_OPPORTUNITIES_TABLE, CREATE_SESSIONS_TABLE
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(CREATE_OPPORTUNITIES_TABLE)
            cursor.execute(CREATE_SESSIONS_TABLE)
            conn.commit()
            print("✅ Opportunity database initialized")
        except Exception as e:
            print(f"⚠️  Database init warning: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def start_session(self, ai_enabled: bool = False, config: Dict = None):
        """Start a new scan session"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO scan_sessions (id, start_time, ai_enabled, config)
                VALUES (%s, %s, %s, %s)
            """, (
                self.session_id,
                datetime.now(),
                ai_enabled,
                json.dumps(config) if config else None
            ))
            conn.commit()
        except Exception as e:
            print(f"Error starting session: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def log_opportunity(self, opportunity: Dict) -> bool:
        """
        Log an arbitrage opportunity to PostgreSQL.
        
        Args:
            opportunity: Dict with opportunity details from scanner
            
        Returns:
            True if logged successfully
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Extract AI analysis if present
            ai_analysis = opportunity.get('ai_analysis', {})
            sentiment = ai_analysis.get('sentiment', {}) if ai_analysis else {}
            mispricing = ai_analysis.get('mispricing', {}) if ai_analysis else {}
            risk = ai_analysis.get('risk', {}) if ai_analysis else {}
            
            # Parse prices from strings
            kalshi_prices = opportunity.get('kalshi_prices', '')
            poly_prices = opportunity.get('polymarket_prices', '')
            
            k_yes, k_no = self._parse_prices(kalshi_prices)
            p_yes, p_no = self._parse_prices(poly_prices)
            
            cursor.execute("""
                INSERT INTO arbitrage_opportunities (
                    timestamp,
                    kalshi_market, polymarket_market,
                    match_confidence, match_method,
                    kalshi_yes_price, kalshi_no_price,
                    polymarket_yes_price, polymarket_no_price,
                    strategy, position_size,
                    gross_profit, total_fees, net_profit, roi,
                    ai_enabled, ai_score, ai_recommendation,
                    sentiment_score, sentiment_confidence,
                    mispricing_likelihood, risk_score, risk_factors,
                    scan_session_id
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
            """, (
                datetime.now(),
                opportunity.get('kalshi_market'),
                opportunity.get('polymarket_market'),
                opportunity.get('match_confidence', 0.8),
                'fuzzy',
                k_yes, k_no, p_yes, p_no,
                opportunity.get('strategy'),
                5.0,  # position_size from config
                opportunity.get('gross_profit', 0),
                opportunity.get('total_fees', 0),
                opportunity.get('net_profit', 0),
                opportunity.get('roi', 0),
                'ai_analysis' in opportunity and opportunity['ai_analysis'] is not None,
                opportunity.get('ai_score'),
                opportunity.get('ai_recommendation'),
                sentiment.get('sentiment_score'),
                sentiment.get('confidence'),
                mispricing.get('mispricing_likelihood'),
                risk.get('overall_risk'),
                risk.get('risk_factors', []),
                self.session_id
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error logging opportunity: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def _parse_prices(self, price_str: str) -> tuple:
        """Parse 'YES: $0.45, NO: $0.55' into (0.45, 0.55)"""
        try:
            parts = price_str.split(',')
            yes = float(parts[0].split('$')[1])
            no = float(parts[1].split('$')[1])
            return yes, no
        except:
            return 0.0, 0.0
    
    def update_execution(self, opportunity_id: int, executed: bool,
                        actual_profit: float = None, notes: str = None):
        """Update opportunity with execution results"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE arbitrage_opportunities
                SET executed = %s,
                    execution_timestamp = %s,
                    actual_profit = %s,
                    execution_notes = %s,
                    updated_at = %s
                WHERE id = %s
            """, (
                executed,
                datetime.now() if executed else None,
                actual_profit,
                notes,
                datetime.now(),
                opportunity_id
            ))
            conn.commit()
        except Exception as e:
            print(f"Error updating execution: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def end_session(self, notes: str = None):
        """End current scan session"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Get session stats
            cursor.execute("""
                SELECT COUNT(*), AVG(ai_score)
                FROM arbitrage_opportunities
                WHERE scan_session_id = %s
            """, (self.session_id,))
            
            count, avg_score = cursor.fetchone()
            
            # Update session
            cursor.execute("""
                UPDATE scan_sessions
                SET end_time = %s,
                    opportunities_found = %s,
                    avg_ai_score = %s,
                    notes = %s
                WHERE id = %s
            """, (
                datetime.now(),
                count or 0,
                avg_score,
                notes,
                self.session_id
            ))
            
            conn.commit()
        except Exception as e:
            print(f"Error ending session: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_recent_opportunities(self, limit: int = 10) -> List[Dict]:
        """Get recent opportunities for analysis"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    id, timestamp, kalshi_market, polymarket_market,
                    net_profit, roi, ai_score, ai_recommendation, executed
                FROM arbitrage_opportunities
                ORDER BY timestamp DESC
                LIMIT %s
            """, (limit,))
            
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'timestamp': row[1],
                    'kalshi_market': row[2],
                    'polymarket_market': row[3],
                    'net_profit': row[4],
                    'roi': row[5],
                    'ai_score': row[6],
                    'ai_recommendation': row[7],
                    'executed': row[8]
                }
                for row in rows
            ]
        finally:
            conn.close()
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE executed = TRUE) as executed,
                    AVG(net_profit) as avg_profit,
                    AVG(ai_score) as avg_ai_score,
                    MAX(timestamp) as last_opportunity
                FROM arbitrage_opportunities
            """)
            
            row = cursor.fetchone()
            return {
                'total_opportunities': row[0] or 0,
                'executed_count': row[1] or 0,
                'avg_profit': float(row[2]) if row[2] else 0.0,
                'avg_ai_score': float(row[3]) if row[3] else 0.0,
                'last_opportunity': row[4]
            }
        finally:
            conn.close()


# Quick test
if __name__ == "__main__":
    logger = OpportunityLogger()
    
    # Test opportunity
    test_opp = {
        'kalshi_market': 'Will Bitcoin hit $100k?',
        'polymarket_market': 'Will BTC reach $100,000?',
        'kalshi_prices': 'YES: $0.45, NO: $0.55',
        'polymarket_prices': 'YES: $0.42, NO: $0.58',
        'strategy': 'Buy YES on Kalshi, NO on Polymarket',
        'gross_profit': 0.15,
        'total_fees': 0.08,
        'net_profit': 0.07,
        'roi': 1.36,
        'ai_score': 0.72,
        'ai_recommendation': 'CONSIDER',
        'ai_analysis': {
            'sentiment': {'sentiment_score': 0.65, 'confidence': 0.82},
            'mispricing': {'mispricing_likelihood': 0.45},
            'risk': {'overall_risk': 0.28, 'risk_factors': ['timing', 'resolution']}
        }
    }
    
    logger.start_session(ai_enabled=True)
    success = logger.log_opportunity(test_opp)
    
    if success:
        print("✅ Test opportunity logged!")
        stats = logger.get_stats()
        print(f"Database stats: {stats}")
    
    logger.end_session("Test run")
