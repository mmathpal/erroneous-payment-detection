#!/usr/bin/env python3
"""
LLM Analysis Agent

Uses OpenAI GPT to analyze anomalies and provide recommendations
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from openai import OpenAI

from src.agents.base import FindingsObject, ErrorType, SeverityLevel


class LLMAnalyzer:
    """LLM-powered analysis and recommendation engine"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize LLM analyzer

        Args:
            api_key: OpenAI API key (uses env var OPENAI_API_KEY if not provided)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")

        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.client = OpenAI(api_key=self.api_key, base_url=base_url)
        self.agent_name = "LLMAnalyzer"
        self.model = "gpt-4o-mini"  # Cost-effective model

    def analyze_anomalies(
        self,
        findings: List[FindingsObject],
        include_recommendations: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze findings using LLM

        Args:
            findings: List of findings from other detectors
            include_recommendations: Whether to include detailed recommendations

        Returns:
            Analysis results with insights and recommendations
        """
        if not findings:
            return {
                "summary": "No anomalies detected",
                "recommendations": [],
                "insights": []
            }

        # Prepare context for LLM
        context = self._prepare_context(findings)

        # Build prompt
        prompt = self._build_analysis_prompt(context, include_recommendations)

        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert financial analyst specializing in detecting erroneous payments and trade anomalies in OTC clearing systems."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )

            analysis_text = response.choices[0].message.content

            # Parse response
            analysis = self._parse_llm_response(analysis_text)

            return analysis

        except Exception as e:
            return {
                "error": f"LLM analysis failed: {str(e)}",
                "summary": "Analysis unavailable",
                "recommendations": []
            }

    def explain_anomaly(self, finding: FindingsObject) -> str:
        """
        Get detailed explanation for a single anomaly

        Args:
            finding: FindingsObject to explain

        Returns:
            Detailed explanation string
        """
        prompt = f"""
Explain this financial anomaly in detail:

Type: {finding.error_type.value}
Severity: {finding.severity.value}
Description: {finding.description}

Evidence:
{json.dumps(finding.evidence, indent=2)}

Provide:
1. What this anomaly means
2. Potential causes
3. Business impact
4. Recommended actions

Be concise but thorough.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert financial analyst explaining trade anomalies."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=800
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"Explanation unavailable: {str(e)}"

    def prioritize_findings(self, findings: List[FindingsObject]) -> List[Dict[str, Any]]:
        """
        Use LLM to prioritize findings by business impact

        Args:
            findings: List of findings to prioritize

        Returns:
            Prioritized list with reasoning
        """
        if not findings:
            return []

        # Summarize findings for LLM
        findings_summary = []
        for idx, finding in enumerate(findings):
            findings_summary.append({
                "index": idx,
                "type": finding.error_type.value,
                "severity": finding.severity.value,
                "confidence": finding.confidence_score,
                "description": finding.description,
                "client_id": finding.client_id
            })

        prompt = f"""
Analyze these {len(findings)} financial anomalies and prioritize them by business impact and urgency.

Anomalies:
{json.dumps(findings_summary, indent=2)}

Return a JSON array of indices in priority order (highest priority first) with brief reasoning.
Format: [{{"index": 0, "priority": 1, "reasoning": "..."}}]
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial risk analyst prioritizing anomalies."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=1000
            )

            # Parse JSON response
            response_text = response.choices[0].message.content

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            prioritized = json.loads(response_text.strip())

            return prioritized

        except Exception as e:
            # Fallback: prioritize by severity and confidence
            return [
                {
                    "index": idx,
                    "priority": idx + 1,
                    "reasoning": "LLM prioritization failed, using default order"
                }
                for idx in range(len(findings))
            ]

    def generate_alert_message(
        self,
        findings: List[FindingsObject],
        ensemble_score: float
    ) -> str:
        """
        Generate human-readable alert message

        Args:
            findings: List of findings
            ensemble_score: Combined confidence score

        Returns:
            Alert message for stakeholders
        """
        prompt = f"""
Generate a concise alert message for stakeholders about detected payment anomalies.

Overall Risk Score: {ensemble_score:.2f}/1.0
Number of Anomalies: {len(findings)}

Anomalies detected:
"""
        for finding in findings[:5]:  # Top 5
            prompt += f"\n- [{finding.severity.value.upper()}] {finding.description}"

        prompt += "\n\nWrite a professional alert message (2-3 sentences) suitable for email notification."

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial analyst writing alert notifications."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.4,
                max_tokens=300
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"Alert: {len(findings)} anomalies detected with risk score {ensemble_score:.2f}. Manual review required."

    def _prepare_context(self, findings: List[FindingsObject]) -> Dict[str, Any]:
        """Prepare context dictionary from findings"""
        context = {
            "total_findings": len(findings),
            "by_severity": {},
            "by_type": {},
            "high_confidence": [],
            "summary": []
        }

        for finding in findings:
            # Group by severity
            severity_key = finding.severity.value
            context["by_severity"][severity_key] = context["by_severity"].get(severity_key, 0) + 1

            # Group by type
            type_key = finding.error_type.value
            context["by_type"][type_key] = context["by_type"].get(type_key, 0) + 1

            # Track high confidence
            if finding.confidence_score > 0.8:
                context["high_confidence"].append({
                    "type": finding.error_type.value,
                    "description": finding.description,
                    "confidence": finding.confidence_score
                })

            # Add to summary
            context["summary"].append({
                "type": finding.error_type.value,
                "severity": finding.severity.value,
                "description": finding.description
            })

        return context

    def _build_analysis_prompt(self, context: Dict[str, Any], include_recommendations: bool) -> str:
        """Build prompt for LLM analysis"""
        prompt = f"""
Analyze these financial anomalies detected in an OTC clearing system:

Total Anomalies: {context['total_findings']}

By Severity:
{json.dumps(context['by_severity'], indent=2)}

By Type:
{json.dumps(context['by_type'], indent=2)}

High Confidence Anomalies:
{json.dumps(context['high_confidence'], indent=2)}

All Anomalies:
{json.dumps(context['summary'], indent=2)}

Provide:
1. Executive summary (2-3 sentences)
2. Key insights about patterns or trends
3. Most critical issues to address first
"""

        if include_recommendations:
            prompt += "4. Recommended actions for each critical issue\n"

        prompt += "\nFormat your response as clear, actionable insights for financial operations team."

        return prompt

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response into structured format"""
        # Basic parsing - split by sections
        sections = {
            "full_response": response_text,
            "summary": "",
            "insights": [],
            "recommendations": []
        }

        lines = response_text.split("\n")
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect sections
            if any(keyword in line.lower() for keyword in ["summary", "executive"]):
                current_section = "summary"
            elif any(keyword in line.lower() for keyword in ["insight", "pattern", "trend"]):
                current_section = "insights"
            elif any(keyword in line.lower() for keyword in ["recommend", "action"]):
                current_section = "recommendations"
            elif current_section:
                # Add content to current section
                if line.startswith(("-", "*", "•")) or line[0].isdigit():
                    content = line.lstrip("-*•0123456789. ")
                    if current_section == "summary":
                        sections["summary"] += content + " "
                    elif current_section == "insights":
                        sections["insights"].append(content)
                    elif current_section == "recommendations":
                        sections["recommendations"].append(content)

        return sections


if __name__ == "__main__":
    # Test with sample finding
    analyzer = LLMAnalyzer()

    sample_finding = FindingsObject(
        agent_name="Test",
        timestamp=datetime.now(),
        client_id="TEST-001",
        value_date="2026-02-18",
        error_type=ErrorType.SPLIT_BOOKING_ERROR,
        severity=SeverityLevel.HIGH,
        confidence_score=0.95,
        description="Split booking duplicate detected",
        evidence={"amount": 265000, "components": [33000, 232000]}
    )

    explanation = analyzer.explain_anomaly(sample_finding)
    print("=== LLM Explanation ===")
    print(explanation)
