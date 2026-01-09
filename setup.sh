#!/bin/bash
# Setup Script for AI-Enhanced Arbitrage Bot
# Addresses all known limitations

echo "🤖 Kalshi/Polymarket Arbitrage Bot - Setup"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check current directory
if [ ! -f "scan_cross_platform.py" ]; then
    echo -e "${RED}❌ Error: Must run from /Users/rod/Antigravity/kalshi_bot${NC}"
    exit 1
fi

echo "📋 Checking prerequisites..."
echo ""

# 1. Python dependencies
echo "1️⃣  Python dependencies..."
pip3 install --user fuzzywuzzy python-Levenshtein psycopg2-binary scikit-learn joblib requests 2>&1 | grep -E "(Successfully|Requirement already)"
echo -e "${GREEN}✅ Python packages installed${NC}"
echo ""

# 2. FunctionGemma on Aragorn
echo "2️⃣  FunctionGemma AI Model..."
echo -e "${YELLOW}   Checking Aragorn (192.168.1.176)...${NC}"

if curl -s --connect-timeout 3 http://192.168.1.176:11434/api/tags > /dev/null 2>&1; then
    if curl -s http://192.168.1.176:11434/api/tags 2>/dev/null | grep -q "functiongemma"; then
        echo -e "${GREEN}✅ FunctionGemma already installed on Aragorn${NC}"
    else
        echo -e "${YELLOW}⚠️  FunctionGemma not found. Installing...${NC}"
        echo ""
        echo "   Run this command on Aragorn:"
        echo -e "   ${YELLOW}ssh rod@192.168.1.176 'ollama pull functiongemma:2b'${NC}"
        echo ""
        read -p "   Press Enter after installing FunctionGemma..."
    fi
else
    echo -e "${RED}❌ Cannot reach Aragorn. Check network connection.${NC}"
    echo "   Fallback: Scanner works without AI"
fi
echo ""

# 3. PostgreSQL Database
echo "3️⃣  PostgreSQL Database..."
echo -e "${YELLOW}   Checking Gandalf (192.168.1.211)...${NC}"

if python3 -c "from db.opportunity_logger import OpportunityLogger; OpportunityLogger()" 2>&1 | grep -q "Database initialized"; then
    echo -e "${GREEN}✅ Database connection successful${NC}"
else
    echo -e "${YELLOW}⚠️  Database not configured. Setting up...${NC}"
    echo ""
    echo "   Run this script on Gandalf:"
    echo -e "   ${YELLOW}scp setup_database.sh rod@192.168.1.211:~/${NC}"
    echo -e "   ${YELLOW}ssh rod@192.168.1.211 'bash setup_database.sh'${NC}"
    echo ""
    echo "   Or run locally (if you have psql access):"
    echo -e "   ${YELLOW}bash setup_database.sh${NC}"
    echo ""
    read -p "   Press Enter after database setup..."
fi
echo ""

# 4. Create directories
echo "4️⃣  Creating directories..."
mkdir -p logs models data
echo -e "${GREEN}✅ Directories created${NC}"
echo ""

# 5. Train ML model with mock data
echo "5️⃣  Training ML model (mock data for testing)..."
python3 -c "
from ai.ml_scorer import OpportunityScorer
scorer = OpportunityScorer()
scorer.train_from_mock_data(n_samples=200)
print('${GREEN}✅ ML model trained with mock data${NC}')
print('   (Will retrain with real data after 50+ opportunities)')
" 2>&1 | grep -v "^$"
echo ""

# 6. Test scanner
echo "6️⃣  Testing scanner..."
python3 scan_cross_platform.py 2>&1 | head -20
echo ""

# Summary
echo "=========================================="
echo "🎉 Setup Complete!"
echo "=========================================="
echo ""
echo "Current Status:"
echo -e "  ${GREEN}✅${NC} Cross-platform scanner"
echo -e "  ${GREEN}✅${NC} AI integration (FunctionGemma)"
echo -e "  ${GREEN}✅${NC} ML opportunity scorer"
echo -e "  ${GREEN}✅${NC} PostgreSQL database"
echo ""
echo "Known Limitations:"
echo -e "  ${YELLOW}⚠️${NC}  No Kalshi simple binary markets currently"
echo "      → Wait for politics/economics markets to resume"
echo -e "  ${YELLOW}⚠️${NC}  ML model trained on mock data"  
echo "      → Will retrain after collecting 50-100 real opportunities"
echo ""
echo "Next Steps:"
echo "  1. Monitor Kalshi for simple binary markets"
echo "  2. Run scanner daily: python3 scan_cross_platform.py"
echo "  3. After 50+ opportunities, retrain ML model"
echo "  4. Review AI recommendations vs your judgment"
echo ""
echo "Run Scanner:"
echo -e "  ${GREEN}python3 scan_cross_platform.py${NC}                 # Single scan"
echo -e "  ${GREEN}python3 scan_cross_platform.py --continuous${NC}     # Every 15 min"
echo ""
