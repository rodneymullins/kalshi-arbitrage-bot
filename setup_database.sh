#!/bin/bash
# Database Setup Script for Kalshi Bot
# Run this on Gandalf (PostgreSQL server) or remotely

echo "🔧 Setting up Kalshi Bot Database..."
echo "===================================="
echo ""

# Database configuration
DB_HOST="${DB_HOST:-192.168.1.211}"
DB_NAME="kalshi_trades"
DB_USER="kalshi_bot"
DB_PASSWORD="kalshi_bot"

echo "Configuration:"
echo "  Host: $DB_HOST"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo ""

# Check if running on Gandalf or remotely
if [ "$DB_HOST" = "localhost" ] || [ "$DB_HOST" = "127.0.0.1" ]; then
    PSQL_CMD="psql -U postgres"
else
    echo "⚠️  Remote setup - you may need to run this on Gandalf directly"
    echo "   SSH to Gandalf and run: ./setup_database.sh"
    echo ""
    read -p "Continue with remote setup? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    PSQL_CMD="PGPASSWORD=postgres psql -h $DB_HOST -U postgres"
fi

# Create role and database
echo "1. Creating database role..."
$PSQL_CMD << SQL
-- Create role if not exists
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN
        CREATE ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASSWORD';
        RAISE NOTICE 'Role $DB_USER created';
    ELSE
        RAISE NOTICE 'Role $DB_USER already exists';
    END IF;
END
\$\$;
SQL

echo "2. Creating database..."
$PSQL_CMD << SQL
-- Create database if not exists
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec
SQL

echo "3. Granting privileges..."
$PSQL_CMD << SQL
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
ALTER DATABASE $DB_NAME OWNER TO $DB_USER;
SQL

echo ""
echo "4. Creating tables..."
$PSQL_CMD -d $DB_NAME -U $DB_USER << 'SQL'
-- Opportunities table
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
    match_method TEXT,
    
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
    
    -- AI Analysis
    ai_enabled BOOLEAN DEFAULT FALSE,
    ai_score REAL,
    ai_recommendation TEXT,
    sentiment_score REAL,
    sentiment_confidence REAL,
    mispricing_likelihood REAL,
    risk_score REAL,
    risk_factors TEXT[],
    
    -- ML Analysis
    ml_score REAL,
    ml_recommendation TEXT,
    ml_confidence REAL,
    
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

-- Sessions table
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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_opportunities_timestamp ON arbitrage_opportunities(timestamp);
CREATE INDEX IF NOT EXISTS idx_opportunities_net_profit ON arbitrage_opportunities(net_profit);
CREATE INDEX IF NOT EXISTS idx_opportunities_executed ON arbitrage_opportunities(executed);
CREATE INDEX IF NOT EXISTS idx_opportunities_ai_score ON arbitrage_opportunities(ai_score);
CREATE INDEX IF NOT EXISTS idx_opportunities_scan_session ON arbitrage_opportunities(scan_session_id);

-- Training data view
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
    ml_score,
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
    AVG(ml_score) as avg_ml_score,
    SUM(actual_profit) FILTER (WHERE executed = TRUE) as total_actual_profit
FROM arbitrage_opportunities
GROUP BY DATE(timestamp)
ORDER BY date DESC;
SQL

echo ""
echo "✅ Database setup complete!"
echo ""
echo "Test connection:"
echo "  psql -h $DB_HOST -U $DB_USER -d $DB_NAME"
echo ""
echo "Or from Python:"
echo "  cd /Users/rod/Antigravity/kalshi_bot"
echo "  python3 -c 'from db.opportunity_logger import OpportunityLogger; OpportunityLogger()'"
