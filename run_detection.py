#!/usr/bin/env python3
"""
Simple runner for EM Payment Risk Management System
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
load_dotenv()

from src.agents.orchestration.orchestrator import AnomalyDetectionOrchestrator


def main():
    """Run payment risk analysis"""
    print("=" * 80)
    print("EM PAYMENT RISK MANAGEMENT SYSTEM")
    print("=" * 80)
    print()

    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    use_llm = bool(api_key) and api_key != "your-openai-api-key-here"

    if not use_llm:
        print("⚠️  OPENAI_API_KEY not set - LLM analysis disabled")
        print("   Configure in .env file or set: export OPENAI_API_KEY='your-key'\n")

    # Initialize orchestrator
    orchestrator = AnomalyDetectionOrchestrator(
        use_ml=True,
        use_llm=use_llm,
        openai_api_key=api_key
    )

    # Run detection
    try:
        alerts = orchestrator.run_full_detection()

        # Generate and display report
        report = orchestrator.generate_report(alerts)
        print(report)

        # Save report
        output_file = f"payment_risk_report_{orchestrator.rule_detector.db.execute_query('SELECT GETDATE() as now')[0]['now'].strftime('%Y%m%d_%H%M%S')}.txt"
        with open(output_file, "w") as f:
            f.write(report)

        print(f"\n✓ Report saved to: {output_file}")

        # Summary statistics
        print("\n" + "=" * 80)
        print("RISK ASSESSMENT SUMMARY")
        print("=" * 80)
        print(f"Total Payment Risk Alerts: {len(alerts)}")
        print(f"Critical/High Risk: {sum(1 for a in alerts if a.confidence_level.value in ['critical', 'high'])}")
        print(f"Average Risk Score: {sum(a.ensemble_score for a in alerts) / len(alerts):.2f}" if alerts else "N/A")

    except Exception as e:
        print(f"\n✗ Error during risk analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
