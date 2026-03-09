# RAG-Based Resolution System

This document explains the RAG (Retrieval-Augmented Generation) system for intelligent resolution recommendations.

## Overview

The RAG system provides **context-aware resolution recommendations** by retrieving similar historical incidents and extracting common resolution patterns. Unlike generic LLM analysis, RAG grounds recommendations in actual past cases.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Resolution Agent                       │
│  - Analyzes current findings                             │
│  - Searches RAG for similar incidents                    │
│  - Extracts resolution patterns                          │
│  - Generates recommendations                             │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│              In-Memory RAG Indexer (FAISS)               │
│  - Sentence embeddings (all-MiniLM-L6-v2)                │
│  - Vector similarity search                              │
│  - 6 sample historical incidents                         │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
            ┌──────────────┐
            │ Sample       │
            │ Incidents    │
            │              │
            │ - Split      │
            │   booking    │
            │ - DRA dup    │
            │ - Exposure   │
            │ - Date error │
            │ - Negative   │
            │ - Expired    │
            └──────────────┘
```

## Components

### 1. In-Memory RAG Indexer (`src/rag/indexer.py`)

**Technology:**
- **FAISS** (Facebook AI Similarity Search) - in-memory vector database
- **sentence-transformers** - local embeddings (no API calls)
- Model: `all-MiniLM-L6-v2` (384-dimensional embeddings)

**Why in-memory?**
- POC/testing - no database setup required
- Fast (<10ms search with 100s of documents)
- Portable - save/load with pickle
- Good for <10k documents

**Key Methods:**
```python
indexer = get_rag_indexer()  # Singleton

# Add incidents
indexer.add_incident(incident)
indexer.add_incidents_batch(incidents)

# Search
matches = indexer.search(query, top_k=5, min_similarity=0.3)
matches = indexer.search_by_type(query, "split_booking_duplicate", top_k=3)

# Get specific incident
incident = indexer.get_incident_by_id("INC-2024-001")

# Stats
stats = indexer.get_stats()
```

### 2. Sample Incidents (`src/rag/sample_incidents.py`)

Contains 6 historical incidents:

| Incident ID | Type | Description |
|------------|------|-------------|
| INC-2024-001 | Split Booking Duplicate | Client XYZ, R+D=D pattern, EOD crossing |
| INC-2024-002 | DRA Duplicate | Margin Gen timeout retry |
| INC-2024-003 | Exposure Anomaly | 10x notional, pricing bug |
| INC-2024-004 | Date Anomaly | Effective > maturity |
| INC-2024-005 | Negative Exposure | Invalid negative value |
| INC-2024-006 | Expired Active Trade | Lifecycle failure |

Each incident includes:
- Title and description
- Resolution steps (detailed)
- Outcome
- Metadata (amounts, timestamps, impact)

### 3. Resolution Agent (`src/agents/resolution_agent.py`)

**Input:**
- List of findings from detection agents
- Ensemble confidence score

**Process:**
1. Groups findings by error type
2. Searches RAG for similar incidents (top 3)
3. Generates explanation based on:
   - Severity level
   - Finding types
   - Similar incident outcomes
4. Extracts common resolution steps
5. Customizes steps for current context
6. Calculates confidence (ensemble + RAG similarity)

**Output:**
```python
ResolutionRecommendation(
    similar_incidents=[...],        # Top 3 matches
    explanation="...",               # Human-readable
    recommended_steps=[...],         # Action items
    confidence=0.85,                 # 0-1 score
    generated_at=datetime.now()
)
```

**Confidence Calculation:**
```
confidence = (ensemble_score * 0.6) + (avg_rag_similarity * 0.4)
```

### 4. RAG MCP Tool (`src/mcp_servers/rag_tool/server.py`)

MCP server exposing RAG capabilities:

**Tools:**
- `semantic_search` - Free-form similarity search
- `search_by_incident_type` - Filtered search
- `get_resolution_steps` - Get steps by incident ID
- `get_similar_incidents` - Auto-build query from findings
- `get_rag_stats` - Index statistics

**Note:** MCP tool is available but **not required** for basic RAG usage. The Resolution Agent directly uses the indexer.

## Integration with Orchestrator

The Resolution Agent is integrated into the detection pipeline:

```python
orchestrator = AnomalyDetectionOrchestrator(
    use_ml=True,
    use_llm=False,      # LLM disabled when RAG enabled
    use_rag=True,       # Enable RAG recommendations
)
```

**Pipeline Steps:**
1. Rule-based detection
2. ML-based detection
3. Combine findings
4. Group by entity
5. Create alerts
6. **RAG resolution analysis** ← NEW (for ensemble_score ≥ 0.5)
7. Sort by risk score

**When RAG is used:**
- Only for high-confidence alerts (ensemble_score ≥ 0.5)
- Adds `resolution_recommendation` to alert
- Logs similar incidents found and confidence
- LLM analysis is **skipped** (RAG replaces it)

## Usage Examples

### Basic RAG Search

```python
from src.rag.indexer import get_rag_indexer
from src.rag.sample_incidents import load_incidents_to_rag

# Initialize
indexer = get_rag_indexer()
load_incidents_to_rag(indexer)

# Search
matches = indexer.search(
    query="Duplicate booking with split R and D legs",
    top_k=3,
    min_similarity=0.3
)

for match in matches:
    print(f"{match.incident.title} - {match.similarity_score:.1%}")
    print(f"Resolution: {match.incident.resolution_steps[0]}")
```

### Using Resolution Agent

```python
from src.agents.resolution_agent import ResolutionAgent
from src.agents.base import FindingsObject, ErrorType, SeverityLevel

# Create findings
findings = [
    FindingsObject(
        agent_name="RuleBasedDetector",
        error_type=ErrorType.SPLIT_BOOKING_ERROR,
        confidence_score=0.95,
        description="Split booking duplicate detected",
        ...
    )
]

# Analyze
agent = ResolutionAgent()
recommendation = agent.analyze_findings(findings, ensemble_score=0.85)

# Use recommendations
print(recommendation.explanation)
for step in recommendation.recommended_steps:
    print(f"- {step}")
```

### Run Full Detection with RAG

```python
from src.agents.orchestration.orchestrator import AnomalyDetectionOrchestrator

orchestrator = AnomalyDetectionOrchestrator(use_rag=True)
alerts = orchestrator.run_full_detection()

# Check recommendations
for alert in alerts:
    if alert.resolution_recommendation:
        print(f"Alert {alert.alert_id}:")
        print(f"  {alert.resolution_recommendation}")
```

## Testing

Run the RAG test suite:

```bash
python test_rag_system.py
```

Tests:
1. RAG indexer loading and search
2. Resolution agent with single finding
3. Resolution agent with multiple findings

Expected output:
- 6 incidents loaded
- Semantic search finds relevant matches
- Resolution recommendations with 5-8 steps
- Confidence scores 0.7-0.9 for good matches

## Configuration

**Embedding Model:**
```python
indexer = InMemoryRAGIndexer(model_name="all-MiniLM-L6-v2")
```

Other options:
- `all-mpnet-base-v2` (768 dim, higher quality, slower)
- `paraphrase-MiniLM-L3-v2` (384 dim, faster)

**Similarity Threshold:**
```python
agent = ResolutionAgent(min_similarity=0.3)  # 0-1 range
```

Lower = more results (less precise)
Higher = fewer results (more precise)

**RAG Trigger Threshold:**
In orchestrator, only alerts with `ensemble_score ≥ 0.5` get RAG analysis.

## Performance

**Indexing:**
- 6 incidents: <1 second
- 100 incidents: ~2-3 seconds
- 1000 incidents: ~20-30 seconds

**Search:**
- Single query: <10ms
- Batch (10 queries): ~50ms

**Memory:**
- FAISS index: ~5-10KB per document (with 384-dim embeddings)
- 1000 incidents ≈ 5-10MB RAM

## Adding New Incidents

### Option 1: Edit `sample_incidents.py`

```python
def get_sample_incidents():
    incidents = [
        ...,  # existing incidents
        IncidentDocument(
            incident_id="INC-2024-007",
            title="New Incident Type",
            description="...",
            incident_type="new_type",
            resolution_steps=["Step 1", "Step 2", ...],
            outcome="...",
            metadata={...}
        )
    ]
    return incidents
```

### Option 2: Programmatically

```python
from src.rag.indexer import get_rag_indexer, IncidentDocument

indexer = get_rag_indexer()

new_incident = IncidentDocument(...)
indexer.add_incident(new_incident)

# Save for next run
indexer.save_to_file("incidents.pkl")

# Load later
indexer.load_from_file("incidents.pkl")
```

## Production Considerations

For production deployment:

1. **Replace in-memory with persistent store:**
   - Use PostgreSQL with pgvector extension
   - Or managed vector DB (Pinecone, Weaviate, etc.)

2. **Incident data source:**
   - Pull from case management system API
   - Regular sync job (daily/weekly)
   - Track incident metadata (date, analyst, effectiveness)

3. **Model updates:**
   - Fine-tune embedding model on domain data
   - Consider domain-specific models (finance, legal)

4. **Monitoring:**
   - Track RAG recommendation acceptance rate
   - A/B test RAG vs LLM vs hybrid
   - Log similarity scores and user feedback

5. **Scaling:**
   - FAISS supports GPU acceleration for large indexes
   - Use IndexIVFFlat or IndexHNSW for >10k documents
   - Shard by incident type or date range

## Comparison: RAG vs LLM

| Feature | RAG (Current) | LLM (Previous) |
|---------|---------------|----------------|
| Data source | Historical incidents | General knowledge |
| Latency | <10ms | ~1-3s (API call) |
| Cost | Free (local) | $0.01-0.10 per alert |
| Accuracy | High (grounded) | Variable (hallucination risk) |
| Explainability | Shows similar cases | Black box |
| Customization | Easy (add incidents) | Requires prompt engineering |
| Offline | Yes | No (API required) |

**Recommendation:** Use RAG for POC and production unless you need:
- Novel analysis (no historical precedent)
- Natural language generation quality
- Multi-step reasoning beyond pattern matching

## Troubleshooting

**Issue: "sentence-transformers not installed"**
```bash
pip install sentence-transformers
```

**Issue: "faiss-cpu not installed"**
```bash
pip install faiss-cpu
```

**Issue: No similar incidents found**
- Check `min_similarity` threshold (try 0.0)
- Verify incidents loaded: `indexer.get_stats()`
- Test search query directly: `indexer.search("test", top_k=10)`

**Issue: Poor similarity scores**
- Add more sample incidents of the same type
- Use more specific query text
- Try different embedding model

**Issue: Slow indexing**
- Use `add_incidents_batch()` instead of individual `add_incident()`
- Consider lighter model (`paraphrase-MiniLM-L3-v2`)

## Next Steps

1. **Add more incidents** - Populate with real historical cases
2. **Integrate feedback** - Track which recommendations were helpful
3. **A/B test** - Compare RAG vs LLM vs hybrid approaches
4. **Dashboard integration** - Show similar incidents in UI
5. **Production deployment** - Migrate to persistent vector store

## References

- FAISS: https://github.com/facebookresearch/faiss
- sentence-transformers: https://www.sbert.net/
- RAG pattern: https://arxiv.org/abs/2005.11401
