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
| Training script | `train_ml_model.py` | Run once / periodically | Trains on full dataset, saves `.pkl` to `models/` |
| Isolation Forest detector | `ml_engine/detector.py` | Loads pre-trained model | Loads `.pkl` from disk, runs inference only — no retraining |
| Risk Scorer | `risk_scoring/scorer.py` | Weighted formula | Combines ML + rule findings into one 0-100 score |

**Important workflow:** You must run `train_ml_model.py` before the detector can be used. The detector will raise a `FileNotFoundError` if the `.pkl` file does not exist.

```
Step 1 (once):   poetry run python train_ml_model.py   → saves models/trade_anomaly_model.pkl
Step 2 (anytime): poetry run python src/agents/ml_engine/detector.py  → loads .pkl, runs detection
```

The Rule Engine (`rule_engine/detector.py`) runs in parallel with the ML engine. Both produce `FindingsObject` results that feed into the Risk Scorer.

---

## File 1: `ml_engine/detector.py`

### Imports and Setup (lines 1–24)

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
Type hint helpers. `List[FindingsObject]` makes the return type of functions self-documenting. `Dict` and `Any` are imported but not directly used in this file — they are kept for consistency with other agents and in case evidence dicts are typed explicitly in future.

```python
import numpy as np
```
NumPy — used for array operations on scores (`.min()`, `.max()`) and replacing infinite values.

```python
import joblib
```
Used to load the pre-trained model from the `.pkl` file saved by `train_ml_model.py`. `joblib` is preferred over `pickle` for scikit-learn objects because it handles large numpy arrays more efficiently.

```python
import pandas as pd
```
Pandas — used to hold the database results in a DataFrame so feature engineering (column operations) is easy.

> **Note:** `IsolationForest` and `StandardScaler` are no longer imported here. The detector does not train — it only loads. Those classes live entirely in `train_ml_model.py` now.

```python
from src.agents.base import FindingsObject, ErrorType, SeverityLevel
```
Imports the shared data structures all agents use to report findings. Every agent must return `FindingsObject` instances so the orchestrator can handle them uniformly.

```python
from src.database.connection import DatabaseConnection
```
The database wrapper that executes SQL queries against the EM (Exposure Manager) SQL Server database.

```python
from src.config.settings import settings
```
Imports the global settings object. Used here to resolve the model file path via `settings.models_dir`, so the path is consistent across the whole project and configurable from `.env`.

```python
MODEL_PATH = settings.models_dir / "trade_anomaly_model.pkl"
```
Module-level constant. Resolves to `<project_root>/models/trade_anomaly_model.pkl`. Defined at module level (not inside the class) so it is evaluated once on import rather than on every instantiation.

---

### Class Definition and `__init__` (lines 27–51)

```python
class MLAnomalyDetector:
```
Defines a class grouping all ML detection logic. One instance is created by the orchestrator per detection run.

```python
def __init__(self):
```
Constructor takes no arguments. All configuration (contamination, features, scaler) is loaded from the saved `.pkl` artifact — not passed in at runtime. This ensures the detector always uses exactly the same settings the model was trained with.

```python
    self.db = DatabaseConnection(database="EM")
```
Opens a connection to the EM database.

```python
    self.agent_name = "MLAnomalyDetector"
```
A string identifier stamped onto every `FindingsObject` this agent produces. The Risk Scorer uses this to distinguish ML findings from rule-based findings.

```python
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model file not found at {MODEL_PATH}. "
            "Please run: poetry run python train_ml_model.py"
        )
```
Fails fast with a clear, actionable error message if the model hasn't been trained yet. Without this check, the failure would occur later inside `detect_trade_anomalies` with a cryptic `AttributeError`. The error message tells the user exactly what to do.

```python
    artifact = joblib.load(MODEL_PATH)
```
Loads the entire saved dictionary from disk. `artifact` is a dict containing the model, scaler, and metadata (see `train_ml_model.py` for what is saved).

```python
    self.model = artifact["model"]
```
The trained `IsolationForest` instance. All 100 decision trees are already built — no training happens here.

```python
    self.scaler = artifact["scaler"]
```
The `StandardScaler` that was fitted on the training data. **Critically important** — this must be the exact same scaler used during training. Using a different scaler (even one fitted on the same data with slightly different row order) would produce different normalised values and corrupt the predictions.

```python
    self.feature_names = artifact["feature_names"]
```
The list of feature column names e.g. `['exposure', 'exposure_ratio', 'pv_discrepancy']`. Stored so the detector always uses the same features the model was trained on.

```python
    self.contamination = artifact["contamination"]
```
The contamination value used during training. Stored as metadata — not used at inference time (the model's decision boundary is already baked in), but useful for logging and auditing.

```python
    print(f"[MLAnomalyDetector] Loaded model trained on {artifact['training_samples']} samples ({artifact['trained_date']})")
```
Prints a confirmation showing when the model was trained and how much data it saw. Useful during debugging to confirm you are not running a stale model.

---

### `detect_trade_anomalies` — SQL Query (lines 53–144)

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

### Scaling (line 95)

```python
    X_scaled = self.scaler.transform(X)
```
`transform` (not `fit_transform`) — applies the normalisation parameters that were learned during training. It does **not** re-learn from the current data. This is the key difference from the old approach:

| Old (retrained each run) | New (pre-trained) |
|---|---|
| `scaler.fit_transform(X)` — learns mean/std from current 100 rows | `scaler.transform(X)` — uses mean/std learned from full training dataset |

Using `fit_transform` here would be wrong — the scaler would compute different statistics from just the `TOP 100` rows seen at inference time, which may not match the distribution the model was trained on, leading to inconsistent scores.

---

### Prediction (lines 97–99)

```python
    predictions = self.model.predict(X_scaled)
```
`predict` (not `fit_predict`) — runs inference using the already-trained model. No trees are built. Returns `+1` (normal) or `-1` (anomaly) for each row based on the decision boundary established during training.

**How Isolation Forest decides what is an anomaly:**
During training it built 100 decision trees by randomly selecting a feature and a split value. For each data point it counted how many splits were needed to isolate it. Points requiring few splits are anomalies — they sit far from the dense cluster of normal data. At inference time it simply applies those same trees to the new data.

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

### `__main__` block (lines 169–181)

```python
if __name__ == "__main__":
```
This block only runs when the file is executed directly (`python detector.py`), not when imported as a module. Used for quick manual testing.

```python
    detector = MLAnomalyDetector()
```
No arguments — all configuration comes from the loaded `.pkl`. This will raise `FileNotFoundError` if you haven't run `train_ml_model.py` first.

```python
    findings = detector.detect_all_anomalies()
    print(f"Total anomalies found: {len(findings)}\n")
    for finding in findings:
        print(f"[{finding.severity.value.upper()}] {finding.error_type.value}")
        print(f"  {finding.description}")
        print(f"  Confidence: {finding.confidence_score:.2f}")
```
Runs detection and prints a summary of each finding. `.value` on an Enum returns the string (e.g. `SeverityLevel.HIGH.value` → `"high"`). `.upper()` capitalises it for display.

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

This is the **only place** where training happens. Run it once before first use, then re-run whenever you want to refresh the model on newer data. The detector never trains — it only loads what this script produces.

### Imports

```python
from src.config.settings import settings
```
Now imports `settings` so the save path (`settings.models_dir`) is consistent with the detector's load path. Previously this script used a hardcoded `Path("models")` which could silently save to the wrong place depending on where you ran it from.

---

### `train_trade_anomaly_model` (lines 29–137)

```python
def train_trade_anomaly_model(contamination: float = 0.15):
```
Standalone training function. Key differences from the old in-detector training:
1. Fetches **all** records (no `TOP 100` limit) — trains on the full dataset for better generalisation
2. Uses `n_estimators=100` — double the trees for a more stable model
3. Saves model + scaler to disk so the detector can load them

```python
    query = """
        SELECT
            src_trade_ref, exposure, notional_1, component_use_pv, used_pv
        FROM trade
        WHERE exposure IS NOT NULL AND notional_1 IS NOT NULL AND notional_1 != 0
    """
```
No `TOP 100` here — fetches everything. The detector uses `TOP 100` at inference for speed, but the training data should be as large as possible.

```python
    results = db.execute_query(query)
    print(f"   Fetched {len(results)} trade records\n")

    if len(results) < 50:
        print("⚠ Warning: Less than 50 records. Model may not be reliable.")
        print("   Minimum recommended: 100+ records\n")
```
Data quality gate. Does **not** abort — training continues — but warns the user. Isolation Forest needs sufficient data to find meaningful clusters. With fewer than 50 records the "normal" pattern is poorly defined and the model will produce unreliable anomaly scores. 100+ records is the recommended minimum.

```python
    df = pd.DataFrame(results)
```
Converts the list of dicts from the database into a DataFrame for vectorised feature engineering.

```python
    df['exposure_ratio'] = df['exposure'] / df['notional_1']
    df['pv_discrepancy'] = df.apply(...)
    feature_cols = ['exposure', 'exposure_ratio', 'pv_discrepancy']
    X = df[feature_cols].fillna(0).replace([np.inf, -np.inf], 0)
```
Identical feature engineering to `detector.py`. **This must stay in sync.** If you add a feature here, add it in the detector too, or the scaler will receive unexpected columns and crash.

```python
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
```
`fit_transform` here — correct. During training we **want** to learn the mean and std from the data. This fitted scaler is saved to the artifact and loaded by the detector, which uses only `transform` (not `fit_transform`).

```python
    model = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=100
    )
    model.fit(X_scaled)
```
`fit()` not `fit_predict()` — we only need a trained model, not predictions on the training data.

```python
    predictions = model.predict(X_scaled)
    anomaly_count = (predictions == -1).sum()
    print(f"   Detected {anomaly_count} anomalies ({anomaly_count/len(predictions)*100:.1f}%)\n")
```
Post-training sanity check. Runs `predict` on the training data and counts how many records were labelled `-1` (anomaly). The percentage should be roughly equal to `contamination` (e.g. 10% if `contamination=0.1`). A wildly different percentage suggests the data distribution is unexpected.

```python
    model_path = settings.models_dir / "trade_anomaly_model.pkl"
    joblib.dump(model_artifact, model_path)

    file_size = model_path.stat().st_size / 1024
    print(f"   ✓ Model saved to: {model_path}")
    print(f"   Size: {file_size:.1f} KB\n")
```
`.stat().st_size` returns bytes; dividing by 1024 gives KB. Printed as confirmation — a typical Isolation Forest with 100 trees should be a few hundred KB.

```python
    print("\nNext steps:")
    print("  - Model will be used automatically by ML detector")
    print("  - Run detection to see results")
    print("  - Re-train periodically with: poetry run python train_ml_model.py")
```
Reminder shown after successful training — tells the user exactly what to do next.

---

### `main()` (lines 138–151)

```python
def main():
    train_trade_anomaly_model(contamination=settings.isolation_forest_contamination)
```
Now reads contamination from `settings.isolation_forest_contamination` (default `0.1` in `settings.py`, overridable via `.env`). Previously hardcoded to `0.15`. This means you can change contamination in one place (`.env` or `settings.py`) and it applies to both training and inference.

```python
    try:
        train_trade_anomaly_model(contamination=settings.isolation_forest_contamination)
        print("\n✅ Training successful!\n")
    except Exception as e:
        print(f"\n❌ Training failed: {str(e)}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```
Wraps the training call in a `try/except` so any failure (database connection error, insufficient data, disk write error) is caught cleanly.
- `print(f"\n❌ Training failed: {str(e)}\n")` — prints the error message in plain English
- `traceback.print_exc()` — prints the full Python stack trace so you can see exactly which line caused the failure. This is imported inside the `except` block (lazy import) since it is only ever needed on failure.
- `sys.exit(1)` — exits with code `1` (non-zero = failure). This is important for CI/CD pipelines or shell scripts that check the exit code to know if training succeeded.

```python
if __name__ == "__main__":
    main()
```
Only runs `main()` when the script is executed directly. If `train_ml_model` were ever imported as a module (unlikely but possible), this prevents accidental training on import.

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
    model_path = settings.models_dir / "trade_anomaly_model.pkl"
    joblib.dump(model_artifact, model_path)
```
Saves to `settings.models_dir / "trade_anomaly_model.pkl"` — the same path the detector loads from. The artifact bundles everything the detector needs:

| Key | What it is | Why it's needed |
|---|---|---|
| `model` | Trained `IsolationForest` | The decision trees for prediction |
| `scaler` | Fitted `StandardScaler` | Must match what was used during training |
| `feature_names` | `['exposure', 'exposure_ratio', 'pv_discrepancy']` | Documents which columns the model expects |
| `contamination` | e.g. `0.1` | Metadata — baked into the model already |
| `trained_date` | ISO timestamp | Audit trail — shown on detector startup |
| `training_samples` | e.g. `847` | Shown on detector startup |
| `detected_anomalies` | e.g. `127` | Sanity check — ~contamination% of training samples |

---

## End-to-End Flow Diagram

```
── TRAINING (run once) ──────────────────────────────────────────

  Database (all rows)
        │
        ▼
  train_ml_model.py
  ├── feature engineering
  ├── StandardScaler.fit_transform()   ← learns mean/std
  ├── IsolationForest.fit()            ← builds 100 trees
  └── joblib.dump(artifact)            → models/trade_anomaly_model.pkl

── DETECTION (every run) ────────────────────────────────────────

  models/trade_anomaly_model.pkl
        │
        ▼ joblib.load()
  MLAnomalyDetector.__init__()
  ├── self.model   = artifact["model"]
  ├── self.scaler  = artifact["scaler"]   ← same scaler as training
  └── self.feature_names = artifact["feature_names"]

  Database (TOP 100 rows)
        │
        ▼
  feature engineering
        │
        ▼
  scaler.transform()    ← applies saved mean/std (NO refit)
        │
        ▼
  model.predict()       ← uses pre-built trees (NO retraining)
  model.score_samples() ← raw anomaly scores
        │
        ▼ normalise + filter
  List[FindingsObject]
        │
        │
Database (all rows, 3 SQL rules)
        │
        ▼
┌───────────────────┐     ┌──────────────────────┐
│  RuleBasedDetector│     │  MLAnomalyDetector   │
│  (3 SQL rules)    │     │  (loads from .pkl)   │
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

**Why `fit_transform` in training but `transform` in the detector?**

- `fit_transform` = learn the mean/std **then** apply them. Used once in `train_ml_model.py` on the full dataset.
- `transform` = apply already-learned mean/std. Used in `detector.py` at inference time.

If the detector called `fit_transform`, it would re-learn statistics from just the `TOP 100` rows it fetches, which may have a different distribution from the training data. This would silently corrupt the scores. The saved scaler ensures the same transformation is applied consistently every time.

### Why `contamination=0.15`?

This is a prior belief: "I expect about 15% of my trade data to contain some form of anomaly." Set it too low (e.g. 0.01) and the model will only flag the most extreme outliers. Set it too high (e.g. 0.50) and it flags half the database, creating too many false positives.

For a POC, 15% is a reasonable starting point. In production this should be tuned against labelled historical data.

### Why is ML confidence always lower than rules?

Rules have `confidence_score=1.0` because they are deterministic — if `R + D = D` then it IS a split booking error, no uncertainty. ML has `confidence_score=0.5–1.0` because it is statistical — it found something unusual but cannot be certain it is erroneous. This is why ML-only detections are listed in `mitigating_factors` and reduce the final risk score slightly.
