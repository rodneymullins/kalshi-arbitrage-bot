#!/bin/bash
# Test AI-enhanced scanner with FunctionGemma

echo "🧪 Testing AI-Enhanced Arbitrage Scanner"
echo "=========================================="
echo ""

cd /Users/rod/Antigravity/kalshi_bot

echo "1. Testing FunctionGemma connection..."
python3 -c "
from ai.functiongemma_analyzer import FunctionGemmaAnalyzer
analyzer = FunctionGemmaAnalyzer()
print('✅ FunctionGemma analyzer initialized')

# Test sentiment
result = analyzer.analyze_sentiment('Will Bitcoin hit \$100,000 by January 31?')
print(f'Sentiment test: {result}')
" 2>&1 | head -20

echo ""
echo "2. Running AI-enhanced scanner..."
python3 scan_cross_platform.py 2>&1 | head -100

echo ""
echo "✅ Test complete!"
