# CLAUDE.md — Erroneous Payment Detection System

## Project Context
This is a POC for Exposure Manager (EM) application.
It detects erroneous payments in the OTC clearing space.

## Domain Knowledge
- EM = Exposure Manager, the application we work on
- DRA = Daily Return Amount
- Margin Gen = External margin calculation engine
- MARK = Synchronised margin calculation system (not pure Kafka)
- Split booking = When EM splits a booking into R (return) and D (delivery)
  legs based on existing balance direction changes
- EOD = End of Day boundary — bookings crossing this are high risk

## Architecture
Multi-agent system with 5 specialist agents + 1 orchestrator:
1. Orchestrator Agent — supervisor, delegates and aggregates
2. Database Agent — queries Movement, DRA, Booking tables
3. Log Agent — reads EM application log files
4. Kafka Agent — consumes Margin Gen / MARK responses
5. Email Agent — searches Exchange via MS Graph API
6. Resolution Agent — RAG-powered, recommends fixes

Each agent has dedicated MCP servers (see /mcp_servers/)

## Tech Stack
- Python 3.11+
- LangChain for agent orchestration
- FastMCP for MCP servers
- ChromaDB for vector store (RAG)
- scikit-learn + XGBoost + PyTorch for ML models
- PostgreSQL (EM table mirror for POC)
- confluent-kafka-python for Kafka
- msal + requests for MS Graph / Exchange
- FastAPI for backend
- Streamlit for POC dashboard
- MLflow for model tracking
- Docker Compose for local deployment

## Coding Standards
- Always add type hints to all functions
- Always write docstrings
- Use async/await for I/O-bound operations
- Each agent must return a FindingsObject (see agents/base.py)
- All MCP tools must return structured JSON
- Never hardcode credentials — use .env file
- Write a unit test for every new function in /tests/

## Key Data Tables (PostgreSQL)
- movements: client_id, value_date, currency, amount, delivery_type, booking_timestamp
- dra: client_id, value_date, dra_amount, methodology
- bookings: booking_id, client_id, trade_id, booking_timestamp, amount, status
- ci_collateral_movement: collateral_movement_id, collateral_balance_id, workflow_task_id,
  delivery_or_return, nominal, settlement_status_id, transaction_date, expected_settlement_date,
  arts_reference, input_user, input_date, last_updated_user, last_updated_date, failed_flag,
  failed_reason_code_id, failed_comment_id, reversal_movement_flag, valuation_percentage,
  is_gmi_adjustment, is_manual_flag

## Known Incidents (for testing)
- Duplicate booking: client_id=XYZ, date=2024-03-05
  Two bookings within 45 mins, amounts 232+33 and 265
  Delivery types R and D (split booking pattern)
```

---

## Step 4: How to Prompt Claude Code — Sprint by Sprint

The key to using Claude Code effectively is giving it **one focused task at a time**, not the entire system at once. Here's exactly what to type for each sprint:

---

### Sprint 1 — Project Foundation
```
# In your terminal, inside the project folder:
claude

# Then type:
"Set up the base project structure. Create:
1. requirements.txt with all dependencies from CLAUDE.md
2. A base FindingsObject dataclass in agents/base.py that all agents will return
3. A config.py that loads all settings from .env
4. A docker-compose.yml with PostgreSQL and ChromaDB services
5. A .env.example file with all required environment variables

Use the tech stack defined in CLAUDE.md."
```

---

### Sprint 1 — Database Agent + MCP SQL Tool
```
"Build the Database Agent and its MCP SQL Tool.

MCP SQL Tool (mcp_servers/sql_tool/server.py):
- Expose these tools via FastMCP:
  - query_movement_table(sql: str) -> list[dict]
  - query_dra_table(sql: str) -> list[dict]
  - query_booking_table(sql: str) -> list[dict]
  - get_client_history(client_id: str, days: int) -> list[dict]
- Connect to PostgreSQL using config from .env

Database Agent (agents/database_agent.py):
- LangChain agent that uses the SQL MCP tool
- Implement duplicate detection rule:
  Same client_id + value_date + currency, two bookings within 120 mins,
  matching amounts via split booking pattern (R + D delivery types)
- Call ML scoring MCP tool for anomaly score
- Return a FindingsObject

Test it against the sample data in /data/sample/ where
client XYZ had two bookings (232+33 and 265) on 2024-03-05."
```

---

### Sprint 2 — ML Models
```
"Build the ML models in /ml_models/.

1. isolation_forest.py:
   - IsolationForest from scikit-learn
   - Features: amount, time_gap_since_last_booking_mins, 
     client_booking_count_today, amount_vs_client_30d_avg,
     is_after_eod_boundary, dra_vs_movement_ratio
   - train(df) and predict(features) -> float methods
   - Save/load model with joblib

2. rolling_zscore.py:
   - compute_zscore(client_id, metric, window_days=30) -> float
   - Uses movement table history via SQL tool

3. ensemble_scorer.py:
   - Combines scores with these weights:
     rule_score: 0.35, isolation_forest: 0.20, 
     xgboost: 0.25, log_correlation: 0.10, kafka_anomaly: 0.10
   - Returns final confidence score 0.0-1.0

4. MCP ML Scoring Tool (mcp_servers/ml_scoring_tool/server.py):
   - run_isolation_forest(features: dict) -> float
   - compute_rolling_zscore(client_id: str, metric: str) -> float
   - get_anomaly_score(record_id: str) -> float"
```

---

### Sprint 3 — Log Agent
```
"Build the Log Agent and its MCP Log Parser Tool.

MCP Log Parser Tool (mcp_servers/log_parser_tool/server.py):
- read_log_file(path: str, start_time: datetime, end_time: datetime) -> list[LogEntry]
- filter_by_severity(entries: list, level: str) -> list[LogEntry]
- search_by_keyword(path: str, keywords: list[str], time_range: tuple) -> list[LogEntry]
- get_errors_for_client(client_id: str, log_path: str) -> list[LogEntry]

Key patterns to detect in logs:
- EOD boundary crossing: regex r'EOD.*boundary.*crossed.*clientId=(\w+)'
- Margin Gen timeout: r'MarginGen.*timeout.*clientId=(\w+)'  
- Zero margin: r'margin=0\.0.*clientId=(\w+)'
- Duplicate booking attempt: r'BookingId=(\w+).*already exists'

Log Agent (agents/log_agent.py):
- Takes client_id and time_range from orchestrator
- Returns FindingsObject with: errors_found, patterns_matched, 
  eod_boundary_crossed (bool), margin_gen_timeout (bool), severity_score"
```

---

### Sprint 4 — RAG Pipeline + Resolution Agent
```
"Build the full RAG pipeline and Resolution Agent.

RAG Indexer (rag/indexer.py):
- Use ChromaDB as vector store
- Embedding model: sentence-transformers all-MiniLM-L6-v2 (offline, no API needed)
- Chunk size: 512 tokens with 50 token overlap
- Store with metadata: date, incident_type, client_id, resolution_steps
- load_and_index_incident(doc: str, metadata: dict) method
- Pre-load the 3 sample incidents from /data/sample/incidents/

RAG Retriever (mcp_servers/rag_read_tool/server.py):
- semantic_search(query: str, top_k: int = 5) -> list[IncidentMatch]
- get_similar_incidents(embedding: list[float]) -> list[IncidentMatch]
- get_resolution_steps(incident_id: str) -> list[str]

Resolution Agent (agents/resolution_agent.py):
- Only instantiated when ensemble score > 0.5
- Takes all findings from other agents as input
- RAG retrieves top 3 similar past incidents
- LLM generates explanation and recommended action steps
- Returns: similar_incidents, explanation, recommended_steps, confidence"
```

---

### Sprint 5 — Orchestrator + Full Integration
```
"Build the Orchestrator Agent that ties everything together.

Orchestrator (agents/orchestrator_agent.py):
- Receives a trigger (scheduled, manual, or event-driven)
- Runs DatabaseAgent, LogAgent, KafkaAgent in parallel using asyncio.gather()
- Runs EmailAgent after with context from DB findings
- Passes all findings to ensemble_scorer.score()
- If score > 0.5: invokes ResolutionAgent
- If score > 0.8: auto-raises alert
- Returns a complete Alert object with all evidence

Alert object should contain:
- alert_id, timestamp, client_id, value_date
- ensemble_score, confidence_level (LOW/MEDIUM/HIGH)
- evidence from each agent
- resolution recommendation (if score > 0.5)
- audit_log of all agent actions taken"
```

---

### Sprint 6 — Streamlit Dashboard
```
"Build the Streamlit POC dashboard in ui/dashboard.py.

Layout:
- Header: 'Exposure Manager — Error Detection Agent'
- Sidebar: date picker, client filter, confidence threshold slider
- Main area: 
  - Alert cards showing: client_id, alert_type, confidence score 
    (color coded: red >0.8, amber 0.5-0.8, grey <0.5)
  - Expandable evidence panel per alert showing findings 
    from each agent (DB, logs, Kafka, emails)
  - Resolution recommendation section with similar past incidents
  - Buttons: 'Mark as Reviewed', 'Raise Case', 'Dismiss'
- Footer: last run time, total alerts today

Connect it to the orchestrator via FastAPI backend (api/main.py):
- POST /run-detection: triggers orchestrator manually
- GET /alerts: returns all alerts for date range
- PATCH /alerts/{id}: updates alert status"