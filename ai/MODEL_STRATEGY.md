# AI Model Strategy for Arbitrage Bot

## Why FunctionGemma is Perfect

### **Primary Model: FunctionGemma (270M)**

**Advantages**:
1. ✅ **Structured Output** - Designed for JSON responses (perfect for scores/decisions)
2. ✅ **Function Calling** - Can trigger specific analysis types
3. ✅ **Extremely Fast** - 270M params = <1 second inference
4. ✅ **Consistent** - Same input → same output (critical for trading)
5. ✅ **Lightweight** - Can run multiple parallel analyses

**Use Cases in Arbitrage Bot**:
- **Sentiment scoring** → Extract numerical bias/confidence scores
- **Risk assessment** → Structured risk factor analysis
- **Mispricing detection** → Boolean flags + confidence scores
- **Market matching** → Similarity scoring with reasoning
- **Opportunity ranking** → Consistent scoring for prioritization

### **Secondary Model: Qwen2.5-Coder (7B)**

**Use When**:
- Need deeper reasoning (complex market analysis)
- Long-form explanations required
- Code generation (new strategies)
- Fallback if FunctionGemma unavailable

### **Model Selection Logic**

```python
def select_model(task_type: str, response_needed: str):
    """Auto-select optimal model"""
    
    if response_needed == "structured_json":
        return "functiongemma:2b"  # Always use FG for structured
    
    if task_type in ["sentiment", "risk", "scoring"]:
        return "functiongemma:2b"  # Fast structured analysis
    
    if task_type in ["reasoning", "explanation", "strategy"]:
        return "qwen2.5-coder:7b"  # Complex reasoning
    
    return "functiongemma:2b"  # Default to speed
```

## Performance Comparison

| Model | Params | Speed | Structured | Use Case |
|-------|--------|-------|------------|----------|
| FunctionGemma | 270M | ⚡⚡⚡ (<1s) | ✅✅✅ | Primary analysis |
| Qwen2.5-Coder | 7B | ⚡⚡ (2-5s) | ✅✅ | Complex reasoning |
| Gemma | 2B | ⚡⚡⚡ (1-2s) | ✅ | Backup |

## Updated Architecture

```
Arbitrage Opportunity
        ↓
   ┌────┴────┐
   │ Router  │ (Selects FunctionGemma or Qwen)
   └────┬────┘
        ↓
┌───────┴────────┐
│ FunctionGemma  │ (90% of requests)
│   (270M)       │
│                │
│ • Sentiment    │
│ • Risk         │
│ • Mispricing   │
│ • Scoring      │
└───────┬────────┘
        │
        ├─→ JSON Output → Decision Logic
        │
        └─→ (If complex) → Qwen2.5-Coder
```

## Example FunctionGemma Workflow

```python
# 1. Market Sentiment (FunctionGemma)
sentiment = functiongemma.analyze_sentiment(
    "Will Bitcoin hit $100k by Jan 31?"
)
# Output: {"sentiment_score": 0.6, "confidence": 0.8, ...}
# Time: 0.5s

# 2. Risk Assessment (FunctionGemma)
risk = functiongemma.assess_risk(
    kalshi_market="BTC-100K-JAN31",
    polymarket_market="Will BTC reach $100,000...",
    match_confidence=0.9
)
# Output: {"overall_risk": 0.2, "resolution_risk": 0.1, ...}
# Time: 0.6s

# 3. Combined Decision (FunctionGemma)
decision = functiongemma.make_decision(
    sentiment=sentiment,
    risk=risk,
    net_profit=0.15,
    roi=3.2
)
# Output: {"execute": true, "confidence": 0.85, ...}
# Time: 0.4s

# Total time: ~1.5s (vs 5-10s with Qwen)
```

## Integration with Existing Stack

### On Aragorn (192.168.1.176):
```bash
# Pull FunctionGemma
ollama pull functiongemma:2b

# Verify
curl http://192.168.1.176:11434/api/tags
```

### In Scanner:
```python
from ai.functiongemma_analyzer import FunctionGemmaAnalyzer

class CrossPlatformScanner:
    def __init__(self):
        # ... existing code ...
        
        # Add FunctionGemma (primary)
        self.ai_analyzer = FunctionGemmaAnalyzer(
            endpoint="http://192.168.1.176:11434/api/generate"
        )
    
    def calculate_arb_opportunity(self, k_market, pm_market):
        # ... existing price calculations ...
        
        # Add AI analysis (using FunctionGemma)
        ai_analysis = self.ai_analyzer.analyze_opportunity({
            "kalshi_market": k_market.get("title"),
            "polymarket_market": pm_market.get("question"),
            "match_confidence": match_score,
            "net_profit": net_profit,
            "roi": roi
        })
        
        opp["ai_analysis"] = ai_analysis
        opp["ai_score"] = ai_analysis["ai_score"]
        opp["ai_recommendation"] = ai_analysis["recommendation"]
        
        return opp
```

## Benefits for Your Bot

### Speed
- **Current**: Rule-based analysis (instant)
- **With FunctionGemma**: +1.5s (negligible for 15-min scans)
- **With Qwen**: +5-10s (acceptable but slower)

### Accuracy
- **Rule-based**: Misses nuanced signals
- **FunctionGemma**: Catches sentiment/bias patterns
- **Combined**: Best of both worlds

### Scalability
- Can analyze 100+ opportunities in <3 minutes
- Parallel processing (multiple FunctionGemma instances)
- Minimal resource usage (270M params)

## Deployment Strategy

1. **Week 1**: Deploy FunctionGemma analyzer
2. **Week 2**: Collect AI predictions vs actual outcomes
3. **Week 3**: Fine-tune scoring weights based on data
4. **Week 4**: Full integration with auto-ranking

## Next Steps

1. ✅ Pull FunctionGemma on Aragorn
2. ✅ Test analyzer with sample markets
3. ✅ Integrate into scanner
4. ✅ Monitor AI score accuracy
5. ✅ Fine-tune based on results

---

*FunctionGemma = Perfect fit for trading bot! Fast, structured, consistent.* 🎯
