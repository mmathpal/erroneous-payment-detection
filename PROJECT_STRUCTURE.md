# Project Structure - EM Anomaly Detection System

## Clean, Organized Structure

```
erroneous-payment-detection/
├── run_detection.py              # ⭐ Main entry point
│
├── config.py                     # Configuration settings
│
├── README.md                     # Project overview
├── QUICKSTART.md                 # Usage guide
├── DETECTION_SYSTEM.md           # Technical documentation
├── claude.md                     # Domain knowledge
│
├── src/
│   ├── agents/                   # 🎯 Detection Agents (Modularized)
│   │   ├── base.py              # Base classes (FindingsObject, Alert)
│   │   │
│   │   ├── rule_engine/         # Rule-Based Detection
│   │   │   ├── __init__.py
│   │   │   └── detector.py      # 8 deterministic rules
│   │   │
│   │   ├── ml_engine/           # ML-Based Detection
│   │   │   ├── __init__.py
│   │   │   └── detector.py      # Isolation Forest
│   │   │
│   │   ├── llm_engine/          # LLM Analysis
│   │   │   ├── __init__.py
│   │   │   └── analyzer.py      # OpenAI integration
│   │   │
│   │   └── orchestration/       # Orchestrator
│   │       ├── __init__.py
│   │       └── orchestrator.py  # Combines all engines
│   │
│   ├── database/                # 🗄️ Database Layer
│   │   ├── connection.py        # SQL Server connection
│   │   ├── setup_database.py   # Create tables
│   │   ├── load_csv_data.py    # Load test data
│   │   ├── create_trade_details.py  # Trade table setup
│   │   └── README.md            # Database docs
│   │
│   ├── mcp_servers/             # 🔧 MCP Tools
│   │   └── sql_server_tool/
│   │       ├── __init__.py
│   │       └── server.py        # SQL MCP server
│   │
│   └── data/                    # 📊 Sample Data
│       └── sample/
│           ├── collateral_movement.csv
│           └── arrangement_clearing_dra.csv
│
└── tests/                       # 🧪 Tests
    └── __init__.py
```

## Module Overview

### 1. Detection Agents (`src/agents/`)

Modular architecture - each engine in its own folder:

#### **Rule Engine** (`rule_engine/`)
- **detector.py**: 8 deterministic rules
  - Split booking duplicates
  - DRA duplicates
  - Trade duplicates
  - Date anomalies
  - Exposure anomalies
  - Expired trades
  - Negative values
  - PV discrepancies

#### **ML Engine** (`ml_engine/`)
- **detector.py**: Machine learning detection
  - Isolation Forest model
  - Feature engineering
  - Statistical anomaly detection

#### **LLM Engine** (`llm_engine/`)
- **analyzer.py**: AI-powered analysis
  - OpenAI GPT-4 integration
  - Business context explanations
  - Prioritization
  - Recommendations

#### **Orchestration** (`orchestration/`)
- **orchestrator.py**: Combines all engines
  - Runs rule + ML detection
  - Calculates ensemble scores
  - Groups findings by entity
  - Generates prioritized alerts
  - Adds LLM insights

### 2. Database Layer (`src/database/`)

SQL Server integration:
- **connection.py**: FreeTDS-based connection
- **setup_database.py**: Creates EM database & tables
- **load_csv_data.py**: Migrates CSV to SQL Server
- **create_trade_details.py**: Trade table with anomalies

### 3. MCP Servers (`src/mcp_servers/`)

Model Context Protocol tools:
- **sql_server_tool**: Query database, detect anomalies

### 4. Sample Data (`src/data/sample/`)

CSV files with test anomalies:
- **collateral_movement.csv**: 12 records, 4 split booking patterns
- **arrangement_clearing_dra.csv**: 8 records, 3 duplicate groups

## Database Tables (SQL Server)

### EM Database
- **trade** (11 records)
  - 8 different anomaly types
  - Duplicates, date errors, exposure issues, etc.

- **ci_collateral_movement** (12 records)
  - 4 split booking duplicate scenarios
  - R + D = D patterns

- **arrangement_clearing_dra** (8 records)
  - 3 duplicate groups
  - Same arrangement/generation/date

## Import Structure

### Easy Imports

```python
# Rule engine
from src.agents.rule_engine import RuleBasedDetector

# ML engine
from src.agents.ml_engine import MLAnomalyDetector

# LLM engine
from src.agents.llm_engine import LLMAnalyzer

# Orchestrator
from src.agents.orchestration import AnomalyDetectionOrchestrator

# Base classes
from src.agents.base import FindingsObject, Alert, ErrorType, SeverityLevel
```

## Files Removed (Cleanup)

Removed unnecessary files:
- ❌ `CLEANUP_SUMMARY.md` - Old planning
- ❌ `DEMO_GUIDE.md` - Old demo
- ❌ `POC_PLAN.md` - Old planning
- ❌ `POC_SUMMARY.md` - Old summary
- ❌ `demo_app_enhanced.py` - Old demo app
- ❌ `test_detector.py` - Old test
- ❌ `create_excel_template.py` - CSV approach
- ❌ `src/mcp_servers/csv_reader_tool/` - Replaced by SQL MCP
- ❌ `src/agents/database/` - Old structure
- ❌ `src/rag/` - Not used

## Key Features

### ✅ Modular Design
Each detection engine in its own module with:
- Clear separation of concerns
- Independent testing
- Easy to extend

### ✅ Clean Imports
```python
# Instead of long paths
from src.agents.orchestration import AnomalyDetectionOrchestrator

# Clean module imports
from src.agents.rule_engine import RuleBasedDetector
from src.agents.ml_engine import MLAnomalyDetector
from src.agents.llm_engine import LLMAnalyzer
```

### ✅ Production Ready
- SQL Server integration
- MCP tool support
- Ensemble scoring
- LLM analysis
- Comprehensive reporting

## Usage Patterns

### Run Complete Detection
```bash
python run_detection.py
```

### Use Individual Engines
```python
# Rule-based only
from src.agents.rule_engine import RuleBasedDetector
detector = RuleBasedDetector()
findings = detector.detect_all_anomalies()

# ML only
from src.agents.ml_engine import MLAnomalyDetector
detector = MLAnomalyDetector()
findings = detector.detect_all_anomalies()

# LLM analysis only
from src.agents.llm_engine import LLMAnalyzer
analyzer = LLMAnalyzer()
analysis = analyzer.analyze_anomalies(findings)
```

### Use Orchestrator (Recommended)
```python
from src.agents.orchestration import AnomalyDetectionOrchestrator

orchestrator = AnomalyDetectionOrchestrator(
    use_ml=True,
    use_llm=True,
    openai_api_key="your-key"
)

alerts = orchestrator.run_full_detection()
report = orchestrator.generate_report(alerts)
```

## Dependencies

```
# Core
pyodbc              # SQL Server
scikit-learn        # ML models
pandas              # Data processing
numpy               # Numerical computing

# Optional
openai              # LLM analysis (if using GPT-4)
```

## File Count Summary

**Total Essential Files**: ~20
- Python files: ~15
- Documentation: 4
- Configuration: 1

Clean, focused, production-ready structure!
