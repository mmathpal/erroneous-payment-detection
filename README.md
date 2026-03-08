# Erroneous Payment Detection System - POC

A proof-of-concept intelligent system for detecting erroneous payments in Exposure Manager (EM) using AI agents, RAG (Retrieval-Augmented Generation), and rule-based detection.

**Status**: ✅ POC Complete | **Team**: Barclays Capital - OTC Clearing | **Timeline**: 3-Day POC

---

## POC Scope

This POC demonstrates automated detection of erroneous payments in Exposure Manager with:

### ✅ Implemented Features
- **Duplicate Booking Detection**: Detects split booking patterns (R+D delivery types) within configurable time windows
- **Zero Margin Detection**: Flags when Margin Gen sends 0 margin (100% confidence)
- **DRA Mismatch Detection**: Compares DRA amounts vs movement totals
- **RAG-Powered Recommendations**: Provides resolution steps based on similar past incidents
- **Interactive Dashboard**: Real-time monitoring with Streamlit
- **Evidence-Based Alerts**: Complete proof for operations team

### 🎯 POC Success
Successfully detected the **real XYZ123 incident** from March 5, 2024:
- User booked 232+33 = 265 (R delivery type) at 10:30
- Same user booked 265 (D delivery type) at 11:15 (45 mins later)
- **AI Confidence**: 95% (split booking pattern detected)

---

## Project Structure

```
erroneous-payment-detection/
├── src/
│   ├── agents/
│   │   ├── base.py              # Core data structures (FindingsObject, ErrorType)
│   │   └── database/
│   │       └── detector.py      # Database detection logic
│   ├── mcp_servers/
│   │   └── excel_reader_tool/
│   │       └── server.py        # Excel reading MCP tool
│   ├── rag/
│   │   └── simple_rag.py        # RAG system with ChromaDB
│   └── data/
│       └── sample/
│           ├── movements.xlsx    # Payment movements
│           ├── dra.xlsx          # DRA calculations
│           ├── bookings.xlsx     # Booking records
│           └── past_incidents.xlsx  # Historical incidents for RAG
├── config.py                     # Configuration settings
├── demo_app_enhanced.py          # Streamlit dashboard with RAG
├── test_detector.py              # Command-line test script
├── DEMO_GUIDE.md                 # Complete demo flow (5-7 mins)
├── POC_SUMMARY.md                # Executive summary
└── pyproject.toml                # Dependencies
```

---

## Quick Start

### Prerequisites
- Python 3.13+
- pip or Poetry

### Installation

```bash
# Clone repository
cd erroneous-payment-detection

# Install dependencies
pip install pandas openpyxl structlog sentence-transformers chromadb streamlit

# OR use Poetry
poetry install
```

### Run the Demo

**Option 1: Interactive Dashboard**
```bash
streamlit run demo_app_enhanced.py
```
Dashboard opens at: http://localhost:8501

**Option 2: Command-line Test**
```bash
python test_detector.py
```

---

## Detection Capabilities

### 1. Duplicate Booking Detection
- **Pattern**: Same client, date, currency, amount within time window
- **Special Detection**: Split booking pattern (R+D delivery types)
- **Confidence**: 95% (split patterns), 85% (regular duplicates)
- **Evidence**: Booking IDs, timestamps, amounts, delivery types

### 2. Zero Margin Detection
- **Pattern**: DRA amount = 0.0
- **Indicator**: Margin Gen error
- **Confidence**: 100% (rule-based)
- **Evidence**: Client ID, DRA amount, methodology

### 3. DRA Mismatch Detection
- **Pattern**: DRA amount ≠ sum of movements (threshold: $1)
- **Indicator**: Calculation error
- **Confidence**: 90%
- **Evidence**: DRA vs movements comparison

---

## Technology Stack

### Core
- **Python 3.13**: Modern Python features
- **pandas**: Data processing and analysis
- **openpyxl**: Excel file reading

### AI/RAG
- **sentence-transformers**: Offline embedding generation (all-MiniLM-L6-v2)
- **ChromaDB**: Vector store for similarity search
- **structlog**: Structured logging

### UI
- **Streamlit**: Interactive dashboard
- **plotly**: Visualizations (future)

### Configuration
- **pydantic-settings**: Type-safe configuration
- **python-dotenv**: Environment management

---

## Configuration

Key settings in `config.py`:

```python
duplicate_time_window_minutes = 120  # 2-hour window for duplicate detection
fraud_threshold = 0.7               # Alert threshold
alert_threshold = 0.8               # High-priority alerts

# Future ML ensemble weights
rule_based_weight = 0.35
isolation_forest_weight = 0.20
xgboost_weight = 0.25
log_correlation_weight = 0.10
kafka_anomaly_weight = 0.10
```

---

## Demo Results

### Test Data Summary
- **6 movements** (including XYZ123 split booking: 232 + 33 + 265)
- **5 DRA records** (including 2 zero margin cases)
- **5 bookings** (including XYZ123 duplicates at 10:30 and 11:15)
- **3 past incidents** (for RAG similarity search)

### Detection Results
```
🚨 4 ERRORS DETECTED:

1. [HIGH] Duplicate Booking - XYZ123
   Confidence: 95%
   Pattern: Split booking (R+D), 45 mins apart, $265
   → Real incident from manager's conversation!

2. [CRITICAL] Zero Margin - ZZZ000
   Confidence: 100%
   Likely Margin Gen error

3-4. [MEDIUM] DRA Mismatch - XYZ123, GHI999
   Confidence: 90%
   DRA amounts don't match movement totals
```

---

## Next Phase: Production Extension

### Phase 2 (Weeks 1-2)
- **Database Integration**: Connect to real EM PostgreSQL
- **Log Agent**: Parse EM application logs for errors
- **Kafka/MARK Agent**: Monitor Margin Gen responses real-time

### Phase 3 (Weeks 3-4)
- **Email Agent**: Search Exchange for payment communications (MS Graph API)
- **ML Models**: Train Isolation Forest, XGBoost on historical data
- **Orchestrator**: Coordinate all agents with ensemble scoring

### Phase 4 (Production)
- **Case Management**: Auto-raise JIRA tickets
- **Alerting**: Email/Slack notifications
- **Monitoring**: Metrics dashboard
- **Audit Trail**: Complete detection history

---

## Documentation

- **DEMO_GUIDE.md**: Complete demo walkthrough (5-7 minutes) with talking points
- **POC_SUMMARY.md**: Executive summary with business value and architecture
- **POC_PLAN.md**: Original 3-day implementation plan
- **src/data/sample/EXCEL_DATA_FORMAT.md**: Data format specifications

---

## Architecture

### Current POC
```
┌─────────────────────────────────────┐
│      Database Detector              │
│   (duplicate, zero margin, DRA)     │
└─────────────┬───────────────────────┘
              │
    ┌─────────┴─────────┐
    │                   │
┌───▼──────────┐  ┌─────▼─────────┐
│ Excel Reader │  │  Simple RAG   │
│  MCP Tool    │  │  (ChromaDB)   │
└──────────────┘  └───────────────┘
```

### Future Production Architecture
```
┌─────────────────────────────────────┐
│      ORCHESTRATOR AGENT             │
│   (ensemble scoring, decisions)     │
└─────────────────────────────────────┘
              │
    ┌─────────┼─────────┬─────────┐
    │         │         │         │
┌───▼───┐ ┌──▼───┐ ┌───▼───┐ ┌───▼────┐
│  DB   │ │ Log  │ │Kafka │ │ Email  │
│ Agent │ │Agent │ │Agent │ │ Agent  │
└───┬───┘ └──┬───┘ └───┬───┘ └───┬────┘
    │        │         │         │
┌───▼────────▼─────────▼─────────▼────┐
│         MCP TOOLS                    │
│  SQL | Log Parser | Kafka | Graph   │
│  RAG | ML Scoring | LLM Reasoning   │
└──────────────────────────────────────┘
```

---

## Testing

### Run Detection Tests
```bash
python test_detector.py
```

### Run Dashboard
```bash
streamlit run demo_app_enhanced.py
```

### Future: Unit Tests
```bash
poetry run pytest
poetry run pytest --cov=src --cov-report=html
```

---

## Business Value

### Immediate Benefits
- **Automated Detection**: Catches errors before payment settlement
- **Real-time Alerts**: Operations team notified immediately
- **Evidence-Based**: Complete proof for investigation
- **Confidence Scoring**: Prioritize high-confidence cases

### Risk Mitigation
- **Financial**: Prevent duplicate payments (like XYZ123 incident)
- **Operational**: Flag margin calculation errors early
- **Compliance**: Full audit trail of all detections
- **Reputational**: Catch before client notices

### Efficiency Gains
- **Time Savings**: Automated vs manual review
- **Accuracy**: AI detects patterns humans miss
- **Scalability**: Handles increasing transaction volumes
- **Resolution Speed**: RAG provides instant recommendations

---

## Development

### Code Quality
```bash
# Format code
poetry run black src/
poetry run ruff check src/

# Type checking
poetry run mypy src/
```

### Pre-commit Hooks (Future)
```bash
poetry run pre-commit install
poetry run pre-commit run --all-files
```

---

## Project Status

**✅ POC Complete** - Ready for stakeholder demo

### Completed
- ✅ Duplicate booking detection (XYZ123 pattern)
- ✅ Zero margin detection
- ✅ DRA mismatch detection
- ✅ RAG system with similarity search
- ✅ Interactive Streamlit dashboard
- ✅ Complete documentation

### Pending (Post-POC)
- 🔜 Database integration (PostgreSQL)
- 🔜 Log parsing agent
- 🔜 Kafka monitoring agent
- 🔜 Email search agent
- 🔜 ML models (Isolation Forest, XGBoost)
- 🔜 Case management integration (JIRA)

---

## Contact

**Developer**: Sr. Software Engineer
**Team**: Exposure Manager, Barclays Capital
**Department**: OTC Clearing
**Timeline**: 3-Day POC (Completed)

---

## License

Internal Barclays Capital Project

---

## Acknowledgments

Built for Exposure Manager team to demonstrate AI-powered erroneous payment detection capabilities. Successfully detected real XYZ123 incident pattern from March 5, 2024.
