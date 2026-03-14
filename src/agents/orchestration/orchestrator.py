#!/usr/bin/env python3
"""
Orchestrator Agent

Coordinates all detection agents and produces final alerts
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.agents.base import FindingsObject, Alert, SeverityLevel
from src.agents.rule_engine.detector import RuleBasedDetector
from src.agents.ml_engine.detector import MLAnomalyDetector
from src.agents.llm_engine.analyzer import LLMAnalyzer
from src.agents.risk_scoring.scorer import RiskScorer
from src.agents.resolution_agent import ResolutionAgent


class AnomalyDetectionOrchestrator:
    """
    Simplified Orchestrator for POC (Rule + ML + LLM + RAG)
    """

    def __init__(
        self,
        use_ml: bool = True,
        use_llm: bool = True,
        use_rag: bool = True,
        openai_api_key: Optional[str] = None
    ):
        """
        Initialize orchestrator (simplified POC with LLM/RAG)

        Args:
            use_ml: Enable ML-based detection
            use_llm: Enable LLM analysis (optional)
            use_rag: Enable RAG resolution recommendations
            openai_api_key: OpenAI API key for LLM
        """
        self.use_ml = use_ml
        self.use_llm = use_llm
        self.use_rag = use_rag

        # Initialize agents (simplified: 3 rules, trade ML, optional LLM/RAG)
        self.rule_detector = RuleBasedDetector()
        self.ml_detector = MLAnomalyDetector() if use_ml else None
        self.llm_analyzer = LLMAnalyzer(api_key=openai_api_key) if use_llm and openai_api_key else None
        self.risk_scorer = RiskScorer()
        # Pass API key to ResolutionAgent for LLM-enhanced recommendations
        if use_rag:
            self.resolution_agent = ResolutionAgent(openai_api_key=openai_api_key)
        else:
            self.resolution_agent = None

        # Weights for ensemble scoring
        self.weights = {
            "rule_based": 0.50,
            "ml_based": 0.30,
            "llm_confidence": 0.20
        }

    def run_full_detection(self) -> List[Alert]:
        """
        Run simplified detection pipeline with optional LLM/RAG

        Returns:
            List of Alert objects
        """
        print("=== Starting Anomaly Detection (Simplified POC) ===\n")

        # Step 1: Rule-based detection (3 rules only)
        print("1. Running rule-based detection (3 rules)...")
        rule_findings = self.rule_detector.detect_all_anomalies()
        print(f"   Found {len(rule_findings)} anomalies\n")

        # Step 2: ML-based detection (trade anomalies only)
        ml_findings = []
        if self.use_ml and self.ml_detector:
            print("2. Running ML-based detection (trade anomalies)...")
            ml_findings = self.ml_detector.detect_all_anomalies()
            print(f"   Found {len(ml_findings)} anomalies\n")

        # Step 3: Combine findings
        all_findings = rule_findings + ml_findings
        print(f"3. Total findings: {len(all_findings)}\n")

        # Step 4: Group by entity
        grouped_findings = self._group_findings(all_findings)
        print(f"4. Grouped into {len(grouped_findings)} entities\n")

        # Step 5: Create alerts
        alerts = []
        for entity_id, findings in grouped_findings.items():
            alert = self._create_alert(entity_id, findings)
            alerts.append(alert)

        # Step 6: RAG-based resolution (if enabled)
        if self.use_rag and self.resolution_agent:
            print("5. Running RAG resolution recommendations...")
            for alert in alerts:
                if alert.ensemble_score >= 0.5:
                    recommendation = self.resolution_agent.analyze_findings(
                        alert.agent_findings,
                        alert.ensemble_score
                    )
                    if recommendation:
                        alert.resolution_recommendation = recommendation.explanation
                        alert.audit_log.append({
                            "timestamp": datetime.now().isoformat(),
                            "action": "rag_resolution",
                            "similar_incidents": len(recommendation.similar_incidents),
                            "confidence": recommendation.confidence
                        })
            print("   RAG recommendations added\n")

        # Step 7: Sort alerts
        alerts.sort(key=lambda x: (x.risk_score, x.ensemble_score), reverse=True)

        print(f"=== Detection Complete: {len(alerts)} Alerts Generated ===\n")

        return alerts

    def _group_findings(self, findings: List[FindingsObject]) -> Dict[str, List[FindingsObject]]:
        """Group findings by entity (client_id)"""
        grouped = {}

        for finding in findings:
            entity_id = finding.client_id or "unknown"

            if entity_id not in grouped:
                grouped[entity_id] = []

            grouped[entity_id].append(finding)

        return grouped

    def _create_alert(self, entity_id: str, findings: List[FindingsObject]) -> Alert:
        """
        Create alert from grouped findings

        Args:
            entity_id: Entity identifier
            findings: List of findings for this entity

        Returns:
            Alert object
        """
        # Calculate ensemble score (legacy)
        ensemble_score = self._calculate_ensemble_score(findings)

        # Calculate comprehensive risk score
        risk_assessment = self.risk_scorer.calculate_risk_score(findings, entity_id)

        # Determine confidence level
        if ensemble_score >= 0.8:
            confidence_level = SeverityLevel.CRITICAL
        elif ensemble_score >= 0.6:
            confidence_level = SeverityLevel.HIGH
        elif ensemble_score >= 0.4:
            confidence_level = SeverityLevel.MEDIUM
        else:
            confidence_level = SeverityLevel.LOW

        # Get value date from first finding
        value_date = findings[0].value_date if findings else None

        # Create alert
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            client_id=entity_id,
            value_date=value_date or "N/A",
            ensemble_score=ensemble_score,
            confidence_level=confidence_level,
            risk_score=risk_assessment.total_risk_score,
            risk_level=risk_assessment.risk_level.value,
            risk_factors=risk_assessment.risk_factors,
            mitigating_factors=risk_assessment.mitigating_factors,
            agent_findings=findings,
            audit_log=[
                {
                    "timestamp": datetime.now().isoformat(),
                    "action": "alert_created",
                    "findings_count": len(findings),
                    "risk_assessment": risk_assessment.to_dict()
                }
            ]
        )

        return alert

    def _calculate_ensemble_score(self, findings: List[FindingsObject]) -> float:
        """
        Calculate weighted ensemble score

        Args:
            findings: List of findings

        Returns:
            Ensemble score (0.0 to 1.0)
        """
        if not findings:
            return 0.0

        # Separate by agent type
        rule_findings = [f for f in findings if f.agent_name == "RuleBasedDetector"]
        ml_findings = [f for f in findings if f.agent_name == "MLAnomalyDetector"]

        # Calculate average confidence scores
        rule_score = (
            sum(f.confidence_score for f in rule_findings) / len(rule_findings)
            if rule_findings else 0.0
        )

        ml_score = (
            sum(f.confidence_score for f in ml_findings) / len(ml_findings)
            if ml_findings else 0.0
        )

        # LLM confidence boost (if multiple findings)
        llm_boost = min(len(findings) * 0.1, 0.3)

        # Calculate weighted ensemble score
        ensemble_score = (
            rule_score * self.weights["rule_based"] +
            ml_score * self.weights["ml_based"] +
            llm_boost * self.weights["llm_confidence"]
        )

        # Normalize to 0-1 range
        return min(max(ensemble_score, 0.0), 1.0)

    def generate_report(self, alerts: List[Alert]) -> str:
        """
        Generate human-readable report

        Args:
            alerts: List of alerts

        Returns:
            Report string
        """
        report = []
        report.append("=" * 80)
        report.append("EM PAYMENT RISK MANAGEMENT SYSTEM - RISK ASSESSMENT REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Alerts: {len(alerts)}")
        report.append("")

        # Summary by severity
        by_severity = {}
        for alert in alerts:
            severity = alert.confidence_level.value
            by_severity[severity] = by_severity.get(severity, 0) + 1

        report.append("Alerts by Severity:")
        for severity in ["critical", "high", "medium", "low"]:
            count = by_severity.get(severity, 0)
            if count > 0:
                report.append(f"  {severity.upper()}: {count}")
        report.append("")

        # Top alerts
        report.append("=" * 80)
        report.append("TOP PRIORITY ALERTS")
        report.append("=" * 80)

        for idx, alert in enumerate(alerts[:10], 1):  # Top 10
            report.append(f"\nAlert #{idx}")
            report.append(f"  ID: {alert.alert_id}")
            report.append(f"  Entity: {alert.client_id}")
            report.append(f"  Risk Score: {alert.risk_score:.1f}/100 ({alert.risk_level.upper()})")
            report.append(f"  Severity: {alert.confidence_level.value.upper()}")
            report.append(f"  Ensemble Score: {alert.ensemble_score:.2f}")
            report.append(f"  Findings: {len(alert.agent_findings)}")

            # Risk factors
            if alert.risk_factors:
                report.append(f"  Key Risk Factors:")
                for factor in alert.risk_factors[:3]:  # Top 3
                    report.append(f"    • {factor}")

            # List findings
            report.append(f"  Detected Issues:")
            for finding in alert.agent_findings:
                report.append(f"    - [{finding.error_type.value}] {finding.description}")

            if alert.resolution_recommendation:
                report.append(f"  Recommendation: {alert.resolution_recommendation[:200]}...")

        report.append("")
        report.append("=" * 80)
        report.append("END OF REPORT")
        report.append("=" * 80)

        return "\n".join(report)


def main():
    """Main execution (simplified POC with optional LLM/RAG)"""
    import os

    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")

    # Initialize orchestrator (simplified: 3 rules + trade ML + optional LLM/RAG)
    orchestrator = AnomalyDetectionOrchestrator(
        use_ml=True,
        use_llm=bool(api_key),  # Enable if API key available
        use_rag=True,  # Enable RAG recommendations
        openai_api_key=api_key
    )

    # Run detection
    alerts = orchestrator.run_full_detection()

    # Generate report
    report = orchestrator.generate_report(alerts)
    print(report)

    # Optionally save to file
    output_file = f"payment_risk_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(output_file, "w") as f:
        f.write(report)
    print(f"\nReport saved to: {output_file}")


if __name__ == "__main__":
    main()
