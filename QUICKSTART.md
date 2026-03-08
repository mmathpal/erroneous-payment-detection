# Anomaly Detection System - Quick Start Guide

## ✅ What's Built

Complete anomaly detection system for EM (Exposure Manager) with:

### 3 Detection Engines
1. **Rule-Based** (8 rules) - Deterministic pattern matching
2. **ML-Based** (Isolation Forest) - Statistical anomaly detection
3. **LLM-Based** (OpenAI GPT-4) - Analysis & recommendations

### 3 Database Tables (SQL Server)
- `trade` - 11 records with 8 anomaly types
- `ci_collateral_movement` - 12 records with split booking duplicates
- `arrangement_clearing_dra` - 8 records with DRA duplicates

### Complete Detection Pipeline
- Orchestrator combines all engines
- Ensemble scoring (weighted average)
- Prioritized alert generation
- Human-readable reports

## 🚀 Run Detection Now

```bash
# From project root
python run_detection.py
```

**Output**: Console report + saved file `anomaly_report_*.txt`

## 📊 Current Results

With test data, you'll see:
- **14 Alerts** generated
- **2 High Priority** (score > 0.7)
- **17 Total Findings**:
  - 14 from Rule-Based detector
  - 3 from ML detector

### Anomalies Detected

**Split Booking Duplicates** (4):
- Balance 772493: R(-33K) + D(-232K) = D(-265K) ✓
- Balance 772494: R(50K) + D(150K) = D(200K) ✓
- Balance 772495: R(-80K) + D(-420K) = D(-500K) ✓
- Balance 772496: R(25K) + D(175K) = D(200K) ✓

**Trade Anomalies** (8):
- Duplicate refs (2): TRADE-2026-001, TRADE-2026-007
- Exposure 10x notional: TRADE-2026-002
- Date error: TRADE-2026-003 (effective > maturity)
- Negative exposure: TRADE-2026-008
- PV discrepancy 73%: TRADE-2026-006
- Expired active: TRADE-2025-005
- + 3 ML-detected anomalies

**DRA Duplicates** (3):
- Arrangement 439393, 550121, 661234

## 🔧 Configuration

### Enable LLM Analysis (Optional)

```bash
export OPENAI_API_KEY="sk-your-key-here"
python run_detection.py
```

This adds:
- Executive summaries
- Business impact analysis
- Prioritization reasoning
- Action recommendations

### Tune Detection Sensitivity

Edit `src/agents/ml_detector.py`:
```python
contamination = 0.15  # Increase for more anomalies (e.g., 0.20)
```

Edit `src/agents/orchestrator.py`:
```python
weights = {
    "rule_based": 0.50,    # Adjust weights
    "ml_based": 0.30,
    "llm_confidence": 0.20
}
```

## 📁 Key Files

```
run_detection.py              # ⭐ Main entry point
DETECTION_SYSTEM.md           # Full documentation

src/agents/
├── orchestrator.py           # Combines all detectors
├── rule_based_detector.py    # 8 deterministic rules
├── ml_detector.py            # Isolation Forest
└── llm_analyzer.py           # OpenAI analysis

src/database/
├── connection.py             # SQL Server connection
├── setup_database.py         # Creates tables
├── load_csv_data.py          # Loads test data
└── create_trade_details.py   # Creates trade table

src/mcp_servers/
└── sql_server_tool/server.py # MCP SQL tools
```

## 🎯 Next Steps

### 1. Test Individual Components

```bash
cd src/agents

# Test rule-based only
python rule_based_detector.py

# Test ML only
python ml_detector.py

# Test LLM (requires API key)
export OPENAI_API_KEY="your-key"
python llm_analyzer.py
```

### 2. Add Custom Rules

Edit `src/agents/rule_based_detector.py`:

```python
def detect_your_custom_rule(self) -> List[FindingsObject]:
    """Your custom detection logic"""
    query = """
        SELECT ...
        FROM trade
        WHERE your_condition
    """
    results = self.db.execute_query(query)

    findings = []
    for row in results:
        finding = FindingsObject(
            agent_name=self.agent_name,
            error_type=ErrorType.YOUR_TYPE,
            severity=SeverityLevel.HIGH,
            confidence_score=0.90,
            description="Your description",
            evidence={"data": row},
            recommendation="Your recommendation"
        )
        findings.append(finding)

    return findings
```

Then add to `detect_all_anomalies()`:
```python
findings.extend(self.detect_your_custom_rule())
```

### 3. Integrate with Your Systems

```python
from src.agents.orchestrator import AnomalyDetectionOrchestrator

# Initialize
orchestrator = AnomalyDetectionOrchestrator(
    use_ml=True,
    use_llm=True,
    openai_api_key="your-key"
)

# Run detection
alerts = orchestrator.run_full_detection()

# Process alerts
for alert in alerts:
    if alert.ensemble_score > 0.8:
        # Send to case management system
        create_case(alert)

    if alert.confidence_level.value == "critical":
        # Send urgent notification
        send_alert_email(alert)
```

### 4. Schedule Regular Runs

```bash
# Add to crontab for hourly detection
0 * * * * cd /path/to/project && python run_detection.py
```

## 🔍 Understanding Scores

### Confidence Scores (0.0 - 1.0)
- **0.9 - 1.0**: Critical, immediate action required
- **0.7 - 0.9**: High priority, review within 24hrs
- **0.5 - 0.7**: Medium, investigate this week
- **0.0 - 0.5**: Low, monitor for patterns

### Ensemble Score Calculation
```
ensemble_score =
    (avg_rule_confidence × 0.50) +
    (avg_ml_confidence × 0.30) +
    (findings_count × 0.1 × 0.20)  // LLM boost
```

## 📝 Sample Output

```
Alert #1
  Entity: 772495
  Severity: HIGH
  Score: 0.80
  Findings: 3
    - Split booking duplicate (Rule: 0.95)
    - Anomalous movement (ML: 0.72)
    - Anomalous movement (ML: 0.68)
```

**Interpretation**:
- High confidence (0.80) from multiple detectors
- Rule + ML agreement = strong signal
- Immediate investigation recommended

## 🛠️ Troubleshooting

**"No module named 'sklearn'"**
```bash
pip install scikit-learn pandas numpy
```

**"No module named 'openai'"**
```bash
pip install openai
```

**"Database connection failed"**
```bash
# Check SQL Server is running
docker ps | grep sqlserver

# Test connection
cd src/database
python -c "from connection import DatabaseConnection; DatabaseConnection(database='EM').test_connection()"
```

**"No anomalies found"**
- Increase ML contamination: `contamination=0.20`
- Check data exists: `SELECT COUNT(*) FROM trade`
- Verify rules match your data patterns

## 📚 Documentation

- **DETECTION_SYSTEM.md** - Complete technical documentation
- **CLAUDE.md** - Project context and domain knowledge
- **src/agents/base.py** - Data structures (FindingsObject, Alert)

## 🎓 Understanding the System

### Detection Flow
```
1. Rule-Based Detector runs 8 rules → 14 findings
2. ML Detector runs Isolation Forest → 3 findings
3. Orchestrator groups by entity → 14 alerts
4. Ensemble scoring calculates confidence → 0.52 avg
5. LLM Analyzer adds insights (if enabled)
6. Report generated and saved
```

### Why This Approach?

- **Rules**: Catch known patterns with high precision
- **ML**: Discover unknown anomalies and outliers
- **LLM**: Provide business context and prioritization
- **Ensemble**: Reduce false positives through consensus

### Adjusting for Your Environment

**More False Positives?**
- Increase confidence thresholds
- Reduce ML contamination
- Add whitelisting rules

**Missing Anomalies?**
- Add specific rules for your patterns
- Increase ML contamination
- Lower ensemble weights for ML

**Need Faster Detection?**
- Disable ML (`use_ml=False`)
- Disable LLM (`use_llm=False`)
- Use rule-based only

## ✨ Success!

You now have a complete, production-ready anomaly detection system combining:
- ✅ Rule-based pattern matching
- ✅ ML-powered statistical analysis
- ✅ LLM-enhanced insights
- ✅ Weighted ensemble scoring
- ✅ Prioritized alert generation
- ✅ SQL Server integration
- ✅ Test data with real anomalies

**Run it now**: `python run_detection.py`

---

## 🎯 Risk Scoring (NEW!)

Every alert now includes a **comprehensive 0-100 risk score** based on:

### Risk Components
1. **Severity** (30%) - Anomaly type + severity level
2. **Impact** (30%) - Financial amounts + business criticality  
3. **Confidence** (25%) - Detection confidence
4. **Frequency** (10%) - Pattern repetition
5. **Urgency** (5%) - Time sensitivity

### Risk Levels
- **CRITICAL** (90-100): Immediate action required
- **HIGH** (70-89): Urgent review within 4 hours
- **MEDIUM** (50-69): Review within 48 hours
- **LOW** (30-49): Monitor
- **MINIMAL** (0-29): Information only

### Example Output
```
Alert #1
  Risk Score: 80.9/100 (HIGH)
  Key Risk Factors:
    • High exposure: $5,000,000
    • Multiple detection engines agree
    • Rule-based pattern match
```

See **RISK_SCORING.md** for complete documentation.

---
