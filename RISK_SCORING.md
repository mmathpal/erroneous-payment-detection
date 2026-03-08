# Risk Scoring System

## Overview

Comprehensive risk assessment system that calculates a **0-100 risk score** for each anomaly based on multiple factors beyond simple detection confidence.

## Risk Score Components

### 1. Severity Score (30% weight)
Based on anomaly type and severity level:

**Error Type Scores**:
- Split Booking Error: 90/100
- Zero Margin: 95/100
- Duplicate Booking: 85/100
- DRA Mismatch: 80/100
- EOD Boundary Crossing: 75/100
- Margin Swing: 70/100
- Timeout: 60/100
- Unknown: 50/100

**Severity Multipliers**:
- Critical: 1.0x
- High: 0.85x
- Medium: 0.65x
- Low: 0.40x

### 2. Impact Score (30% weight)
Financial and business impact assessment:

**Financial Thresholds**:
- Exposure > $1M: 90/100
- Exposure > $500K: 75/100
- Exposure > $100K: 60/100
- Nominal > $500K: 85/100
- Nominal > $200K: 70/100

**Critical Issues**: 80-95/100
- Duplicate bookings
- Split booking errors
- Date anomalies
- Zero margin

### 3. Confidence Score (25% weight)
Average detection confidence from all agents:
- Directly uses 0-1 confidence scores
- Scaled to 0-100 for final calculation

### 4. Frequency Score (10% weight)
Pattern repetition:
- 5+ findings: 100/100
- 3-4 findings: 75/100
- 2 findings: 50/100
- 1 finding: 25/100

### 5. Urgency Score (5% weight)
Time sensitivity:
- Critical severity: 95/100
- High severity: 75/100
- Zero margin / EOD crossing: 90/100
- Default: 50/100

## Risk Levels

Total Risk Score determines risk level:

| Score Range | Risk Level | Action Required |
|-------------|-----------|-----------------|
| 90-100 | **CRITICAL** | Immediate action - Stop processing |
| 70-89 | **HIGH** | Urgent review within 4 hours |
| 50-69 | **MEDIUM** | Review within 48 hours |
| 30-49 | **LOW** | Monitor, review this week |
| 0-29 | **MINIMAL** | Information only |

## Calculation Formula

```
Total Risk Score =
    (Severity Score × 0.30) +
    (Impact Score × 0.30) +
    (Confidence Score × 100 × 0.25) +
    (Frequency Score × 0.10) +
    (Urgency Score × 0.05)
```

## Risk Factors

System automatically identifies key risk factors:

### Amplifying Factors
- ✓ Multiple detection engines agree
- ✓ High-confidence detections (>0.85)
- ✓ Critical error types
- ✓ Large financial amounts
- ✓ Rule-based pattern match (high precision)

### Mitigating Factors
- ✓ Low severity findings
- ✓ Single detector only (no consensus)
- ✓ ML-only detection (statistical)
- ✓ Low confidence (<0.6)

## Example Risk Assessment

### High Risk Example
```
Alert: Split Booking Duplicate + ML Anomaly
Entity: 772495
Risk Score: 80.6/100 (HIGH)

Components:
- Severity: 90/100 (Split booking × Critical level)
- Impact: 85/100 (High nominal amount)
- Confidence: 0.84 (Average of 0.95 rule + 0.72 ML)
- Frequency: 75/100 (3 findings)
- Urgency: 75/100 (High severity)

Risk Factors:
• Multiple detection engines agree
• 2 high-confidence detections
• Critical error type: split_booking_error

Final: (90×0.3) + (85×0.3) + (84×0.25) + (75×0.1) + (75×0.05) = 80.6
```

### Medium Risk Example
```
Alert: Single Split Booking
Entity: 772493
Risk Score: 77.0/100 (HIGH)

Components:
- Severity: 90/100 (Split booking × High level)
- Impact: 70/100 (Moderate amount)
- Confidence: 0.95 (Rule-based only)
- Frequency: 25/100 (1 finding)
- Urgency: 75/100 (High severity)

Risk Factors:
• Critical error type
• Rule-based pattern match

Final: (90×0.3) + (70×0.3) + (95×0.25) + (25×0.1) + (75×0.05) = 77.0
```

## Usage

### In Code

```python
from src.agents.risk_scoring import RiskScorer

scorer = RiskScorer()
risk_score = scorer.calculate_risk_score(findings)

print(f"Risk Score: {risk_score.total_risk_score:.1f}/100")
print(f"Risk Level: {risk_score.risk_level.value}")
print(f"Risk Factors: {risk_score.risk_factors}")
```

### In Alerts

Risk scores are automatically calculated for all alerts:

```python
alert.risk_score        # 0-100
alert.risk_level        # critical/high/medium/low/minimal
alert.risk_factors      # List of key factors
```

### In Reports

```
Alert #1
  Risk Score: 80.9/100 (HIGH)
  Key Risk Factors:
    • High exposure: $5,000,000
    • Rule-based pattern match
```

## Benefits

### 1. Multi-Dimensional Assessment
Goes beyond simple confidence to consider:
- Type of anomaly
- Financial impact
- Multiple detector consensus
- Pattern frequency
- Time sensitivity

### 2. Actionable Prioritization
Clear risk levels with defined actions:
- CRITICAL → Stop processing
- HIGH → Urgent review
- MEDIUM → Review soon
- LOW → Monitor

### 3. Transparency
Detailed breakdown shows:
- Component scores
- Risk factors identified
- Mitigating factors
- Full audit trail in alert

### 4. Tunable Weights
Easily adjust component weights in `RiskScorer`:
```python
WEIGHTS = {
    "severity": 0.30,    # Adjust these
    "impact": 0.30,
    "confidence": 0.25,
    "frequency": 0.10,
    "urgency": 0.05
}
```

## Configuration

### Adjust Severity Scores
Edit `SEVERITY_SCORES` in `risk_scoring/scorer.py`:
```python
SEVERITY_SCORES = {
    ErrorType.DUPLICATE_BOOKING: 85,  # Change score
    ErrorType.SPLIT_BOOKING_ERROR: 90,
    # ...
}
```

### Adjust Impact Thresholds
Edit `_calculate_impact_score()`:
```python
if exposure > 1_000_000:  # Change threshold
    impact_score = max(impact_score, 90)
```

### Change Risk Levels
Edit `_determine_risk_level()`:
```python
if total_score >= 90:  # Change boundary
    return RiskLevel.CRITICAL
```

## Integration

Risk scoring is automatically integrated in:
- ✅ Orchestrator (calculates for every alert)
- ✅ Alert object (stores risk metrics)
- ✅ Reports (displays risk scores)
- ✅ Audit logs (includes full breakdown)

## Output Example

```json
{
  "alert_id": "...",
  "risk_score": 80.6,
  "risk_level": "high",
  "risk_factors": [
    "Multiple detection engines agree",
    "Critical error type: split_booking_error"
  ],
  "audit_log": [{
    "risk_assessment": {
      "total_risk_score": 80.6,
      "severity_score": 90.0,
      "impact_score": 85.0,
      "confidence_score": 0.84,
      "frequency_score": 75.0,
      "urgency_score": 75.0,
      "breakdown": {
        "severity_component": {
          "score": 90.0,
          "weight": 0.3,
          "contribution": 27.0
        },
        // ...
      }
    }
  }]
}
```

## Comparison: Ensemble Score vs Risk Score

| Metric | Ensemble Score | Risk Score |
|--------|---------------|-----------|
| Range | 0.0 - 1.0 | 0 - 100 |
| Factors | Detection confidence only | 5 components |
| Weights | Agent types | Multi-dimensional |
| Output | Simple average | Comprehensive assessment |
| Use Case | Legacy compatibility | Actionable prioritization |

**Both scores are calculated** - Risk Score is recommended for decision making.

## Best Practices

1. **Use Risk Score for prioritization**
   - Sort by risk_score (not ensemble_score)
   - Use risk_level for action decisions

2. **Review risk_factors**
   - Understand why score is high/low
   - Check for amplifying factors

3. **Monitor score distribution**
   - If all alerts are HIGH/CRITICAL, tune thresholds
   - Aim for good spread across levels

4. **Tune for your environment**
   - Adjust weights based on your priorities
   - Customize thresholds for financial amounts
   - Add domain-specific risk factors

5. **Audit trail**
   - Full breakdown stored in alert.audit_log
   - Use for investigation and tuning
