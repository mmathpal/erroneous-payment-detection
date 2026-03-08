# EM Anomaly Detection System

Complete anomaly detection solution combining Rule-Based, ML, and LLM approaches.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Orchestrator Agent                     │
│  - Coordinates all detectors                             │
│  - Calculates ensemble scores                            │
│  - Generates prioritized alerts                          │
└──────────────────┬──────────────────────────────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
┌───────▼──────┐ ┌─▼─────────┐ ┌─▼──────────┐
│ Rule-Based   │ │ ML-Based  │ │ LLM        │
│ Detector     │ │ Detector  │ │ Analyzer   │
│              │ │           │ │            │
│ - Duplicates │ │ -Isolation│ │ -Analysis  │
│ - Date errors│ │  Forest   │ │ -Insights  │
│ - Exposure   │ │ -Anomaly  │ │ -Priority  │
│ - PV checks  │ │  scoring  │ │ -Alerts    │
└──────┬───────┘ └─┬─────────┘ └─┬──────────┘
       │           │             │
       └───────────┼─────────────┘
                   │
           ┌───────▼────────┐
           │  SQL Server    │
           │  EM Database   │
           │                │
           │  - trade       │
           │  - ci_coll...  │
           │  - arr_dra     │
           └────────────────┘
```

## Components

### 1. Rule-Based Detector (`rule_based_detector.py`)
Deterministic rules for known patterns:
- **Split Booking Duplicates**: R + D = D pattern
- **DRA Duplicates**: Same arrangement/generation/date
- **Trade Duplicates**: Duplicate trade references
- **Date Anomalies**: Effective date > Maturity date
- **Exposure Anomalies**: Exposure > 5x notional
- **Expired Active Trades**: Active past maturity
- **Negative Values**: Invalid negative exposure
- **PV Discrepancies**: Component vs Used PV mismatch > 10%

**Confidence**: 0.75 - 1.0 (high confidence, deterministic)

### 2. ML Detector (`ml_detector.py`)
Isolation Forest for statistical anomalies:
- **Features**: exposure, notional, ratios, PV, dates
- **Model**: Sklearn Isolation Forest
- **Contamination**: 10-15% (configurable)
- **Detects**: Unknown patterns, outliers, statistical anomalies

**Confidence**: 0.4 - 0.9 (varies by anomaly score)

### 3. LLM Analyzer (`llm_analyzer.py`)
OpenAI GPT-4 for insights:
- **Explains** anomalies in business context
- **Prioritizes** findings by business impact
- **Generates** executive summaries
- **Recommends** actions

**Used for**: Analysis, not detection

### 4. Orchestrator (`orchestrator.py`)
Combines all agents:
- Runs rule-based + ML detection
- Calculates **ensemble score** (weighted average)
- Groups findings by entity
- Generates prioritized alerts
- Adds LLM insights

**Ensemble Weights**:
- Rule-based: 50%
- ML-based: 30%
- LLM boost: 20%

### 5. SQL MCP Server (`sql_server_tool/server.py`)
MCP tools for database access:
- `query_collateral_movement`
- `query_arrangement_dra`
- `query_trade`
- `detect_split_booking_duplicates`
- `detect_dra_duplicates`
- `detect_trade_anomalies`
- `execute_custom_query`

## Database Tables

### trade (11 records with 8 anomaly types)
- Duplicate trade refs
- Exposure mismatches (10x notional)
- Date errors (effective > maturity)
- Expired active trades
- Negative exposure
- PV discrepancies (73%)
- Currency mismatches

### ci_collateral_movement (12 records)
- 4 split booking duplicate patterns
- R + D = D scenarios

### arrangement_clearing_dra (8 records)
- 3 duplicate groups
- Same arrangement/generation/date

## Usage

### Quick Start

```bash
cd src/agents

# Set OpenAI API key (optional, for LLM analysis)
export OPENAI_API_KEY="your-key-here"

# Run complete detection
python orchestrator.py
```

### Individual Detectors

```python
# Rule-based only
from src.agents.rule_based_detector import RuleBasedDetector
detector = RuleBasedDetector()
findings = detector.detect_all_anomalies()

# ML only
from src.agents.ml_detector import MLAnomalyDetector
detector = MLAnomalyDetector(contamination=0.15)
findings = detector.detect_all_anomalies()

# LLM analysis
from src.agents.llm_analyzer import LLMAnalyzer
analyzer = LLMAnalyzer()
analysis = analyzer.analyze_anomalies(findings)
```

### Orchestrator (Recommended)

```python
from src.agents.orchestrator import AnomalyDetectionOrchestrator

# With all features
orchestrator = AnomalyDetectionOrchestrator(
    use_ml=True,
    use_llm=True,
    openai_api_key="your-key"
)

# Run detection
alerts = orchestrator.run_full_detection()

# Generate report
report = orchestrator.generate_report(alerts)
print(report)
```

## Output Format

### FindingsObject
Each detector returns findings in this format:
```python
{
    "agent_name": "RuleBasedDetector",
    "timestamp": "2026-03-07T...",
    "client_id": "772493",
    "value_date": "2026-02-18",
    "error_type": "split_booking_error",
    "severity": "high",
    "confidence_score": 0.95,
    "description": "Split booking duplicate detected...",
    "evidence": {...},
    "recommendation": "Investigate duplicate booking..."
}
```

### Alert Object
Orchestrator produces alerts:
```python
{
    "alert_id": "uuid",
    "ensemble_score": 0.87,
    "confidence_level": "high",
    "agent_findings": [FindingsObject, ...],
    "resolution_recommendation": "LLM analysis...",
    "status": "pending"
}
```

## Installation

```bash
# Install dependencies
pip install pyodbc scikit-learn pandas numpy openai

# Verify database connection
cd src/database
python -c "from connection import DatabaseConnection; DatabaseConnection(database='EM').test_connection()"
```

## Configuration

Edit `config.py`:
```python
# SQL Server
sql_server_host = "localhost"
sql_server_database = "EM"

# ML
isolation_forest_contamination = 0.1  # 10% expected anomalies

# Ensemble weights
rule_based_weight = 0.50
ml_based_weight = 0.30
llm_confidence_weight = 0.20

# Thresholds
alert_threshold = 0.8  # Auto-alert above this score
```

## Expected Results

With current test data, you should see:

**Rule-Based Findings**: ~18-20 anomalies
- 4 split booking duplicates
- 3 DRA duplicate groups
- 2 trade duplicates
- 1 date anomaly
- 1 exposure anomaly
- 1 expired active trade
- 1 negative exposure
- 1 PV discrepancy

**ML Findings**: ~3-5 anomalies (varies)
- Statistical outliers
- Pattern anomalies

**Total Alerts**: ~8-12 (grouped by entity)
**Critical/High**: 6-8 alerts

## Next Steps

1. **Test the system**:
   ```bash
   python src/agents/orchestrator.py
   ```

2. **Review anomaly_report_*.txt** generated

3. **Integrate with**:
   - Email notifications
   - Dashboard (Streamlit)
   - Case management system

4. **Tune parameters**:
   - ML contamination rate
   - Ensemble weights
   - Alert thresholds

5. **Add more rules** as you discover patterns

## Troubleshooting

**No ML findings**: Increase `contamination` parameter
**Too many false positives**: Increase rule confidence thresholds
**LLM errors**: Check OpenAI API key and quota
**Database errors**: Verify SQL Server connection

## Files Created

```
src/
├── agents/
│   ├── base.py                 (existing - FindingsObject, Alert)
│   ├── rule_based_detector.py  (NEW - 8 rule types)
│   ├── ml_detector.py          (NEW - Isolation Forest)
│   ├── llm_analyzer.py         (NEW - OpenAI analysis)
│   └── orchestrator.py         (NEW - combines all)
├── mcp_servers/
│   └── sql_server_tool/
│       └── server.py           (NEW - MCP SQL tools)
└── database/
    ├── connection.py           (updated - FreeTDS)
    ├── setup_database.py       (creates tables)
    ├── load_csv_data.py        (loads CSV)
    └── create_trade_details.py (creates trade table)
```

## Clean Files (Can Remove)

- `src/mcp_servers/csv_reader_tool/` (replaced by SQL MCP)
- `demo_app_enhanced.py` (old demo)
- `create_excel_template.py` (CSV approach deprecated)
- `test_detector.py` (old test)
- POC_*.md files (planning docs)

Keep CLAUDE.md for reference!
