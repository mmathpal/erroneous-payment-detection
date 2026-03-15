# ML Engine — Line-by-Line Code Explanation

This document explains every line of the three ML-related files in the Erroneous Payment Detection system.

---

## Table of Contents

1. [Architecture Summary](#architecture-summary)
2. [File 1: `ml_engine/detector.py` — Isolation Forest](#file-1-ml_enginedetectorpy)
3. [File 2: `risk_scoring/scorer.py` — Risk Scoring Engine](#file-2-risk_scoringscorerpy)
4. [File 3: `train_ml_model.py` — Training Script](#file-3-train_ml_modelpy)
5. [End-to-End Flow Diagram](#end-to-end-flow-diagram)
6. [Key Concepts Explained](#key-concepts-explained)

---

## Architecture Summary

The ML layer has two distinct components:

| Component | File | Type | Purpose |
|---|---|---|---|
| Isolation Forest detector | `ml_engine/detector.py` | Trained ML model | Finds statistically unusual trades |
| Risk Scorer | `risk_scoring/scorer.py` | Weighted formula | Combines ML + rule findings into one 0-100 score |
| Training script | `train_ml_model.py` | One-off script | Trains and saves the model to disk |

The Rule Engine (`rule_engine/detector.py`) runs in parallel with the ML engine. Both produce `FindingsObject` results that feed into the Risk Scorer.

---

## File 1: `ml_engine/detector.py`

### Imports and Setup (lines 1–21)

```python
#!/usr/bin/env python3
```
Shebang line — tells the OS to run this file with Python 3 if executed directly from the terminal.

```python
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
```
`__file__` is the path to this file itself (`detector.py`).
`.parent.parent.parent` walks three directories up: `ml_engine/` → `agents/` → `src/` → project root.
`sys.path.insert(0, ...)` adds the project root to Python's module search path so imports like `from src.agents.base import ...` work correctly regardless of where you run the script from.

```python
from datetime import datetime
```
Used to timestamp findings when they are created.

```python
from typing import List, Dict, Any
```
Type hint helpers. `List[FindingsObject]` makes the return type of functions self-documenting.

```python
import numpy as np
```
NumPy — used for array operations on scores (`.min()`, `.max()`) and replacing infinite values.

```python
from sklearn.ensemble import IsolationForest
```
The core ML algorithm. Imports scikit-learn's Isolation Forest class.

```python
from sklearn.preprocessing import StandardScaler
```
Feature normaliser. Ensures all features are on the same scale before feeding into the model.

```python
import pandas as pd
```
Pandas — used to hold the database results in a DataFrame so feature engineering (column operations) is easy.

```python
from src.agents.base import FindingsObject, ErrorType, SeverityLevel
```
Imports the shared data structures all agents use to report findings. Every agent must return `FindingsObject` instances so the orchestrator can handle them uniformly.

```python
from src.database.connection import DatabaseConnection
```
The database wrapper that executes SQL queries against the EM (Exposure Manager) SQL Server database.

---

### Class Definition and `__init__` (lines 24–38)

```python
class MLAnomalyDetector:
```
Defines a class grouping all ML detection logic. One instance is created by the orchestrator per detection run.

```python
def __init__(self, contamination: float = 0.15):
```
Constructor. `contamination=0.15` is the default — meaning "I expect about 15% of records to be anomalies." You can override this when creating the detector e.g. `MLAnomalyDetector(contamination=0.10)`.

```python
    self.db = DatabaseConnection(database="EM")
```
Opens a connection to the EM database. The `database="EM"` argument selects which database to connect to (configured in `.env`).

```python
    self.agent_name = "MLAnomalyDetector"
```
A string identifier stamped onto every `FindingsObject` this agent produces. The Risk Scorer uses this to distinguish ML findings from rule-based findings.

```python
    self.contamination = contamination
```
Stores the contamination parameter on the instance so `detect_trade_anomalies` can pass it to the model.

```python
    self.model = None
```
The Isolation Forest model starts as `None`. It is created and trained inside `detect_trade_anomalies`. There is no pre-loaded saved model — the model is retrained fresh on each run in this POC.

```python
    self.scaler = StandardScaler()
```
Creates a new StandardScaler instance. This will learn the mean and standard deviation of each feature from the data and use that to normalise them. It is also stored on the instance so the same scaler used for training can be used for prediction (important — if you scale with different parameters you get nonsense scores).

---

### `detect_trade_anomalies` — SQL Query (lines 40–64)

```python
def detect_trade_anomalies(self) -> List[FindingsObject]:
```
Main detection method. Return type annotation `-> List[FindingsObject]` documents what comes back.

```python
    query = """
        SELECT TOP 100
            src_trade_ref,
            exposure,
            notional_1,
            component_use_pv,
            used_pv
        FROM trade
        WHERE exposure IS NOT NULL
          AND notional_1 IS NOT NULL
          AND notional_1 != 0
    """
```
SQL Server query pulling at most 100 trades. `TOP 100` is a POC limit to keep things fast.
`WHERE exposure IS NOT NULL` — rows with null exposure would make `exposure_ratio` division fail.
`AND notional_1 != 0` — prevents division-by-zero when calculating `exposure_ratio`.

The five columns fetched:
- `src_trade_ref` — trade identifier (used as client_id in findings)
- `exposure` — the current risk exposure of the trade
- `notional_1` — the face value / notional amount of the trade
- `component_use_pv` — the PV that the margin component *should* use
- `used_pv` — the PV that was *actually* used in the margin calculation

```python
    results = self.db.execute_query(query)
```
Executes the query. Returns a list of dicts, one per row e.g. `[{"src_trade_ref": "TRD001", "exposure": 500000.0, ...}, ...]`.

```python
    if not results or len(results) < 10:
        return []
```
Safety check. If fewer than 10 records are returned, the model cannot learn meaningful patterns (Isolation Forest builds decision trees that need sufficient data variance). Returns an empty list — no findings.

```python
    df = pd.DataFrame(results)
```
Converts the list of dicts into a Pandas DataFrame. Now each column is addressable as `df['exposure']` etc., and row operations are vectorised.

---

### Feature Engineering (lines 69–79)

```python
    df['exposure_ratio'] = df['exposure'] / df['notional_1']
```
**New feature: exposure_ratio.**
For each row divides exposure by notional. If exposure = 500,000 and notional = 100,000 then ratio = 5.0 — this trade's risk is 5× its face value, which is unusual and worth flagging. A normal ratio might be 0.1–0.5.

```python
    df['pv_discrepancy'] = df.apply(
        lambda x: abs(x['component_use_pv'] - x['used_pv']) / x['component_use_pv']
        if x['component_use_pv'] != 0 else 0,
        axis=1
    )
```
**New feature: pv_discrepancy.**
`df.apply(..., axis=1)` runs a function on every row.
The lambda function calculates: `|expected_pv - actual_pv| / expected_pv`.
This is a percentage difference. If `component_use_pv` = 1,000,000 and `used_pv` = 800,000 then discrepancy = 0.20 (20%).
The `if x['component_use_pv'] != 0 else 0` guard prevents division-by-zero for rows where the expected PV is zero.

```python
    feature_cols = ['exposure', 'exposure_ratio', 'pv_discrepancy']
    X = df[feature_cols].fillna(0).replace([np.inf, -np.inf], 0)
```
`feature_cols` lists the three features the model will use. Raw `notional_1`, `component_use_pv`, `used_pv` are dropped — they are only used to *compute* the above features.
`.fillna(0)` — any NaN values (e.g. if a row somehow slipped through) become 0.
`.replace([np.inf, -np.inf], 0)` — if `notional_1` was somehow 0 despite the WHERE clause, the division would produce infinity. This replaces any infinity with 0.

---

### Scaling (line 82)

```python
    X_scaled = self.scaler.fit_transform(X)
```
`fit_transform` does two things in one call:
1. **fit** — learns the mean and std of each column from `X`
2. **transform** — subtracts the mean and divides by std, making every feature have mean=0 and std=1

Why this matters: `exposure` values might be in the millions (e.g. 1,500,000) while `pv_discrepancy` values are between 0 and 1. Without scaling, the model would pay almost all its attention to `exposure` and ignore `pv_discrepancy`. Scaling puts them on equal footing.

Example before/after:
```
Before: exposure=1500000,  exposure_ratio=5.0,  pv_discrepancy=0.25
After:  exposure=2.31,     exposure_ratio=3.14, pv_discrepancy=1.87
```

---

### Model Training and Prediction (lines 85–93)

```python
    self.model = IsolationForest(
        contamination=self.contamination,  # 0.15 = expect 15% anomalies
        random_state=42,                   # Fixed seed for reproducibility
        n_estimators=50                    # Build 50 decision trees
    )
```
Creates the Isolation Forest model. Not yet trained.

`contamination=0.15` — sets the decision boundary so approximately 15% of samples will be labelled anomalies.
`random_state=42` — any fixed integer makes results reproducible. Without this, results would vary each run.
`n_estimators=50` — builds 50 trees. More trees = more stable results but slower. 100 is used in the training script; 50 is used here for inference speed.

```python
    predictions = self.model.fit_predict(X_scaled)
```
`fit_predict` trains the model on `X_scaled` and immediately predicts on the same data.
Returns a numpy array of `+1` (normal) or `-1` (anomaly) for each row.
Example: `[1, 1, -1, 1, -1, 1, ...]`

**How Isolation Forest decides what is an anomaly:**
It builds trees by randomly selecting a feature and randomly selecting a split value. Anomalies tend to be isolated (separated from others) in very few splits, because they sit far from the dense cluster of normal data. The algorithm counts splits needed to isolate each point — few splits = anomaly.

```python
    scores = self.model.score_samples(X_scaled)
```
Returns a raw float score per row — more negative = more anomalous.
Example: `[-0.12, -0.09, -0.54, -0.11, -0.67, ...]`
These are not probabilities yet — they need normalising.

---

### Score Normalisation (lines 96–98)

```python
    min_score = scores.min()
    max_score = scores.max()
    normalized_scores = 1 - (scores - min_score) / (max_score - min_score) if max_score > min_score else scores
```
**Min-max normalisation, then inversion.**

Step 1 — `(scores - min_score) / (max_score - min_score)`:
This maps all scores to the range [0, 1] where 0 = most anomalous (lowest raw score) and 1 = most normal.

Step 2 — `1 - ...`:
Inverts it so 1 = most anomalous and 0 = most normal. More intuitive — higher score = more suspicious.

`if max_score > min_score else scores`:
Edge case guard. If all scores are identical (extremely unlikely but possible), skip normalisation to avoid division-by-zero.

Example:
```
Raw scores:        [-0.67, -0.54, -0.09]
After step 1:      [0.00,  0.22,  1.00]   (0 = most anomalous)
After inversion:   [1.00,  0.78,  0.00]   (1 = most anomalous)
```

---

### Building Findings (lines 101–136)

```python
    findings = []
    for idx, (pred, score) in enumerate(zip(predictions, normalized_scores)):
```
Iterates over every row simultaneously checking its prediction label and its normalised score.
`enumerate` gives the row index `idx` needed to look up the original data.
`zip(predictions, normalized_scores)` pairs each prediction with its corresponding score.

```python
        if pred == -1 and score > 0.5:
```
**Double filter:**
1. `pred == -1` — Isolation Forest must have labelled this row as an anomaly
2. `score > 0.5` — the normalised confidence must exceed 50%

This avoids reporting borderline cases. A record flagged by the model but with low confidence is noise, not signal.

```python
            row = results[idx]
```
Retrieves the original database row dict at the same index so we can access `src_trade_ref`, `exposure` etc.

```python
            severity = SeverityLevel.HIGH if score > 0.7 else SeverityLevel.MEDIUM
```
Two-tier severity mapping:
- Score > 0.7 → HIGH (top 30% of anomalies)
- Score 0.5–0.7 → MEDIUM

```python
            pv_disc = X.iloc[idx]['pv_discrepancy']
            if pv_disc > 0.2:
                error_type = ErrorType.PV_DISCREPANCY
                description = f"ML detected PV discrepancy for {row['src_trade_ref']}"
            else:
                error_type = ErrorType.UNKNOWN
                description = f"ML detected anomaly for {row['src_trade_ref']}"
```
The ML model doesn't inherently know *why* something is anomalous — it just knows it is different. This logic does a quick post-hoc check: if the PV discrepancy feature was high (>20%), we can attribute the anomaly to that. Otherwise we report it as `UNKNOWN` — something is off but we don't know what.

```python
            finding = FindingsObject(
                agent_name=self.agent_name,          # "MLAnomalyDetector"
                timestamp=datetime.now(),             # When this finding was created
                client_id=row['src_trade_ref'],       # Trade reference used as ID
                value_date=None,                      # ML doesn't know the value date
                error_type=error_type,                # PV_DISCREPANCY or UNKNOWN
                severity=severity,                    # HIGH or MEDIUM
                confidence_score=float(score),        # Normalised 0-1 score from model
                description=description,              # Human-readable summary
                evidence={                            # Raw data for investigation
                    "src_trade_ref": row['src_trade_ref'],
                    "anomaly_score": float(score),
                    "exposure": float(row['exposure']),
                    "notional": float(row['notional_1']),
                    "pv_discrepancy": float(X.iloc[idx]['pv_discrepancy'])
                },
                recommendation="Review trade details for potential anomaly."
            )
            findings.append(finding)
```
Creates a `FindingsObject` — the standard output format every agent must return. All fields are explained inline. The `evidence` dict is what gets shown in the dashboard's expandable panel.

---

### `detect_collateral_anomalies` (lines 140–148)

```python
def detect_collateral_anomalies(self) -> List[FindingsObject]:
    return []
```
Intentionally disabled for the POC. Placeholder for future collateral movement anomaly detection. Returns an empty list so `detect_all_anomalies` still works without changes.

---

### `detect_all_anomalies` (lines 150–160)

```python
def detect_all_anomalies(self) -> List[FindingsObject]:
    findings = []
    findings.extend(self.detect_trade_anomalies())
    findings.extend(self.detect_collateral_anomalies())
    return findings
```
The single public entry point the orchestrator calls. Aggregates results from all sub-detections into one flat list. `extend` appends all items from a list (vs `append` which would add the list as a nested element).

---

### `__main__` block (lines 163–175)

```python
if __name__ == "__main__":
```
This block only runs when the file is executed directly (`python detector.py`), not when imported as a module. Used for quick manual testing.

```python
    detector = MLAnomalyDetector(contamination=0.15)
    findings = detector.detect_all_anomalies()
    print(f"Total anomalies found: {len(findings)}\n")
    for finding in findings:
        print(f"[{finding.severity.value.upper()}] {finding.error_type.value}")
        print(f"  {finding.description}")
        print(f"  Confidence: {finding.confidence_score:.2f}")
```
Creates the detector, runs it, and prints a summary of each finding. `.value` on an Enum returns the string (e.g. `SeverityLevel.HIGH.value` → `"high"`). `.upper()` capitalises it for display.

---

## File 2: `risk_scoring/scorer.py`

### `RiskLevel` Enum (lines 26–32)

```python
class RiskLevel(Enum):
    CRITICAL = "critical"   # 90-100
    HIGH = "high"           # 70-89
    MEDIUM = "medium"       # 50-69
    LOW = "low"             # 30-49
    MINIMAL = "minimal"     # 0-29
```
Five named risk bands. Stored as an enum so code comparisons like `risk_level == RiskLevel.CRITICAL` are readable and type-safe. The string value (e.g. `"critical"`) is what gets displayed in the dashboard and stored in the database.

---

### `RiskScore` Dataclass (lines 35–57)

```python
@dataclass
class RiskScore:
    total_risk_score: float   # 0-100, the final headline number
    risk_level: RiskLevel     # CRITICAL / HIGH / MEDIUM / LOW / MINIMAL
    confidence_score: float   # 0-1, averaged from all detector confidence scores
    severity_score: float     # 0-100, based on error type
    impact_score: float       # 0-100, based on financial amounts
    frequency_score: float    # 0-100, based on how many findings
    urgency_score: float      # 0-100, based on time-sensitivity
    risk_factors: List[str]   # e.g. ["Multiple detection engines agree"]
    mitigating_factors: List[str]   # e.g. ["ML-only detection (statistical)"]
    calculation_timestamp: datetime
    breakdown: Dict[str, Any] # Per-component detail for the UI
```
`@dataclass` auto-generates `__init__`, `__repr__` etc. from the field annotations. `field(default_factory=list)` means each instance gets its own fresh list (not shared across instances, which is a common Python gotcha with mutable defaults).

---

### `RiskScorer` Weights (lines 82–88)

```python
WEIGHTS = {
    "severity": 0.30,    # 30% — what type of error?
    "impact": 0.30,      # 30% — how much money?
    "confidence": 0.25,  # 25% — how sure are the detectors?
    "frequency": 0.10,   # 10% — how many times detected?
    "urgency": 0.05      # 5%  — time pressure?
}
```
These are class-level constants (not instance variables). All weights sum to exactly 1.0. Changing these weights changes the behaviour of the entire system without touching any logic.

---

### `SEVERITY_SCORES` (lines 91–100)

```python
SEVERITY_SCORES = {
    ErrorType.DUPLICATE_BOOKING:    85,
    ErrorType.SPLIT_BOOKING_ERROR:  90,
    ErrorType.DRA_MISMATCH:         80,
    ErrorType.ZERO_MARGIN:          95,   # Highest — means no margin protection at all
    ErrorType.EOD_BOUNDARY_CROSSING: 75,
    ErrorType.MARGIN_SWING:         70,
    ErrorType.TIMEOUT:              60,
    ErrorType.UNKNOWN:              50    # Lowest — ML-only, uncertain cause
}
```
Domain expert knowledge encoded as constants. Zero margin (95) is the most severe because it means a position has no margin coverage, creating direct financial exposure. `UNKNOWN` (50) is lowest because we don't know the cause.

---

### `SEVERITY_MULTIPLIERS` (lines 103–108)

```python
SEVERITY_MULTIPLIERS = {
    SeverityLevel.CRITICAL: 1.0,   # No reduction
    SeverityLevel.HIGH:     0.85,  # 15% reduction
    SeverityLevel.MEDIUM:   0.65,  # 35% reduction
    SeverityLevel.LOW:      0.40   # 60% reduction
}
```
Applied on top of `SEVERITY_SCORES`. A `SPLIT_BOOKING_ERROR` with `HIGH` severity = `90 × 0.85 = 76.5`. The same error at `MEDIUM` severity = `90 × 0.65 = 58.5`. This allows the error type and the detector's confidence to both influence the severity component.

---

### `calculate_risk_score` (lines 114–198)

```python
def calculate_risk_score(self, findings: List[FindingsObject], entity_id: str = None) -> RiskScore:
```
Main public method. Takes all findings for one entity (e.g. one trade or one client) and returns a single consolidated `RiskScore`.

```python
    if not findings:
        return self._minimal_risk_score()
```
Short-circuit: no findings = no risk. Returns a pre-built minimal score rather than computing with an empty list.

```python
    severity_score   = self._calculate_severity_score(findings)
    impact_score     = self._calculate_impact_score(findings)
    confidence_score = self._calculate_confidence_score(findings)
    frequency_score  = self._calculate_frequency_score(findings)
    urgency_score    = self._calculate_urgency_score(findings)
```
Each component is calculated independently by a dedicated method. This separation makes each easier to understand, test, and tune independently.

```python
    total_risk_score = (
        severity_score   * self.WEIGHTS["severity"] +
        impact_score     * self.WEIGHTS["impact"] +
        confidence_score * 100 * self.WEIGHTS["confidence"] +
        frequency_score  * self.WEIGHTS["frequency"] +
        urgency_score    * self.WEIGHTS["urgency"]
    )
```
The weighted sum. Note `confidence_score * 100` — confidence is 0–1 but all other scores are 0–100, so it must be scaled up before weighting. Without this, confidence would contribute 25× less than intended.

---

### `_calculate_severity_score` (lines 200–222)

```python
def _calculate_severity_score(self, findings: List[FindingsObject]) -> float:
    scores = []
    for finding in findings:
        base_score  = self.SEVERITY_SCORES.get(finding.error_type, 50)   # Look up error type score
        multiplier  = self.SEVERITY_MULTIPLIERS.get(finding.severity, 0.5)  # Look up severity multiplier
        score       = base_score * multiplier
        scores.append(score)
    return max(scores)  # Return worst case, not average
```
Uses `max()` not `average()` — the risk is defined by the worst finding, not the typical one. If 9 findings are low risk and 1 is critical, the severity score reflects the critical one.

---

### `_calculate_impact_score` (lines 224–264)

```python
def _calculate_impact_score(self, findings: List[FindingsObject]) -> float:
    impact_score = 50.0  # Start at medium, can only go up
    for finding in findings:
        evidence = finding.evidence or {}
        if "exposure" in evidence:
            exposure = abs(float(evidence.get("exposure", 0)))
            if exposure > 1_000_000:  impact_score = max(impact_score, 90)
            elif exposure > 500_000:  impact_score = max(impact_score, 75)
            elif exposure > 100_000:  impact_score = max(impact_score, 60)
```
Checks the `evidence` dict for financial amounts. Uses `max()` so the score can only increase as more findings are reviewed. Uses `abs()` because negative exposures are also large in magnitude.

```python
        if finding.error_type in [ErrorType.DUPLICATE_BOOKING, ErrorType.SPLIT_BOOKING_ERROR, ErrorType.ZERO_MARGIN]:
            impact_score = max(impact_score, 80)
```
Certain error types automatically push impact to at least 80, regardless of the financial amount, because they have inherently high business impact.

```python
        if "effective_date" in evidence and "maturity_date" in evidence:
            impact_score = max(impact_score, 95)
```
Date anomalies (effective date after maturity date) are always near-critical — this is a fundamental data integrity failure.

---

### `_calculate_confidence_score` (lines 266–276)

```python
def _calculate_confidence_score(self, findings: List[FindingsObject]) -> float:
    confidences = [f.confidence_score for f in findings]
    return sum(confidences) / len(confidences)
```
Simple average of all detector confidence scores. If the Rule Engine reports 1.0 and the ML Engine reports 0.72, the combined confidence is `(1.0 + 0.72) / 2 = 0.86`.

---

### `_calculate_frequency_score` (lines 278–294)

```python
def _calculate_frequency_score(self, findings: List[FindingsObject]) -> float:
    count = len(findings)
    if count >= 5:   return 100.0
    elif count >= 3: return 75.0
    elif count >= 2: return 50.0
    else:            return 25.0
```
Step function — not a smooth curve. 1 finding = 25, 2 findings = 50, etc. If 5+ detectors/rules flag the same entity, it gets max frequency score. This rewards consensus across multiple independent checks.

---

### `_calculate_urgency_score` (lines 296–318)

```python
def _calculate_urgency_score(self, findings: List[FindingsObject]) -> float:
    urgency = 50.0  # Default medium
    for finding in findings:
        if finding.severity == SeverityLevel.CRITICAL: urgency = max(urgency, 95)
        elif finding.severity == SeverityLevel.HIGH:   urgency = max(urgency, 75)
        if finding.error_type in [ErrorType.ZERO_MARGIN, ErrorType.EOD_BOUNDARY_CROSSING]:
            urgency = max(urgency, 90)
    return urgency
```
Zero margin and EOD boundary crossings both push urgency to 90 because they are time-sensitive — zero margin must be rectified before end of day, and EOD boundary crossings can cause settlement failures.

---

### `_identify_risk_factors` and `_identify_mitigating_factors` (lines 333–395)

These produce human-readable strings for the dashboard "Risk Factors" panel.

```python
if len(findings) >= 3:
    factors.append("Multiple detection engines agree")
```
Consensus across engines is a strong positive signal.

```python
if all(f.agent_name == "MLAnomalyDetector" for f in findings):
    factors.append("ML-only detection (statistical)")
```
This appears in *mitigating* factors — if only the ML flagged it and no rule matched, it's more likely to be a false positive. The risk score is lower as a result.

---

## File 3: `train_ml_model.py`

This script is run once (or periodically) to train a model and save it to disk. The main `detector.py` retrains on every run, but this script trains a more robust version (100 estimators vs 50) that can be loaded without retraining.

### `train_trade_anomaly_model` (lines 28–137)

```python
def train_trade_anomaly_model(contamination: float = 0.15):
```
Standalone training function. Uses same logic as the detector but:
1. Fetches all records (no `TOP 100` limit)
2. Uses `n_estimators=100` (more stable)
3. Saves the model to disk with `joblib`

```python
    df['exposure_ratio'] = df['exposure'] / df['notional_1']
    df['pv_discrepancy'] = df.apply(...)
    feature_cols = ['exposure', 'exposure_ratio', 'pv_discrepancy']
    X = df[feature_cols].fillna(0).replace([np.inf, -np.inf], 0)
```
Identical feature engineering to `detector.py`. Must match exactly — if you change features here, you must change them in the detector too or the saved model will be useless.

```python
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
```
Fits a new scaler on all the training data (not just TOP 100).

```python
    model = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=100    # Double the estimators used at inference time
    )
    model.fit(X_scaled)
```
Trains on the full dataset. Note `fit()` not `fit_predict()` — we don't need predictions here, just a trained model.

```python
    model_artifact = {
        'model': model,
        'scaler': scaler,
        'feature_names': feature_cols,
        'contamination': contamination,
        'n_estimators': 100,
        'trained_date': datetime.now().isoformat(),
        'training_samples': len(df),
        'detected_anomalies': int(anomaly_count)
    }
    joblib.dump(model_artifact, model_path)
```
Saves everything needed to reproduce the model's predictions: the model itself, the scaler (must use same scaler at inference), metadata for auditability. `joblib` is preferred over `pickle` for scikit-learn models as it handles numpy arrays more efficiently.

---

## End-to-End Flow Diagram

```
Database (SQL Server)
        │
        ▼
┌───────────────────┐     ┌──────────────────────┐
│  RuleBasedDetector│     │  MLAnomalyDetector   │
│  (3 SQL rules)    │     │  (Isolation Forest)  │
│  confidence=1.0   │     │  confidence=0.5-1.0  │
└────────┬──────────┘     └──────────┬───────────┘
         │                           │
         │    List[FindingsObject]   │
         └─────────────┬─────────────┘
                       │
                       ▼
              ┌────────────────┐
              │   RiskScorer   │
              │                │
              │ severity  ×0.30│
              │ impact    ×0.30│
              │ confidence×0.25│
              │ frequency ×0.10│
              │ urgency   ×0.05│
              └───────┬────────┘
                      │
                      ▼
              RiskScore (0-100)
              + risk_level (CRITICAL/HIGH/MEDIUM/LOW/MINIMAL)
              + risk_factors
              + mitigating_factors
              + breakdown (per-component detail)
                      │
                      ▼
              Orchestrator → Dashboard
```

---

## Key Concepts Explained

### What is Isolation Forest?

Isolation Forest is an **unsupervised** anomaly detection algorithm — it requires no labelled training data (no "these are good, these are bad" examples).

**Core idea:** Anomalies are easy to isolate. Build random decision trees and count how many splits are needed to isolate each data point. Points requiring few splits are anomalies because they sit far from the dense cluster of normal data.

```
Normal data (clustered):                 Anomaly (isolated):
  ●●●●●●                                     ○
  ●●●●●●                                   (needs only 2 splits to isolate)
  ●●●●●●
(needs many splits to isolate any one point)
```

### Why StandardScaler?

Without scaling:
- `exposure` values: 100,000 to 5,000,000
- `pv_discrepancy` values: 0.0 to 1.0

The model would treat a 1-unit difference in exposure as far more significant than a 1-unit difference in pv_discrepancy, even though 1.0 is the maximum possible pv_discrepancy. Scaling brings both to the same range so the model can assess them fairly.

### Why `contamination=0.15`?

This is a prior belief: "I expect about 15% of my trade data to contain some form of anomaly." Set it too low (e.g. 0.01) and the model will only flag the most extreme outliers. Set it too high (e.g. 0.50) and it flags half the database, creating too many false positives.

For a POC, 15% is a reasonable starting point. In production this should be tuned against labelled historical data.

### Why is ML confidence always lower than rules?

Rules have `confidence_score=1.0` because they are deterministic — if `R + D = D` then it IS a split booking error, no uncertainty. ML has `confidence_score=0.5–1.0` because it is statistical — it found something unusual but cannot be certain it is erroneous. This is why ML-only detections are listed in `mitigating_factors` and reduce the final risk score slightly.
