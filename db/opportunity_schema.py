"""
Opportunity Database Schema for PostgreSQL

Tracks all arbitrage opportunities for ML training and analysis.
"""

CREATE_OPPORTUNITIES_TABLE = """
CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    
    -- Market Information
    kalshi_market TEXT NOT NULL,
    kalshi_ticker TEXT,
    polymarket_market TEXT NOT NULL,
    polymarket_id TEXT,
    
    -- Match Quality
    match_confidence REAL,
    match_method TEXT,  -- 'fuzzy', 'manual', 'exact'
    
    -- Pricing
    kalshi_yes_price REAL,
    kalshi_no_price REAL,
    polymarket_yes_price REAL,
    polymarket_no_price REAL,
    
    -- Strategy
    strategy TEXT,
    position_size REAL,
    
    -- Profitability
    gross_profit REAL,
    total_fees REAL,
    net_profit REAL,
    roi REAL,
    
    -- AI Analysis (FunctionGemma)
    ai_enabled BOOLEAN DEFAULT FALSE,
    ai_score REAL,
    ai_recommendation TEXT,
    sentiment_score REAL,
    sentiment_confidence REAL,
    mispricing_likelihood REAL,
    risk_score REAL,
    risk_factors TEXT[],
    
    -- Execution
    executed BOOLEAN DEFAULT FALSE,
    execution_timestamp TIMESTAMP,
    actual_kalshi_fill REAL,
    actual_polymarket_fill REAL,
    actual_profit REAL,
    execution_notes TEXT,
    
    -- Metadata
    scan_session_id TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_opportunities_timestamp ON arbitrage_opportunities(timestamp);
CREATE INDEX IF NOT EXISTS idx_opportunities_net_profit ON arbitrage_opportunities(net_profit);
CREATE INDEX IF NOT EXISTS idx_opportunities_executed ON arbitrage_opportunities(executed);
CREATE INDEX IF NOT EXISTS idx_opportunities_ai_score ON arbitrage_opportunities(ai_score);
CREATE INDEX IF NOT EXISTS idx_opportunities_scan_session ON arbitrage_opportunities(scan_session_id);

-- View for AI training data
CREATE OR REPLACE VIEW opportunity_training_data AS
SELECT 
    match_confidence,
    kalshi_yes_price,
    kalshi_no_price,
    polymarket_yes_price,
    polymarket_no_price,
    gross_profit,
    total_fees,
    net_profit,
    roi,
    ai_score,
    sentiment_score,
    mispricing_likelihood,
    risk_score,
    executed,
    actual_profit,
    EXTRACT(HOUR FROM timestamp) as hour_of_day,
    EXTRACT(DOW FROM timestamp) as day_of_week,
    ABS(kalshi_yes_price - polymarket_yes_price) as price_spread,
    ABS(kalshi_yes_price - kalshi_no_price) as kalshi_spread,
    ABS(polymarket_yes_price - polymarket_no_price) as poly_spread
FROM arbitrage_opportunities
WHERE ai_enabled = TRUE;

-- Stats view
CREATE OR REPLACE VIEW opportunity_stats AS
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as total_opportunities,
    COUNT(*) FILTER (WHERE executed = TRUE) as executed_count,
    AVG(net_profit) as avg_profit,
    AVG(ai_score) as avg_ai_score,
    AVG(match_confidence) as avg_match_confidence,
    SUM(actual_profit) FILTER (WHERE executed = TRUE) as total_actual_profit
FROM arbitrage_opportunities
GROUP BY DATE(timestamp)
ORDER BY date DESC;
"""

# Session tracking
CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS scan_sessions (
    id TEXT PRIMARY KEY,
    start_time TIMESTAMP DEFAULT NOW(),
    end_time TIMESTAMP,
    opportunities_found INTEGER DEFAULT 0,
    ai_enabled BOOLEAN DEFAULT FALSE,
    avg_ai_score REAL,
    config JSONB,
    notes TEXT
);
"""
