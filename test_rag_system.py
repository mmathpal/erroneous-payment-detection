#!/usr/bin/env python3
"""
Test RAG System

Simple test script to verify RAG indexer and resolution agent are working.
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.rag.indexer import get_rag_indexer
from src.rag.sample_incidents import load_incidents_to_rag
from src.agents.resolution_agent import ResolutionAgent
from src.agents.base import FindingsObject, ErrorType, SeverityLevel
from datetime import datetime


def test_rag_indexer():
    """Test RAG indexer basic functionality"""
    print("=" * 80)
    print("Testing RAG Indexer")
    print("=" * 80)

    # Get indexer
    indexer = get_rag_indexer()

    # Load sample incidents
    print("\n1. Loading sample incidents...")
    num_loaded = load_incidents_to_rag(indexer)
    print(f"   ✓ Loaded {num_loaded} incidents")

    # Get stats
    stats = indexer.get_stats()
    print(f"\n2. Index statistics:")
    print(f"   - Total documents: {stats['total_documents']}")
    print(f"   - Embedding dimension: {stats['embedding_dimension']}")
    print(f"   - Model: {stats['model_name']}")
    print(f"   - Incident types: {', '.join(stats['incident_types'])}")

    # Test search
    print(f"\n3. Testing semantic search...")
    query = "Duplicate booking with split R and D legs, amounts don't match"
    matches = indexer.search(query, top_k=3)

    print(f"   Query: {query}")
    print(f"   Found {len(matches)} matches:\n")

    for match in matches:
        print(f"   {match.rank}. {match.incident.title}")
        print(f"      Similarity: {match.similarity_score:.2%}")
        print(f"      Type: {match.incident.incident_type}")
        print(f"      Outcome: {match.incident.outcome[:80]}...")
        print()

    return indexer


def test_resolution_agent():
    """Test resolution agent"""
    print("=" * 80)
    print("Testing Resolution Agent")
    print("=" * 80)

    # Create sample finding (split booking duplicate)
    finding = FindingsObject(
        agent_name="RuleBasedDetector",
        timestamp=datetime.now(),
        client_id="XYZ",
        value_date="2024-03-05",
        error_type=ErrorType.SPLIT_BOOKING_ERROR,
        severity=SeverityLevel.HIGH,
        confidence_score=0.95,
        description=(
            "Split booking duplicate detected: Two collateral movements within 45 minutes. "
            "Amounts: 232+33 (R+D legs) vs 265 (D leg). Pattern matches EOD boundary crossing."
        ),
        evidence={
            "booking_ids": ["BK-12345", "BK-12346"],
            "amounts": [265, 232],
            "time_gap_mins": 45,
            "delivery_types": ["R+D", "D"],
            "eod_crossed": True
        },
        recommendation="Investigate duplicate booking and verify split booking logic"
    )

    # Create resolution agent
    agent = ResolutionAgent()

    # Analyze
    print("\n1. Analyzing finding...")
    recommendation = agent.analyze_findings([finding], ensemble_score=0.85)

    if recommendation:
        print(f"   ✓ Generated recommendation (confidence: {recommendation.confidence:.2%})")

        print(f"\n2. Explanation:")
        print(f"   {recommendation.explanation}")

        print(f"\n3. Similar incidents found: {len(recommendation.similar_incidents)}")
        for inc in recommendation.similar_incidents:
            print(f"   - {inc['title']} (similarity: {inc['similarity_score']:.1%})")

        print(f"\n4. Recommended resolution steps ({len(recommendation.recommended_steps)} steps):")
        for idx, step in enumerate(recommendation.recommended_steps, 1):
            print(f"   {idx}. {step}")

    else:
        print("   ✗ No recommendation generated")

    return agent


def test_multiple_findings():
    """Test with multiple different finding types"""
    print("\n" + "=" * 80)
    print("Testing Resolution Agent with Multiple Finding Types")
    print("=" * 80)

    findings = [
        FindingsObject(
            agent_name="RuleBasedDetector",
            timestamp=datetime.now(),
            client_id="ABC",
            value_date="2024-05-20",
            error_type=ErrorType.EXPOSURE_LIMIT_BREACH,
            severity=SeverityLevel.CRITICAL,
            confidence_score=1.0,
            description="Exposure 50M exceeds notional 5M by 10x ratio",
            evidence={"exposure": 50000000, "notional": 5000000, "ratio": 10.0},
            recommendation="Immediate investigation required"
        ),
        FindingsObject(
            agent_name="MLAnomalyDetector",
            timestamp=datetime.now(),
            client_id="ABC",
            value_date="2024-05-20",
            error_type=ErrorType.PV_DISCREPANCY,
            severity=SeverityLevel.HIGH,
            confidence_score=0.85,
            description="PV component vs used discrepancy: 73%",
            evidence={"component_pv": 48000000, "used_pv": 13000000, "discrepancy_pct": 73.0},
            recommendation="Review pricing calculation"
        )
    ]

    agent = ResolutionAgent()

    print("\n1. Analyzing 2 findings (exposure + PV discrepancy)...")
    recommendation = agent.analyze_findings(findings, ensemble_score=0.92)

    if recommendation:
        print(f"   ✓ Generated recommendation (confidence: {recommendation.confidence:.2%})")
        print(f"\n2. Explanation:")
        print(f"   {recommendation.explanation}")
        print(f"\n3. Recommended steps: {len(recommendation.recommended_steps)}")
        for idx, step in enumerate(recommendation.recommended_steps[:5], 1):
            print(f"   {idx}. {step}")
    else:
        print("   ✗ No recommendation generated")


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("RAG SYSTEM TEST SUITE")
    print("=" * 80 + "\n")

    try:
        # Test 1: RAG Indexer
        test_rag_indexer()

        # Test 2: Resolution Agent (single finding)
        test_resolution_agent()

        # Test 3: Multiple findings
        test_multiple_findings()

        print("\n" + "=" * 80)
        print("✓ ALL TESTS PASSED")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
