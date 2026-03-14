#!/usr/bin/env python3
"""
Streamlit Dashboard for EM Payment Risk Management System - Simplified
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import os
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from datetime import datetime
from typing import List

from src.agents.orchestration.orchestrator import AnomalyDetectionOrchestrator
from src.agents.base import Alert

# Page config
st.set_page_config(
    page_title="EM Payment Risk Management",
    page_icon="🛡️",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .alert-card {
        padding: 1rem;
        margin: 0.3rem 0;
        border-radius: 0.5rem;
        border-left: 5px solid;
    }
    .alert-critical { border-left-color: #d32f2f; background: #ffe8e8; }
    .alert-high { border-left-color: #f57c00; background: #fff3e0; }
    .alert-medium { border-left-color: #fbc02d; background: #fffde7; }
    .alert-low { border-left-color: #388e3c; background: #e8f5e9; }
</style>
""", unsafe_allow_html=True)


def render_alert_card(alert: Alert):
    """Render simplified alert card"""
    card_class = f"alert-{alert.risk_level}"

    with st.container():
        st.markdown(f'<div class="alert-card {card_class}">', unsafe_allow_html=True)

        # Header
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### 🚨 {alert.client_id}")
            st.caption(f"Alert ID: {alert.alert_id[:8]}")
        with col2:
            st.metric("Risk Score", f"{alert.risk_score:.0f}/100")

        # Expandable details
        with st.expander("🔍 View Details"):
            st.markdown("**Detected Issues:**")
            for finding in alert.agent_findings:
                st.markdown(f"- [{finding.error_type.value}] {finding.description}")

            st.markdown("---")
            st.markdown("**💡 Resolution Recommendations:**")
            if hasattr(alert, 'resolution_recommendation') and alert.resolution_recommendation:
                st.info(alert.resolution_recommendation)
            else:
                st.caption("ℹ️ No specific recommendations available")

        st.markdown('</div>', unsafe_allow_html=True)


def main():
    """Main dashboard"""
    st.markdown('<h1 style="color: #1f77b4;">🛡️ EM Payment Risk Management System</h1>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")

        api_key = os.getenv("OPENAI_API_KEY")
        has_api_key = bool(api_key) and api_key != "your-openai-api-key-here"

        st.subheader("Detection Engines")
        use_rules = st.checkbox("Rule-Based Detection", value=True)
        use_ml = st.checkbox("ML Detection", value=True)
        use_llm = st.checkbox("LLM Analysis", value=has_api_key, disabled=not has_api_key)

        st.subheader("Filters")
        min_confidence = st.slider("Min Confidence", 0, 100, 50)
        severity_filter = st.multiselect(
            "Severity",
            ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            default=["CRITICAL", "HIGH", "MEDIUM"]
        )

        st.divider()
        run_detection = st.button("🔄 Run Analysis", type="primary", use_container_width=True)

    # Initialize session state
    if 'alerts' not in st.session_state:
        st.session_state.alerts = None
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    if 'show_logs' not in st.session_state:
        st.session_state.show_logs = False

    # Main content area
    main_col = st.container()

    # Run detection
    if run_detection:
        st.session_state.logs = []

        try:
            with st.status("🔄 Running payment risk analysis...", expanded=True) as status:
                # Initialize orchestrator
                st.write("🔧 Initializing detection engines...")
                st.session_state.logs.append("🔧 Initializing detection engines...")
                orchestrator = AnomalyDetectionOrchestrator(
                    use_ml=use_ml,
                    use_llm=use_llm and has_api_key,
                    use_rag=True,
                    openai_api_key=api_key if has_api_key else None
                )

                # Run detection steps
                if use_rules:
                    st.write("🔍 Running rule-based detection...")
                    st.session_state.logs.append("🔍 Running rule-based detection...")
                    rule_findings = orchestrator.rule_detector.detect_all_anomalies()
                    msg = f"  → Found {len(rule_findings)} rule-based findings"
                    st.write(msg)
                    st.session_state.logs.append(msg)
                else:
                    rule_findings = []

                if use_ml:
                    st.write("🤖 Running ML detection...")
                    st.session_state.logs.append("🤖 Running ML detection...")
                    ml_findings = orchestrator.ml_detector.detect_all_anomalies()
                    msg = f"  → Found {len(ml_findings)} ML findings"
                    st.write(msg)
                    st.session_state.logs.append(msg)
                else:
                    ml_findings = []

                # Combine and group
                st.write("📊 Grouping findings...")
                st.session_state.logs.append("📊 Grouping findings...")
                all_findings = rule_findings + ml_findings
                grouped_findings = orchestrator._group_findings(all_findings)

                # Create alerts
                st.write("🎯 Calculating risk scores...")
                st.session_state.logs.append("🎯 Calculating risk scores...")
                alerts = []
                for entity_id, findings in grouped_findings.items():
                    alert = orchestrator._create_alert(entity_id, findings)
                    alerts.append(alert)

                # RAG recommendations
                if orchestrator.resolution_agent:
                    st.write("💡 Generating RAG recommendations...")
                    st.session_state.logs.append("💡 Generating RAG recommendations...")
                    for alert in alerts:
                        if alert.ensemble_score >= 0.5:
                            recommendation = orchestrator.resolution_agent.analyze_findings(
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

                st.write("✅ Analysis complete!")
                st.session_state.logs.append("✅ Analysis complete!")
                st.session_state.alerts = alerts
                status.update(label="✅ Analysis complete!", state="complete")

            st.success(f"✅ Found {len(alerts)} alerts ({len(all_findings)} total findings)")

        except Exception as e:
            st.session_state.logs.append(f"❌ Error: {str(e)}")
            st.error(f"❌ Error: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

    # Always show logs after execution completes
    if st.session_state.logs:
        st.markdown("---")
        with st.expander("📋 Execution Logs", expanded=True):
            st.caption(f"Total: {len(st.session_state.logs)} operations")

            # Create fixed-height scrollable container using HTML
            log_lines = "<br>".join(st.session_state.logs)
            st.markdown(
                f"""
                <div style="
                    height: 300px;
                    overflow-y: scroll;
                    background-color: #0e1117;
                    color: #fafafa;
                    padding: 1rem;
                    border-radius: 0.5rem;
                    border: 1px solid #262730;
                    font-family: 'Source Code Pro', monospace;
                    font-size: 0.875rem;
                    line-height: 1.5;
                ">
                    {log_lines}
                </div>
                """,
                unsafe_allow_html=True
            )

    # Display results
    with main_col:
        if st.session_state.alerts:
            alerts = st.session_state.alerts

            # Filter alerts
            filtered = [
                a for a in alerts
                if (a.ensemble_score * 100) >= min_confidence
                and a.confidence_level.value.upper() in severity_filter
            ]

            st.subheader(f"🚨 Alerts ({len(filtered)} shown)")

            if filtered:
                for alert in filtered:
                    render_alert_card(alert)
            else:
                st.info("No alerts match the current filters")
        else:
            st.info("👈 Click 'Run Analysis' to start")


if __name__ == "__main__":
    main()
