#!/usr/bin/env python3
"""
Risk Scoring Engine

Calculates comprehensive risk scores for anomalies based on multiple factors:
- Detection confidence
- Anomaly severity
- Financial impact
- Pattern frequency
- Business criticality
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime
from enum import Enum

from src.agents.base import FindingsObject, ErrorType, SeverityLevel


class RiskLevel(Enum):
    """Overall risk level classification"""
    CRITICAL = "critical"      # 90-100: Immediate action required
    HIGH = "high"              # 70-89: Urgent review needed
    MEDIUM = "medium"          # 50-69: Review within 48 hours
    LOW = "low"                # 30-49: Monitor
    MINIMAL = "minimal"        # 0-29: Information only


@dataclass
class RiskScore:
    """
    Comprehensive risk assessment for an anomaly or alert
    """
    # Overall scores
    total_risk_score: float  # 0-100
    risk_level: RiskLevel
    confidence_score: float  # 0-1 (from detectors)

    # Component scores
    severity_score: float  # 0-100: Based on anomaly type
    impact_score: float    # 0-100: Financial/business impact
    frequency_score: float # 0-100: Pattern repetition
    urgency_score: float   # 0-100: Time sensitivity

    # Risk factors
    risk_factors: List[str] = field(default_factory=list)
    mitigating_factors: List[str] = field(default_factory=list)

    # Metadata
    calculation_timestamp: datetime = field(default_factory=datetime.now)
    breakdown: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_risk_score": round(self.total_risk_score, 2),
            "risk_level": self.risk_level.value,
            "confidence_score": round(self.confidence_score, 2),
            "severity_score": round(self.severity_score, 2),
            "impact_score": round(self.impact_score, 2),
            "frequency_score": round(self.frequency_score, 2),
            "urgency_score": round(self.urgency_score, 2),
            "risk_factors": self.risk_factors,
            "mitigating_factors": self.mitigating_factors,
            "calculation_timestamp": self.calculation_timestamp.isoformat(),
            "breakdown": self.breakdown
        }


class RiskScorer:
    """
    Calculate comprehensive risk scores for anomalies
    """

    # Risk weights (must sum to 1.0)
    WEIGHTS = {
        "severity": 0.30,      # Type of anomaly
        "impact": 0.30,        # Financial/business impact
        "confidence": 0.25,    # Detection confidence
        "frequency": 0.10,     # How often it occurs
        "urgency": 0.05        # Time sensitivity
    }

    # Severity scoring by error type
    SEVERITY_SCORES = {
        ErrorType.DUPLICATE_BOOKING: 85,
        ErrorType.SPLIT_BOOKING_ERROR: 90,
        ErrorType.DRA_MISMATCH: 80,
        ErrorType.ZERO_MARGIN: 95,
        ErrorType.EOD_BOUNDARY_CROSSING: 75,
        ErrorType.MARGIN_SWING: 70,
        ErrorType.TIMEOUT: 60,
        ErrorType.UNKNOWN: 50
    }

    # Severity multipliers by SeverityLevel
    SEVERITY_MULTIPLIERS = {
        SeverityLevel.CRITICAL: 1.0,
        SeverityLevel.HIGH: 0.85,
        SeverityLevel.MEDIUM: 0.65,
        SeverityLevel.LOW: 0.40
    }

    def __init__(self):
        """Initialize risk scorer"""
        self.agent_name = "RiskScorer"

    def calculate_risk_score(
        self,
        findings: List[FindingsObject],
        entity_id: str = None
    ) -> RiskScore:
        """
        Calculate comprehensive risk score for a set of findings

        Args:
            findings: List of findings for an entity
            entity_id: Entity identifier (optional)

        Returns:
            RiskScore object with detailed assessment
        """
        if not findings:
            return self._minimal_risk_score()

        # Calculate component scores
        severity_score = self._calculate_severity_score(findings)
        impact_score = self._calculate_impact_score(findings)
        confidence_score = self._calculate_confidence_score(findings)
        frequency_score = self._calculate_frequency_score(findings)
        urgency_score = self._calculate_urgency_score(findings)

        # Calculate weighted total risk score (0-100)
        total_risk_score = (
            severity_score * self.WEIGHTS["severity"] +
            impact_score * self.WEIGHTS["impact"] +
            confidence_score * 100 * self.WEIGHTS["confidence"] +
            frequency_score * self.WEIGHTS["frequency"] +
            urgency_score * self.WEIGHTS["urgency"]
        )

        # Determine risk level
        risk_level = self._determine_risk_level(total_risk_score)

        # Identify risk factors
        risk_factors = self._identify_risk_factors(findings)
        mitigating_factors = self._identify_mitigating_factors(findings)

        # Create detailed breakdown
        breakdown = {
            "severity_component": {
                "score": round(severity_score, 2),
                "weight": self.WEIGHTS["severity"],
                "contribution": round(severity_score * self.WEIGHTS["severity"], 2)
            },
            "impact_component": {
                "score": round(impact_score, 2),
                "weight": self.WEIGHTS["impact"],
                "contribution": round(impact_score * self.WEIGHTS["impact"], 2)
            },
            "confidence_component": {
                "score": round(confidence_score, 2),
                "weight": self.WEIGHTS["confidence"],
                "contribution": round(confidence_score * 100 * self.WEIGHTS["confidence"], 2)
            },
            "frequency_component": {
                "score": round(frequency_score, 2),
                "weight": self.WEIGHTS["frequency"],
                "contribution": round(frequency_score * self.WEIGHTS["frequency"], 2)
            },
            "urgency_component": {
                "score": round(urgency_score, 2),
                "weight": self.WEIGHTS["urgency"],
                "contribution": round(urgency_score * self.WEIGHTS["urgency"], 2)
            },
            "total_findings": len(findings),
            "unique_error_types": len(set(f.error_type for f in findings)),
            "agent_consensus": self._calculate_agent_consensus(findings)
        }

        return RiskScore(
            total_risk_score=total_risk_score,
            risk_level=risk_level,
            confidence_score=confidence_score,
            severity_score=severity_score,
            impact_score=impact_score,
            frequency_score=frequency_score,
            urgency_score=urgency_score,
            risk_factors=risk_factors,
            mitigating_factors=mitigating_factors,
            breakdown=breakdown
        )

    def _calculate_severity_score(self, findings: List[FindingsObject]) -> float:
        """
        Calculate severity score based on error types and severity levels

        Returns: 0-100 score
        """
        if not findings:
            return 0.0

        scores = []
        for finding in findings:
            # Base score from error type
            base_score = self.SEVERITY_SCORES.get(finding.error_type, 50)

            # Apply severity multiplier
            multiplier = self.SEVERITY_MULTIPLIERS.get(finding.severity, 0.5)

            # Final score
            score = base_score * multiplier
            scores.append(score)

        # Return max score (worst case)
        return max(scores)

    def _calculate_impact_score(self, findings: List[FindingsObject]) -> float:
        """
        Calculate business/financial impact score

        Returns: 0-100 score
        """
        impact_score = 50.0  # Default medium impact

        for finding in findings:
            evidence = finding.evidence or {}

            # Check for financial amounts
            if "exposure" in evidence:
                exposure = abs(float(evidence.get("exposure", 0)))
                if exposure > 1_000_000:
                    impact_score = max(impact_score, 90)
                elif exposure > 500_000:
                    impact_score = max(impact_score, 75)
                elif exposure > 100_000:
                    impact_score = max(impact_score, 60)

            if "nominal" in evidence:
                nominal = abs(float(evidence.get("nominal", 0)))
                if nominal > 500_000:
                    impact_score = max(impact_score, 85)
                elif nominal > 200_000:
                    impact_score = max(impact_score, 70)

            # Critical error types have high impact
            if finding.error_type in [
                ErrorType.DUPLICATE_BOOKING,
                ErrorType.SPLIT_BOOKING_ERROR,
                ErrorType.ZERO_MARGIN
            ]:
                impact_score = max(impact_score, 80)

            # Check for date anomalies (always critical)
            if "effective_date" in evidence and "maturity_date" in evidence:
                impact_score = max(impact_score, 95)

        return min(impact_score, 100.0)

    def _calculate_confidence_score(self, findings: List[FindingsObject]) -> float:
        """
        Calculate average detection confidence

        Returns: 0-1 score
        """
        if not findings:
            return 0.0

        confidences = [f.confidence_score for f in findings]
        return sum(confidences) / len(confidences)

    def _calculate_frequency_score(self, findings: List[FindingsObject]) -> float:
        """
        Calculate score based on pattern frequency

        Returns: 0-100 score
        """
        # Multiple findings = higher frequency
        count = len(findings)

        if count >= 5:
            return 100.0
        elif count >= 3:
            return 75.0
        elif count >= 2:
            return 50.0
        else:
            return 25.0

    def _calculate_urgency_score(self, findings: List[FindingsObject]) -> float:
        """
        Calculate urgency based on time sensitivity

        Returns: 0-100 score
        """
        urgency = 50.0  # Default medium urgency

        for finding in findings:
            # Critical severity = high urgency
            if finding.severity == SeverityLevel.CRITICAL:
                urgency = max(urgency, 95)
            elif finding.severity == SeverityLevel.HIGH:
                urgency = max(urgency, 75)

            # Certain error types need immediate attention
            if finding.error_type in [
                ErrorType.ZERO_MARGIN,
                ErrorType.EOD_BOUNDARY_CROSSING
            ]:
                urgency = max(urgency, 90)

        return urgency

    def _determine_risk_level(self, total_score: float) -> RiskLevel:
        """Determine overall risk level from total score"""
        if total_score >= 90:
            return RiskLevel.CRITICAL
        elif total_score >= 70:
            return RiskLevel.HIGH
        elif total_score >= 50:
            return RiskLevel.MEDIUM
        elif total_score >= 30:
            return RiskLevel.LOW
        else:
            return RiskLevel.MINIMAL

    def _identify_risk_factors(self, findings: List[FindingsObject]) -> List[str]:
        """Identify key risk factors from findings"""
        factors = []

        # Multiple detectors agree
        if len(findings) >= 3:
            factors.append("Multiple detection engines agree")

        # High confidence detections
        high_conf_count = sum(1 for f in findings if f.confidence_score > 0.85)
        if high_conf_count >= 2:
            factors.append(f"{high_conf_count} high-confidence detections")

        # Critical error types
        critical_types = [
            f for f in findings
            if f.error_type in [
                ErrorType.DUPLICATE_BOOKING,
                ErrorType.SPLIT_BOOKING_ERROR,
                ErrorType.ZERO_MARGIN
            ]
        ]
        if critical_types:
            factors.append(f"Critical error type: {critical_types[0].error_type.value}")

        # Large financial amounts
        for finding in findings:
            evidence = finding.evidence or {}
            if "exposure" in evidence:
                exposure = abs(float(evidence.get("exposure", 0)))
                if exposure > 1_000_000:
                    factors.append(f"High exposure: ${exposure:,.0f}")
                    break

        # Rule-based detection (high precision)
        rule_findings = [f for f in findings if f.agent_name == "RuleBasedDetector"]
        if rule_findings:
            factors.append("Rule-based pattern match (high precision)")

        return factors

    def _identify_mitigating_factors(self, findings: List[FindingsObject]) -> List[str]:
        """Identify factors that reduce risk"""
        factors = []

        # Low severity findings
        low_severity = [f for f in findings if f.severity == SeverityLevel.LOW]
        if low_severity:
            factors.append("Some low-severity findings")

        # Single detection (no consensus)
        if len(findings) == 1:
            factors.append("Single detector only (no consensus)")

        # ML-only detection (may be false positive)
        if all(f.agent_name == "MLAnomalyDetector" for f in findings):
            factors.append("ML-only detection (statistical)")

        # Low confidence
        low_conf = [f for f in findings if f.confidence_score < 0.6]
        if low_conf:
            factors.append(f"{len(low_conf)} low-confidence detections")

        return factors

    def _calculate_agent_consensus(self, findings: List[FindingsObject]) -> Dict[str, int]:
        """Calculate how many agents contributed"""
        agents = {}
        for finding in findings:
            agent = finding.agent_name
            agents[agent] = agents.get(agent, 0) + 1
        return agents

    def _minimal_risk_score(self) -> RiskScore:
        """Return minimal risk score for no findings"""
        return RiskScore(
            total_risk_score=0.0,
            risk_level=RiskLevel.MINIMAL,
            confidence_score=0.0,
            severity_score=0.0,
            impact_score=0.0,
            frequency_score=0.0,
            urgency_score=0.0,
            risk_factors=[],
            mitigating_factors=["No anomalies detected"],
            breakdown={}
        )


if __name__ == "__main__":
    # Test risk scorer
    from src.agents.base import FindingsObject, ErrorType, SeverityLevel

    # Sample findings
    findings = [
        FindingsObject(
            agent_name="RuleBasedDetector",
            timestamp=datetime.now(),
            client_id="772493",
            value_date="2026-02-18",
            error_type=ErrorType.SPLIT_BOOKING_ERROR,
            severity=SeverityLevel.HIGH,
            confidence_score=0.95,
            description="Split booking duplicate",
            evidence={"nominal": 265000, "exposure": 1200000}
        ),
        FindingsObject(
            agent_name="MLAnomalyDetector",
            timestamp=datetime.now(),
            client_id="772493",
            value_date="2026-02-18",
            error_type=ErrorType.UNKNOWN,
            severity=SeverityLevel.MEDIUM,
            confidence_score=0.72,
            description="Statistical anomaly",
            evidence={}
        )
    ]

    scorer = RiskScorer()
    risk_score = scorer.calculate_risk_score(findings)

    print("=== Risk Assessment ===")
    print(f"Total Risk Score: {risk_score.total_risk_score:.1f}/100")
    print(f"Risk Level: {risk_score.risk_level.value.upper()}")
    print(f"Confidence: {risk_score.confidence_score:.2f}")
    print(f"\nComponent Scores:")
    print(f"  Severity: {risk_score.severity_score:.1f}")
    print(f"  Impact: {risk_score.impact_score:.1f}")
    print(f"  Frequency: {risk_score.frequency_score:.1f}")
    print(f"  Urgency: {risk_score.urgency_score:.1f}")
    print(f"\nRisk Factors:")
    for factor in risk_score.risk_factors:
        print(f"  - {factor}")
