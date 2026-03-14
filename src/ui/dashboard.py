#!/usr/bin/env python3
"""
Simple EM Payment Risk Dashboard
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.orchestration.orchestrator import AnomalyDetectionOrchestrator
import os
from dotenv import load_dotenv


def main():
    """Simple dashboard with working logs"""

    st.set_page_config(
        page_title="EM Payment Risk",
        page_icon="🛡️",
        layout="wide"
    )

    st.title("🛡️ EM Payment Risk Management System")

    # Initialize session state
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    if 'alerts' not in st.session_state:
        st.session_state.alerts = []
    if 'detection_complete' not in st.session_state:
        st.session_state.detection_complete = False

    # Sidebar configuration
    st.sidebar.header("⚙️ Configuration")

    # Load config
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    if api_key:
        st.sidebar.success("✅ OpenAI API Key configured")
    else:
        st.sidebar.warning("⚠️ No OpenAI API Key (RAG will use templates)")

    use_ml = st.sidebar.checkbox("ML Detection", value=True)
    use_llm = st.sidebar.checkbox("LLM Analysis", value=bool(api_key))
    use_rag = st.sidebar.checkbox("RAG Recommendations", value=True)

    st.sidebar.markdown("---")

    # Run button
    run_detection = st.sidebar.button("▶️ Run Detection", type="primary", use_container_width=True)

    # Clear button
    if st.sidebar.button("🗑️ Clear Results", use_container_width=True):
        st.session_state.logs = []
        st.session_state.alerts = []
        st.session_state.detection_complete = False
        st.rerun()

    # Main content
    if run_detection:
        # Clear previous results
        st.session_state.logs = []
        st.session_state.alerts = []
        st.session_state.detection_complete = False

        # Create live log container
        st.markdown("### 📋 Execution Progress")
        log_placeholder = st.empty()

        def add_log(msg):
            """Add log and update display in real-time"""
            st.session_state.logs.append(msg)
            # Update the display immediately
            log_html = "<br>".join(st.session_state.logs)
            log_placeholder.markdown(
                f"""
                <div style="
                    height: 300px;
                    overflow-y: scroll;
                    background-color: #0e1117;
                    color: #fafafa;
                    padding: 1rem;
                    border: 1px solid #262730;
                    border-radius: 0.5rem;
                    font-family: 'Source Code Pro', monospace;
                    font-size: 14px;
                ">
                    {log_html}
                </div>
                <script>
                    var logDiv = document.querySelector('div[style*="overflow-y: scroll"]');
                    if (logDiv) {{
                        logDiv.scrollTop = logDiv.scrollHeight;
                    }}
                </script>
                """,
                unsafe_allow_html=True
            )

        # Add logs with live updates
        add_log(f"🚀 Started detection at {datetime.now().strftime('%H:%M:%S')}")
        add_log("")

        # Initialize orchestrator
        add_log("🔧 Initializing orchestrator...")
        orchestrator = AnomalyDetectionOrchestrator(
            use_ml=use_ml,
            use_llm=use_llm and bool(api_key),
            use_rag=use_rag,
            openai_api_key=api_key
        )
        add_log("✅ Orchestrator initialized")
        add_log("")

        # Run detection
        add_log("🔍 Running rule-based detection...")
        add_log("   - Checking duplicate bookings...")
        add_log("   - Checking PV discrepancies...")
        add_log("   - Checking booking time anomalies...")

        if use_ml:
            add_log("")
            add_log("🤖 Running ML-based detection...")
            add_log("   - Loading ML models...")
            add_log("   - Analyzing trade patterns...")

        # Run orchestrator
        alerts = orchestrator.run_full_detection()
        st.session_state.alerts = alerts

        add_log("")
        add_log(f"📊 Found {len(alerts)} alerts")

        # Log each alert
        for i, alert in enumerate(alerts, 1):
            add_log(f"   Alert {i}: {alert.client_id} - Risk Score: {alert.risk_score:.1f}")

        if use_rag and any(a.ensemble_score >= 0.5 for a in alerts):
            add_log("")
            add_log("💡 Generating RAG recommendations...")
            high_risk_count = sum(1 for a in alerts if a.ensemble_score >= 0.5)
            add_log(f"   - Processing {high_risk_count} high-risk alerts...")
            if api_key:
                add_log("   - Using LLM-enhanced recommendations...")
            else:
                add_log("   - Using template-based recommendations...")

        add_log("")
        add_log(f"✅ Detection completed at {datetime.now().strftime('%H:%M:%S')}")
        st.session_state.detection_complete = True

        st.success(f"✅ Detection complete! Found {len(st.session_state.alerts)} alerts")
        st.rerun()

    # Show logs if available
    if st.session_state.logs:
        st.markdown("---")
        st.markdown("### 📋 Execution Logs")

        log_html = "<br>".join(st.session_state.logs)
        st.markdown(
            f"""
            <div style="
                height: 300px;
                overflow-y: scroll;
                background-color: #0e1117;
                color: #fafafa;
                padding: 1rem;
                border: 1px solid #262730;
                border-radius: 0.5rem;
                font-family: 'Source Code Pro', monospace;
                font-size: 14px;
            ">
                {log_html}
            </div>
            """,
            unsafe_allow_html=True
        )

    # Show alerts if available
    if st.session_state.detection_complete and st.session_state.alerts:
        st.markdown("---")
        st.markdown("### 🚨 Detected Alerts")

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        critical_count = sum(1 for a in st.session_state.alerts if a.confidence_level.value == "critical")
        high_count = sum(1 for a in st.session_state.alerts if a.confidence_level.value == "high")
        medium_count = sum(1 for a in st.session_state.alerts if a.confidence_level.value == "medium")
        low_count = sum(1 for a in st.session_state.alerts if a.confidence_level.value == "low")

        col1.metric("🔴 Critical", critical_count)
        col2.metric("🟠 High", high_count)
        col3.metric("🟡 Medium", medium_count)
        col4.metric("⚪ Low", low_count)

        # Alert cards
        for alert in st.session_state.alerts:
            # Determine color
            if alert.confidence_level.value == "critical":
                color = "#ff4b4b"
                emoji = "🔴"
            elif alert.confidence_level.value == "high":
                color = "#ff8c00"
                emoji = "🟠"
            elif alert.confidence_level.value == "medium":
                color = "#ffa500"
                emoji = "🟡"
            else:
                color = "#808080"
                emoji = "⚪"

            with st.expander(f"{emoji} **{alert.client_id}** - Risk Score: {alert.risk_score:.1f}/100", expanded=False):
                col1, col2, col3 = st.columns(3)
                col1.metric("Ensemble Score", f"{alert.ensemble_score:.2f}")
                col2.metric("Risk Level", alert.risk_level.upper())
                col3.metric("Findings", len(alert.agent_findings))

                st.markdown("**Detected Issues:**")
                for finding in alert.agent_findings:
                    st.markdown(f"- **[{finding.error_type.value}]** {finding.description}")

                if alert.risk_factors:
                    st.markdown("**Risk Factors:**")
                    for factor in alert.risk_factors:
                        st.markdown(f"- {factor}")

                if alert.resolution_recommendation:
                    st.markdown("**💡 Resolution Recommendation:**")
                    st.info(alert.resolution_recommendation)


if __name__ == "__main__":
    main()
