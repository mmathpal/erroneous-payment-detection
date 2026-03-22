#!/usr/bin/env python3
"""
Resolution Agent

Uses RAG to find similar historical incidents and recommend resolution steps.
Only invoked for high-confidence anomalies (ensemble score > 0.5).
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from src.agents.base import FindingsObject
from src.rag.indexer import get_rag_indexer
from src.rag.sample_incidents import load_incidents_to_rag


@dataclass
class ResolutionRecommendation:
    """Resolution recommendation from RAG"""
    similar_incidents: List[Dict[str, Any]]
    explanation: str
    recommended_steps: List[str]
    confidence: float
    generated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "similar_incidents": self.similar_incidents,
            "explanation": self.explanation,
            "recommended_steps": self.recommended_steps,
            "confidence": self.confidence,
            "generated_at": self.generated_at.isoformat()
        }


class ResolutionAgent:
    """
    RAG-powered resolution agent with optional LLM enhancement

    Responsibilities:
    1. Take findings from other agents as input
    2. Use RAG to retrieve similar historical incidents
    3. Extract common resolution patterns
    4. Generate recommended action steps using LLM (if available)
    5. Return explanation and recommendations
    """

    def __init__(self, min_similarity: float = 0.3, openai_api_key: Optional[str] = None):
        """
        Initialize resolution agent

        Args:
            min_similarity: Minimum similarity score for RAG matches (0-1)
            openai_api_key: OpenAI API key for LLM-enhanced recommendations
        """
        self.min_similarity = min_similarity
        self.openai_api_key = openai_api_key
        self.indexer = get_rag_indexer()

        # Initialize LLM client if API key provided
        self.llm_client = None
        if openai_api_key:
            try:
                from openai import OpenAI
                self.llm_client = OpenAI(api_key=openai_api_key)
                print(f"[ResolutionAgent] LLM client initialized for enhanced recommendations")
            except Exception as e:
                print(f"[ResolutionAgent] Warning: Could not initialize LLM client: {e}")

        # Load sample incidents if indexer is empty
        if self.indexer.get_stats()['total_documents'] == 0:
            num_loaded = load_incidents_to_rag(self.indexer)
            print(f"[ResolutionAgent] Loaded {num_loaded} historical incidents into RAG")
            # ChromaDB persists automatically — no explicit save needed

    def analyze_findings(
        self,
        findings: List[FindingsObject],
        ensemble_score: float
    ) -> Optional[ResolutionRecommendation]:
        """
        Analyze findings and generate resolution recommendation

        Args:
            findings: List of findings from detection agents
            ensemble_score: Overall ensemble score

        Returns:
            ResolutionRecommendation or None if score too low
        """
        # Only process high-confidence findings
        if ensemble_score < 0.5:
            return None

        if not findings:
            return None

        # Group findings by error type
        findings_by_type = {}
        for finding in findings:
            error_type = finding.error_type.value
            if error_type not in findings_by_type:
                findings_by_type[error_type] = []
            findings_by_type[error_type].append(finding)

        # Get similar incidents for each error type
        all_similar_incidents = []
        for error_type, type_findings in findings_by_type.items():
            # Use the highest confidence finding for this type
            primary_finding = max(type_findings, key=lambda f: f.confidence_score)

            # Search RAG
            query = self._build_search_query(primary_finding)
            matches = self.indexer.search(query, top_k=3, min_similarity=self.min_similarity)

            for match in matches:
                all_similar_incidents.append({
                    "incident_id": match.incident.incident_id,
                    "title": match.incident.title,
                    "description": match.incident.description,
                    "incident_type": match.incident.incident_type,
                    "similarity_score": match.similarity_score,
                    "resolution_steps": match.incident.resolution_steps,
                    "outcome": match.incident.outcome,
                    "metadata": match.incident.metadata
                })

        # Remove duplicates by incident_id
        seen_ids = set()
        unique_incidents = []
        for incident in all_similar_incidents:
            if incident["incident_id"] not in seen_ids:
                seen_ids.add(incident["incident_id"])
                unique_incidents.append(incident)

        # Sort by similarity
        unique_incidents.sort(key=lambda x: x["similarity_score"], reverse=True)

        # Take top 3
        top_incidents = unique_incidents[:3]

        # Generate explanation using LLM if available, otherwise use template
        if self.llm_client:
            print(f"[ResolutionAgent] Using LLM to generate explanation")
            explanation = self._generate_llm_explanation(findings, top_incidents, ensemble_score)
        else:
            print(f"[ResolutionAgent] No LLM client available, using template")
            explanation = self._generate_explanation(findings, top_incidents, ensemble_score)

        # Extract common resolution steps
        recommended_steps = self._extract_resolution_steps(top_incidents, findings)

        # Calculate confidence based on similarity and ensemble score
        confidence = self._calculate_confidence(top_incidents, ensemble_score)

        return ResolutionRecommendation(
            similar_incidents=top_incidents,
            explanation=explanation,
            recommended_steps=recommended_steps,
            confidence=confidence,
            generated_at=datetime.now()
        )

    def _build_search_query(self, finding: FindingsObject) -> str:
        """
        Build RAG search query from finding

        Args:
            finding: FindingsObject

        Returns:
            Search query string
        """
        parts = [
            f"Error type: {finding.error_type.value}",
            f"Description: {finding.description}"
        ]

        if finding.client_id:
            parts.append(f"Client: {finding.client_id}")

        # Add key evidence
        if finding.evidence:
            if "amount" in finding.evidence:
                parts.append(f"Amount: {finding.evidence['amount']}")
            if "time_gap_mins" in finding.evidence:
                parts.append(f"Time gap: {finding.evidence['time_gap_mins']} minutes")

        return " ".join(parts)

    def _generate_explanation(
        self,
        findings: List[FindingsObject],
        similar_incidents: List[Dict[str, Any]],
        ensemble_score: float
    ) -> str:
        """
        Generate human-readable explanation

        Args:
            findings: List of findings
            similar_incidents: Similar historical incidents
            ensemble_score: Ensemble confidence score

        Returns:
            Explanation string
        """
        # Determine severity
        if ensemble_score >= 0.8:
            severity = "CRITICAL"
        elif ensemble_score >= 0.6:
            severity = "HIGH"
        else:
            severity = "MEDIUM"

        # Count findings by type
        error_types = [f.error_type.value for f in findings]
        unique_types = set(error_types)

        explanation_parts = [
            f"Detected {len(findings)} anomalies across {len(unique_types)} categories. "
            f"Severity: {severity} (confidence: {ensemble_score:.2f})."
        ]

        # List error types
        if len(unique_types) <= 3:
            types_str = ", ".join(unique_types)
            explanation_parts.append(f"Issues identified: {types_str}.")
        else:
            explanation_parts.append(f"Multiple issue types detected.")

        # Reference similar incidents
        if similar_incidents:
            explanation_parts.append(
                f"\nFound {len(similar_incidents)} similar historical incidents. "
                "Resolution patterns identified from past cases:"
            )

            for idx, incident in enumerate(similar_incidents[:2], 1):
                sim_score = incident['similarity_score']
                explanation_parts.append(
                    f"\n  {idx}. {incident['title']} "
                    f"(similarity: {sim_score:.1%}) - {incident['outcome']}"
                )
        else:
            explanation_parts.append(
                "\nNo similar historical incidents found. "
                "This may be a novel anomaly requiring manual investigation."
            )

        return "".join(explanation_parts)

    def _extract_resolution_steps(
        self,
        similar_incidents: List[Dict[str, Any]],
        findings: List[FindingsObject]
    ) -> List[str]:
        """
        Extract common resolution steps from similar incidents

        Args:
            similar_incidents: Similar historical incidents
            findings: Current findings

        Returns:
            List of recommended resolution steps
        """
        if not similar_incidents:
            # Fallback generic steps
            return [
                "Investigate root cause by reviewing transaction details",
                "Check application logs for errors or warnings",
                "Verify data integrity in database tables",
                "Consult with trading desk or operations team",
                "Document findings and resolution actions taken"
            ]

        # Collect all resolution steps from similar incidents
        all_steps = []
        for incident in similar_incidents:
            steps = incident.get("resolution_steps", [])
            # Weight by similarity
            weight = incident["similarity_score"]
            all_steps.extend([(step, weight) for step in steps])

        # Extract common patterns (simplified - just take first 3-5 steps from top incident)
        if all_steps:
            # Get steps from most similar incident
            top_incident = similar_incidents[0]
            base_steps = top_incident.get("resolution_steps", [])

            # Customize based on current findings
            customized_steps = []

            # Add immediate action for critical issues
            high_severity = any(f.severity.value in ["critical", "high"] for f in findings)
            if high_severity:
                customized_steps.append(
                    "IMMEDIATE: Alert risk management team and put affected trades on hold"
                )

            # Add steps from historical incident
            for step in base_steps[:6]:  # Take up to 6 steps
                customized_steps.append(step)

            # Add monitoring step
            customized_steps.append(
                "Add monitoring alert to prevent recurrence of this issue"
            )

            return customized_steps

        return []

    def _generate_llm_explanation(
        self,
        findings: List[FindingsObject],
        similar_incidents: List[Dict[str, Any]],
        ensemble_score: float
    ) -> str:
        """
        Generate LLM-powered explanation and recommendations

        Args:
            findings: List of findings
            similar_incidents: Similar historical incidents
            ensemble_score: Ensemble confidence score

        Returns:
            LLM-generated explanation string
        """
        # Build context for LLM
        findings_context = []
        for finding in findings:
            findings_context.append({
                "type": finding.error_type.value,
                "description": finding.description,
                "confidence": finding.confidence_score,
                "severity": finding.severity.value,
                "evidence": finding.evidence
            })

        incidents_context = []
        for incident in similar_incidents:
            incidents_context.append({
                "title": incident["title"],
                "description": incident["description"],
                "similarity": f"{incident['similarity_score']:.0%}",
                "resolution_steps": incident["resolution_steps"],
                "outcome": incident["outcome"]
            })

        # Create prompt
        prompt = f"""You are an expert in payment risk management for OTC clearing operations.
Analyze the following payment risk detection findings and provide a clear, actionable recommendation.

**Current Findings:**
"""
        for i, finding in enumerate(findings_context, 1):
            prompt += f"\n{i}. [{finding['type']}] {finding['description']}"
            prompt += f"\n   Confidence: {finding['confidence']:.0%}, Severity: {finding['severity']}"

        prompt += f"\n\n**Overall Detection Confidence:** {ensemble_score:.0%}"

        if incidents_context:
            prompt += "\n\n**Similar Past Incidents:**"
            for i, incident in enumerate(incidents_context, 1):
                prompt += f"\n\n{i}. {incident['title']} (Similarity: {incident['similarity']})"
                prompt += f"\n   Description: {incident['description']}"
                prompt += f"\n   Resolution: {incident['resolution_steps'][0] if incident['resolution_steps'] else 'N/A'}"
                prompt += f"\n   Outcome: {incident['outcome']}"

        prompt += """

**Your Task:**
Provide a concise recommendation in 2-3 paragraphs that:
1. Summarizes what was detected and why it's concerning
2. Explains the likely root cause based on similar incidents
3. Recommends specific actions to resolve this issue
4. Mentions any immediate risks or urgency

Keep the response professional, clear, and actionable for operations team members."""

        try:
            print(f"[ResolutionAgent] Calling OpenAI GPT-4o-mini API...")
            # Call OpenAI API
            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert payment risk analyst specializing in OTC clearing operations. Provide clear, actionable recommendations based on detection findings and historical incident patterns."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Low temperature for more consistent, factual responses
                max_tokens=500
            )

            explanation = response.choices[0].message.content.strip()
            print(f"[ResolutionAgent] LLM response received ({len(explanation)} chars)")
            return explanation

        except Exception as e:
            print(f"[ResolutionAgent] ERROR - LLM call failed: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            # Fallback to template-based explanation
            return self._generate_explanation(findings, similar_incidents, ensemble_score)

    def _calculate_confidence(
        self,
        similar_incidents: List[Dict[str, Any]],
        ensemble_score: float
    ) -> float:
        """
        Calculate confidence in recommendation

        Args:
            similar_incidents: Similar incidents found
            ensemble_score: Detection ensemble score

        Returns:
            Confidence score (0-1)
        """
        if not similar_incidents:
            # Low confidence if no similar incidents
            return ensemble_score * 0.5

        # Average similarity of top incidents
        avg_similarity = sum(
            inc["similarity_score"] for inc in similar_incidents
        ) / len(similar_incidents)

        # Combine ensemble score and RAG similarity
        confidence = (ensemble_score * 0.6) + (avg_similarity * 0.4)

        return min(max(confidence, 0.0), 1.0)

    def get_incident_details(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific historical incident

        Args:
            incident_id: Incident identifier

        Returns:
            Incident details or None
        """
        incident = self.indexer.get_incident_by_id(incident_id)

        if incident is None:
            return None

        return incident.to_dict()


def main():
    """Test the resolution agent"""
    from src.agents.base import FindingsObject, ErrorType, SeverityLevel

    # Create sample findings
    findings = [
        FindingsObject(
            agent_name="RuleBasedDetector",
            timestamp=datetime.now(),
            client_id="XYZ",
            value_date="2024-03-05",
            error_type=ErrorType.SPLIT_BOOKING_ERROR,
            severity=SeverityLevel.HIGH,
            confidence_score=0.95,
            description="Split booking duplicate detected: amounts 232+33 and 265",
            evidence={
                "amount": 265,
                "time_gap_mins": 45,
                "pattern": "R+D=D"
            },
            recommendation="Investigate duplicate booking pattern"
        )
    ]

    # Create resolution agent
    agent = ResolutionAgent()

    # Analyze findings
    recommendation = agent.analyze_findings(findings, ensemble_score=0.85)

    if recommendation:
        print("=== Resolution Recommendation ===\n")
        print(f"Confidence: {recommendation.confidence:.2f}\n")
        print(f"Explanation:\n{recommendation.explanation}\n")
        print(f"\nRecommended Steps:")
        for idx, step in enumerate(recommendation.recommended_steps, 1):
            print(f"  {idx}. {step}")
        print(f"\nSimilar Incidents Found: {len(recommendation.similar_incidents)}")
    else:
        print("No recommendation generated (ensemble score too low)")


if __name__ == "__main__":
    main()
