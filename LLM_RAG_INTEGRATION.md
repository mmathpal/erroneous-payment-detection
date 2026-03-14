# LLM-Enhanced RAG Recommendations

## Overview

RAG recommendations now use **LLM (GPT-4o-mini)** to generate intelligent, context-aware resolution suggestions when an OpenAI API key is provided.

## How It Works

### 1. **RAG retrieves similar incidents** (Vector Search)
- Uses ChromaDB to find top 3 most similar historical incidents
- Based on semantic similarity (no LLM)

### 2. **LLM generates recommendations** (If API key available)
- Takes current findings + similar incidents as context
- Generates professional, actionable recommendations
- Provides root cause analysis and specific resolution steps

### 3. **Fallback to template** (If no API key)
- Uses template-based explanation
- Still functional without LLM

---

## Configuration

### Enable LLM-Enhanced RAG

**1. Add OpenAI API key to `.env`:**
```bash
OPENAI_API_KEY=sk-your-api-key-here
```

**2. Enable in dashboard:**
- ✅ Check "RAG Recommendations" in sidebar
- The system will automatically use LLM if API key is available

### LLM Settings

**Model**: GPT-4o-mini (fast, cost-effective)
**Temperature**: 0.3 (low for consistent, factual responses)
**Max Tokens**: 500 (2-3 paragraphs)

---

## Example LLM Prompt

The LLM receives:

**Context:**
```
You are an expert in payment risk management for OTC clearing operations.
Analyze the following payment risk detection findings.

Current Findings:
1. [DUPLICATE_BOOKING] Split booking pattern detected for client ABC123
   Confidence: 95%, Severity: high

2. [PV_DISCREPANCY] Component PV mismatch of $15,000
   Confidence: 90%, Severity: medium

Overall Detection Confidence: 92%

Similar Past Incidents:
1. Duplicate Booking - Split Pattern (Similarity: 92%)
   Description: Client XYZ booked R+D delivery with 45min gap
   Resolution: Verified with client, reversed duplicate
   Outcome: Successfully resolved

Task: Provide concise recommendation in 2-3 paragraphs:
1. Summarize what was detected and why it's concerning
2. Explain likely root cause based on similar incidents
3. Recommend specific actions
4. Mention immediate risks
```

**LLM Response:**
```
The system has detected a duplicate booking pattern for client ABC123,
characterized by split bookings (R+D delivery types) with a high confidence
of 95%. Additionally, a present value discrepancy of $15,000 has been
identified. This combination suggests a potential erroneous payment scenario
that requires immediate attention.

Based on similar past incidents with 92% similarity, this pattern typically
occurs when a client books a return (R) delivery followed by a delivery (D)
booking within a short timeframe, often due to a balance reversal or
correction attempt. The PV discrepancy further indicates that the component
valuation may not be properly synchronized with the actual position.

Recommended Actions:
1. IMMEDIATE: Contact client ABC123 to verify if both bookings were intentional
2. Review the timeline of bookings and check for any balance reversals
3. Investigate the $15,000 PV discrepancy in the component valuation
4. If confirmed as duplicate, reverse the second booking and adjust PV
5. Add monitoring alert for this client to prevent future occurrences

Given the high confidence and historical pattern match, this should be
prioritized as it poses both financial and operational risk if not addressed
promptly.
```

---

## Benefits of LLM-Enhanced RAG

### vs Pure RAG (Template-based)
- ✅ **Natural language**: Easier to read and understand
- ✅ **Context-aware**: Considers all findings together
- ✅ **Actionable**: Provides specific, prioritized steps
- ✅ **Professional**: Suitable for reporting to management
- ✅ **Intelligent**: Infers root causes and urgency

### vs Pure LLM (No RAG)
- ✅ **Grounded in history**: Uses real past incidents
- ✅ **Factual**: Not hallucinating, based on actual resolutions
- ✅ **Proven solutions**: Recommendations from successful outcomes
- ✅ **Consistent**: RAG ensures similar issues get similar guidance

---

## Cost & Performance

### API Costs (GPT-4o-mini)
- **Per alert**: ~$0.0001 - $0.0003 (0.01-0.03 cents)
- **Per 100 alerts**: ~$0.01 - $0.03
- **Per month** (1000 alerts): ~$0.10 - $0.30

**Very affordable!**

### Performance
- **RAG search**: <10ms
- **LLM generation**: 1-2 seconds
- **Total**: ~2 seconds per alert

---

## Dashboard Behavior

### When API Key is Present
1. User enables "RAG Recommendations" checkbox
2. System detects API key is available
3. RAG retrieves similar incidents (fast)
4. LLM generates intelligent recommendation (2s)
5. Displays in alert details under "💡 Resolution Recommendation"
6. Logs show: "✅ Added RAG recommendation for {client_id}"

### When NO API Key
1. User enables "RAG Recommendations" checkbox
2. System detects no API key
3. RAG retrieves similar incidents
4. Template generates basic recommendation
5. Still functional, just less sophisticated

---

## Code Flow

```python
# In dashboard.py
orchestrator = AnomalyDetectionOrchestrator(
    use_rag=True,
    openai_api_key=api_key  # Passed to orchestrator
)

# In orchestrator.py
self.resolution_agent = ResolutionAgent(
    openai_api_key=openai_api_key  # Passed to resolution agent
)

# In resolution_agent.py
def __init__(self, openai_api_key: Optional[str] = None):
    if openai_api_key:
        self.llm_client = OpenAI(api_key=openai_api_key)

def analyze_findings(...):
    if self.llm_client:
        # Use LLM for recommendation
        explanation = self._generate_llm_explanation(...)
    else:
        # Fallback to template
        explanation = self._generate_explanation(...)
```

---

## Error Handling

If LLM call fails (network, API error, etc.):
- System catches exception
- Logs warning: `[ResolutionAgent] LLM call failed: {error}`
- Automatically falls back to template-based explanation
- User still gets recommendation (graceful degradation)

---

## Comparison Table

| Feature | No RAG | RAG (No LLM) | RAG + LLM |
|---------|--------|--------------|-----------|
| **Similar Incidents** | ❌ | ✅ | ✅ |
| **Resolution Steps** | ❌ | ✅ (from incidents) | ✅ (LLM enhanced) |
| **Natural Language** | ❌ | ⚠️ (template) | ✅ (LLM generated) |
| **Root Cause Analysis** | ❌ | ⚠️ (basic) | ✅ (intelligent) |
| **Urgency Assessment** | ❌ | ⚠️ (severity only) | ✅ (context-aware) |
| **Requires API Key** | ❌ | ❌ | ✅ |
| **Cost** | Free | Free | ~$0.0001/alert |
| **Speed** | N/A | <10ms | ~2 seconds |
| **Offline Capable** | ✅ | ✅ | ❌ |

---

## Best Practice

**For POC/Demo:**
- ✅ Enable both RAG and LLM
- ✅ Add OpenAI API key
- ✅ Show intelligent recommendations to MD
- ✅ Highlight how AI enhances decision-making

**For Production:**
- ✅ Enable RAG + LLM for high-value alerts
- ⚠️ Consider costs for high-volume scenarios
- ✅ Monitor API usage and costs
- ✅ Implement caching for repeated patterns
- ✅ Set budget limits in OpenAI dashboard

---

## Testing

**With API Key:**
```bash
# 1. Add to .env
echo "OPENAI_API_KEY=sk-your-key" >> .env

# 2. Run dashboard
poetry run streamlit run src/ui/dashboard.py

# 3. Enable RAG checkbox
# 4. Run detection
# 5. View alert details - see LLM recommendation
```

**Without API Key:**
```bash
# 1. Remove from .env or leave blank
# 2. Run dashboard
# 3. Enable RAG checkbox (will use template)
# 4. Still gets recommendations, just simpler
```

---

## Summary

✅ **RAG recommendations now use LLM** (GPT-4o-mini)
✅ **Intelligent, context-aware suggestions**
✅ **Graceful fallback** if no API key
✅ **Very low cost** (~$0.0001 per alert)
✅ **Professional output** suitable for MD presentation

**Key Insight**: Best of both worlds - RAG provides factual grounding from history, LLM provides intelligent synthesis and natural language.
