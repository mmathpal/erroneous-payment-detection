# RAG Recommendations - How It Works (No LLM Required)

## Overview

The **RAG (Retrieval-Augmented Generation) Recommendations** feature provides resolution suggestions based on **similar past incidents** using **pure vector similarity search** - **NO LLM required**.

## Important: RAG ≠ LLM

**RAG Recommendations**: Uses ChromaDB vector search (no LLM)
**LLM Analysis**: Uses OpenAI GPT-4o-mini (requires API key)

These are **two separate features** that can be toggled independently in the dashboard.

---

## How RAG Works (Without LLM)

### 1. **Incident Storage (Offline)**
**File**: `src/rag/sample_incidents.py`

Sample historical incidents are stored with:
- Incident ID and title
- Description of the issue
- Incident type (duplicate_booking, zero_margin, etc.)
- Resolution steps taken
- Outcome
- Metadata

Example:
```python
{
    "incident_id": "INC-2024-001",
    "title": "Duplicate Booking - Split Pattern",
    "description": "Client XYZ123 booked 232+33 as R delivery, then booked 265 as D delivery 45 mins later",
    "incident_type": "duplicate_booking",
    "resolution_steps": [
        "Verify with client if both bookings were intentional",
        "Check if split booking was due to balance reversal",
        "Reverse the duplicate booking if confirmed"
    ],
    "outcome": "Duplicate booking reversed successfully"
}
```

### 2. **Vector Indexing (Offline)**
**File**: `src/rag/indexer.py`

- Uses **sentence-transformers** (`all-MiniLM-L6-v2`) to generate embeddings
- Embeddings are numeric vectors representing semantic meaning
- Stored in **ChromaDB** vector database
- **No LLM API calls** - all processing is local

### 3. **Similarity Search (Real-time)**
**File**: `src/agents/resolution_agent.py`

When a new alert is detected:

1. **Build Query**: Create description from current findings
   - Example: "duplicate booking with split pattern R+D delivery"

2. **Vector Search**: Compare query embedding with stored incidents
   - Uses cosine similarity to find matches
   - Returns top 3 most similar incidents
   - Minimum similarity threshold: 0.3 (30%)

3. **Extract Recommendations**:
   - Combine resolution steps from top matches
   - Remove duplicates
   - Prioritize by similarity score

4. **Generate Explanation** (Template-based, not LLM):
   ```python
   explanation = f"Based on {len(top_incidents)} similar past incident(s):\n"
   for incident in top_incidents:
       explanation += f"- {incident['title']} (similarity: {incident['similarity_score']:.0%})\n"
   explanation += "\nRecommended actions based on successful past resolutions."
   ```

### 4. **Display in Dashboard**
**File**: `src/ui/dashboard.py`

The recommendation appears in the alert's expandable details:
```
📋 View Details
  ├── [Findings from each detection agent]
  └── 💡 Resolution Recommendation:
      Based on 2 similar past incident(s):
      - Duplicate Booking - Split Pattern (similarity: 92%)
      - DRA Duplicate After EOD (similarity: 78%)

      Recommended actions:
      1. Verify with client if both bookings were intentional
      2. Check if split booking was due to balance reversal
      3. Reverse the duplicate booking if confirmed
```

---

## Technical Details

### Vector Embeddings
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Embedding Size**: 384 dimensions
- **Processing**: Runs locally (no API)
- **Speed**: ~1ms per incident

### Similarity Matching
- **Algorithm**: Cosine similarity
- **Threshold**: 0.3 (configurable)
- **Top K**: 3 incidents
- **Deduplication**: By incident_id

### Confidence Calculation
```python
confidence = (avg_similarity * 0.7) + (ensemble_score * 0.3)
```

Factors:
- Higher similarity → Higher confidence
- More similar incidents found → Higher confidence
- Higher ensemble score → Higher confidence

---

## LLM vs RAG Comparison

| Feature | RAG Recommendations | LLM Analysis |
|---------|-------------------|--------------|
| **Requires API Key** | ❌ No | ✅ Yes (OpenAI) |
| **Offline Mode** | ✅ Yes | ❌ No |
| **Cost** | Free | $$ API costs |
| **Speed** | Very fast (<10ms) | Slower (1-2s) |
| **Deterministic** | ✅ Yes | ❌ No |
| **Based On** | Historical incidents | AI reasoning |
| **Recommendations** | Past resolutions | AI-generated insights |
| **Accuracy** | High (if similar incident exists) | Variable |
| **Explainability** | ✅ Shows similar incidents | ❌ Black box |

---

## When to Use What

### Use RAG Recommendations When:
- ✅ You have historical incident data
- ✅ Similar patterns repeat frequently
- ✅ You want deterministic, explainable results
- ✅ You want offline capability
- ✅ You want zero cost

### Use LLM Analysis When:
- ✅ Dealing with novel/complex patterns
- ✅ Need natural language explanations
- ✅ Want AI reasoning beyond past incidents
- ✅ Have OpenAI API budget
- ✅ Need context-aware insights

### Use Both When:
- ✅ Maximum confidence needed
- ✅ Both historical and AI insights valuable
- ✅ Critical/high-value alerts
- ✅ Want comprehensive analysis

---

## Adding New Incidents to RAG

**File**: `src/rag/sample_incidents.py`

```python
SAMPLE_INCIDENTS = [
    {
        "incident_id": "INC-2024-NEW",
        "title": "Your Incident Title",
        "description": "Detailed description of what happened",
        "incident_type": "duplicate_booking",  # or zero_margin, pv_discrepancy
        "resolution_steps": [
            "Step 1: What you did",
            "Step 2: What worked",
            "Step 3: Final resolution"
        ],
        "outcome": "What was the result",
        "metadata": {
            "date": "2024-03-15",
            "client_id": "XYZ123",
            "value_date": "2024-03-14"
        }
    }
]
```

Then restart the dashboard - new incidents will be automatically indexed!

---

## Architecture

```
Current Alert
    ↓
Generate Query Text
    ↓
sentence-transformers (offline)
    ↓
Query Embedding (384-dim vector)
    ↓
ChromaDB Similarity Search
    ↓
Top 3 Similar Incidents
    ↓
Extract Resolution Steps
    ↓
Template-Based Explanation
    ↓
Display Recommendation
```

**Key Point**: The entire pipeline runs **offline** with **no LLM API calls**.

---

## Configuration

**File**: `src/agents/resolution_agent.py`

```python
class ResolutionAgent:
    def __init__(self, min_similarity: float = 0.3):
        # Minimum similarity score (0.0 to 1.0)
        # 0.3 = 30% similarity threshold
        # Lower = more matches (less strict)
        # Higher = fewer matches (more strict)
```

**Recommended Settings:**
- **Strict** (high precision): 0.5-0.7
- **Balanced** (default): 0.3-0.5
- **Lenient** (high recall): 0.1-0.3

---

## Performance

- **Index Load Time**: ~100ms (first time)
- **Search Time**: <10ms per query
- **Memory Usage**: ~50MB for 100 incidents
- **Scalability**: Can handle 10,000+ incidents efficiently

---

## Summary

**RAG Recommendations = Vector Similarity Search (No LLM)**
- Finds similar historical incidents using embeddings
- Extracts resolution steps from past successes
- Fast, free, offline, deterministic, explainable

**LLM Analysis = AI Reasoning (Requires OpenAI API)**
- Generates insights using GPT-4o-mini
- Provides context-aware explanations
- Slower, costs money, requires internet, non-deterministic

Both are valuable and can be used together or independently!
