#!/usr/bin/env python3
"""
Streamlit Dashboard for EM Anomaly Detection System
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from typing import List, Dict, Any

from src.agents.orchestration.orchestrator import AnomalyDetectionOrchestrator
from src.agents.base import Alert, SeverityLevel


# Page config
st.set_page_config(
    page_title="EM Anomaly Detection",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .alert-card {
        border-left: 4px solid;
        padding: 1rem;
        margin: 1rem 0;
        background-color: white;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .alert-critical {
        border-left-color: #d32f2f;
    }
    .alert-high {
        border-left-color: #f57c00;
    }
    .alert-medium {
        border-left-color: #fbc02d;
    }
    .alert-low {
        border-left-color: #388e3c;
    }
    .risk-score {
        font-size: 2rem;
        font-weight: bold;
    }
    .risk-critical { color: #d32f2f; }
    .risk-high { color: #f57c00; }
    .risk-medium { color: #fbc02d; }
    .risk-low { color: #388e3c; }
</style>
""", unsafe_allow_html=True)


def get_risk_color(risk_level: str) -> str:
    """Get color for risk level"""
    colors = {
        "critical": "#d32f2f",
        "high": "#f57c00",
        "medium": "#fbc02d",
        "low": "#388e3c",
        "minimal": "#9e9e9e"
    }
    return colors.get(risk_level.lower(), "#9e9e9e")


def format_risk_badge(risk_score: float, risk_level: str) -> str:
    """Format risk score with badge"""
    color = get_risk_color(risk_level)
    return f'<span style="background-color: {color}; color: white; padding: 0.25rem 0.75rem; border-radius: 1rem; font-weight: bold;">{risk_score:.1f}/100 - {risk_level.upper()}</span>'


def render_alert_card(alert: Alert, index: int):
    """Render a single alert card"""

    # Determine card class based on risk level
    card_class = f"alert-{alert.risk_level}"

    with st.container():
        st.markdown(f'<div class="alert-card {card_class}">', unsafe_allow_html=True)

        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            st.markdown(f"**Alert #{index + 1}**: {alert.client_id}")
            st.caption(f"ID: {alert.alert_id[:8]}...")

        with col2:
            st.markdown(format_risk_badge(alert.risk_score, alert.risk_level), unsafe_allow_html=True)

        with col3:
            st.caption(f"Findings: {len(alert.agent_findings)}")
            st.caption(f"Score: {alert.ensemble_score:.2f}")

        # Expandable details
        with st.expander("📋 View Details"):

            # Risk factors
            if alert.risk_factors:
                st.markdown("**Key Risk Factors:**")
                for factor in alert.risk_factors:
                    st.markdown(f"• {factor}")

            # Findings
            st.markdown("**Detected Issues:**")
            for finding in alert.agent_findings:
                st.markdown(f"""
                - **{finding.error_type.value}** ({finding.severity.value})
                  - {finding.description}
                  - Confidence: {finding.confidence_score:.2f}
                  - Agent: {finding.agent_name}
                """)

            # Evidence
            if alert.agent_findings:
                st.markdown("**Evidence:**")
                show_evidence = st.checkbox("Show raw evidence", key=f"evidence_{alert.alert_id}")
                if show_evidence:
                    for idx, finding in enumerate(alert.agent_findings):
                        st.caption(f"Finding {idx + 1} - {finding.agent_name}")
                        st.json(finding.evidence)

            # Actions
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✓ Mark Reviewed", key=f"review_{alert.alert_id}"):
                    st.success("Marked as reviewed")
            with col2:
                if st.button("🚨 Raise Case", key=f"case_{alert.alert_id}"):
                    st.info("Case raised (not implemented)")
            with col3:
                if st.button("✗ Dismiss", key=f"dismiss_{alert.alert_id}"):
                    st.warning("Dismissed")

        st.markdown('</div>', unsafe_allow_html=True)


def main():
    """Main dashboard"""

    # Header
    st.markdown('<div class="main-header">🔍 Exposure Manager - Anomaly Detection</div>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")

        # API Key Status
        api_key = os.getenv("OPENAI_API_KEY")
        has_api_key = bool(api_key) and api_key != "your-openai-api-key-here"

        # Detection options
        st.subheader("Detection Engines")
        use_ml = st.checkbox("Enable ML Detection", value=True)
        use_llm = st.checkbox("Enable LLM Analysis", value=has_api_key, disabled=not has_api_key)

        st.subheader("Filters")
        min_risk_score = st.slider("Minimum Risk Score", 0, 100, 50)

        severity_filter = st.multiselect(
            "Severity Levels",
            ["CRITICAL", "HIGH", "MEDIUM", "LOW", "MINIMAL"],
            default=["CRITICAL", "HIGH", "MEDIUM"]
        )

        st.subheader("Actions")
        run_detection = st.button("🔄 Run Detection", type="primary", use_container_width=True)

        st.divider()

        st.caption(f"Last run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize session state
    if 'alerts' not in st.session_state:
        st.session_state.alerts = None

    # Run detection
    if run_detection:
        try:
            # Progress tracking in sidebar
            with st.sidebar:
                st.markdown("---")
                st.markdown("### 🔄 Detection in Progress")

                step_display = st.empty()
                agent_display = st.empty()
                progress_bar = st.progress(0)
                status_text = st.empty()

                st.markdown("**Execution Log:**")
                log_placeholder = st.empty()
                logs = []

            def add_log(message, emoji="•"):
                logs.append(f"{emoji} {message}")
                with st.sidebar:
                    log_placeholder.markdown("\n".join(logs[-15:]))  # Show last 15 entries

            # Step 1: Initialize
            step_display.markdown("### 📍 Step 1/6")
            agent_display.markdown("### Agent: Orchestration Agent")
            status_text.markdown("**Initializing detection system...**")
            progress_bar.progress(5)
            add_log("**[Orchestration Agent]** Initializing detection system...", "🔧")

            add_log("Loading configuration from .env", "⚙️")
            add_log(f"Database: SQL Server ({os.getenv('SQL_SERVER_HOST', 'localhost')})", "💾")
            progress_bar.progress(8)

            orchestrator = AnomalyDetectionOrchestrator(
                use_ml=use_ml,
                use_llm=use_llm and has_api_key,
                openai_api_key=api_key if has_api_key else None
            )
            add_log("✓ Rule-based engine initialized", "✅")
            if use_ml:
                add_log("✓ ML engine initialized (Isolation Forest)", "✅")
            if use_llm and has_api_key:
                add_log("✓ LLM engine initialized (GPT-4o-mini)", "✅")
            progress_bar.progress(10)

            # Step 2: Rule-based detection
            step_display.markdown("### 📍 Step 2/6")
            agent_display.markdown("### Agent: Rule-Based Detection Agent")
            status_text.markdown("**Running rule-based detection (8 rules)...**")
            add_log("", "")
            add_log("**[Rule-Based Detection Agent]** Starting rule-based detection (8 rules)...", "🔍")
            progress_bar.progress(12)

            # Split booking duplicates
            add_log("Running Rule 1/8: Split booking duplicate detection...", "📌")
            split_findings = orchestrator.rule_detector.detect_split_booking_duplicates()
            add_log(f"  → Found {len(split_findings)} split booking duplicates", "📊")
            progress_bar.progress(15)

            # DRA duplicates
            add_log("Running Rule 2/8: DRA duplicate detection...", "📌")
            dra_findings = orchestrator.rule_detector.detect_dra_duplicates()
            add_log(f"  → Found {len(dra_findings)} DRA duplicates", "📊")
            progress_bar.progress(18)

            # Trade duplicates
            add_log("Running Rule 3/8: Trade duplicate detection...", "📌")
            trade_dup_findings = orchestrator.rule_detector.detect_trade_duplicates()
            add_log(f"  → Found {len(trade_dup_findings)} trade duplicates", "📊")
            progress_bar.progress(21)

            # Date anomalies
            add_log("Running Rule 4/8: Date anomaly detection...", "📌")
            date_findings = orchestrator.rule_detector.detect_date_anomalies()
            add_log(f"  → Found {len(date_findings)} date anomalies", "📊")
            progress_bar.progress(24)

            # Exposure anomalies
            add_log("Running Rule 5/8: Exposure anomaly detection...", "📌")
            exposure_findings = orchestrator.rule_detector.detect_exposure_anomalies()
            add_log(f"  → Found {len(exposure_findings)} exposure anomalies", "📊")
            progress_bar.progress(27)

            # Expired active trades
            add_log("Running Rule 6/8: Expired active trade detection...", "📌")
            expired_findings = orchestrator.rule_detector.detect_expired_active_trades()
            add_log(f"  → Found {len(expired_findings)} expired active trades", "📊")
            progress_bar.progress(30)

            # Negative values
            add_log("Running Rule 7/8: Negative value detection...", "📌")
            negative_findings = orchestrator.rule_detector.detect_negative_values()
            add_log(f"  → Found {len(negative_findings)} negative value issues", "📊")
            progress_bar.progress(33)

            # PV discrepancies
            add_log("Running Rule 8/8: PV discrepancy detection...", "📌")
            pv_findings = orchestrator.rule_detector.detect_pv_discrepancies()
            add_log(f"  → Found {len(pv_findings)} PV discrepancies", "📊")
            progress_bar.progress(36)

            rule_findings = (split_findings + dra_findings + trade_dup_findings +
                           date_findings + exposure_findings + expired_findings +
                           negative_findings + pv_findings)

            add_log(f"✓ Rule-based detection complete: {len(rule_findings)} total findings", "✅")
            status_text.markdown(f"**✓ Rule-based detection complete - {len(rule_findings)} findings**")
            progress_bar.progress(40)

            # Step 3: ML detection
            add_log("", "")
            step_display.markdown("### 📍 Step 3/6")
            if use_ml:
                agent_display.markdown("### Agent: ML Detection Agent")
                status_text.markdown("**Running ML-based detection (Isolation Forest)...**")
                add_log("**[ML Detection Agent]** Starting ML-based detection (Isolation Forest)...", "🤖")
                progress_bar.progress(42)

                add_log("Loading trade data for ML analysis...", "📥")
                progress_bar.progress(45)

                add_log("Detecting trade anomalies with Isolation Forest...", "🧮")
                trade_ml = orchestrator.ml_detector.detect_trade_anomalies()
                add_log(f"  → Found {len(trade_ml)} trade anomalies", "📊")
                progress_bar.progress(50)

                add_log("Loading collateral movement data for ML analysis...", "📥")
                progress_bar.progress(52)

                add_log("Detecting collateral anomalies with Isolation Forest...", "🧮")
                collateral_ml = orchestrator.ml_detector.detect_collateral_anomalies()
                add_log(f"  → Found {len(collateral_ml)} collateral movement anomalies", "📊")
                progress_bar.progress(55)

                ml_findings = trade_ml + collateral_ml
                add_log(f"✓ ML detection complete: {len(ml_findings)} total findings", "✅")
                status_text.markdown(f"**✓ ML detection complete - {len(ml_findings)} findings**")
                progress_bar.progress(60)
            else:
                agent_display.markdown("### Agent: ML Detection Agent (Disabled)")
                ml_findings = []
                add_log("ML detection disabled (skipped)", "⊘")
                status_text.markdown("**ML detection disabled**")
                progress_bar.progress(60)

            # Step 4: Group findings
            add_log("", "")
            step_display.markdown("### 📍 Step 4/6")
            agent_display.markdown("### Agent: Risk Scoring Agent")
            status_text.markdown("**Grouping findings and calculating risk scores...**")
            add_log("**[Risk Scoring Agent]** Grouping findings by entity/client...", "📊")
            progress_bar.progress(62)

            all_findings = rule_findings + ml_findings
            grouped_findings = orchestrator._group_findings(all_findings)
            add_log(f"✓ Grouped into {len(grouped_findings)} unique entities", "✅")
            progress_bar.progress(70)

            # Create alerts with risk scoring
            add_log("Calculating risk scores for each entity...", "🎯")
            alerts = []
            entity_count = len(grouped_findings)
            for idx, (entity_id, findings) in enumerate(grouped_findings.items()):
                alert = orchestrator._create_alert(entity_id, findings)
                alerts.append(alert)
                if idx < 5:  # Show first 5
                    add_log(f"  → Entity {entity_id}: Risk score {alert.risk_score:.1f}/100 ({alert.risk_level})", "📈")
                progress_bar.progress(70 + int((idx + 1) / entity_count * 10))

            if entity_count > 5:
                add_log(f"  → ... and {entity_count - 5} more entities", "📈")

            add_log(f"✓ Created {len(alerts)} alerts with comprehensive risk assessments", "✅")
            status_text.markdown(f"**✓ Risk scoring complete - {len(alerts)} alerts**")
            progress_bar.progress(80)

            # Step 5: LLM analysis
            add_log("", "")
            step_display.markdown("### 📍 Step 5/6")
            if use_llm and has_api_key:
                agent_display.markdown("### Agent: LLM Analysis Agent")
                status_text.markdown("**Running LLM analysis (GPT-4o-mini)...**")
                add_log("**[LLM Analysis Agent]** Preparing context for LLM analysis...", "🧠")
                progress_bar.progress(82)

                add_log("Sending request to OpenAI GPT-4o-mini...", "📡")
                add_log(f"  → Model: gpt-4o-mini", "ℹ️")
                add_log(f"  → Analyzing {len(all_findings)} findings", "ℹ️")
                progress_bar.progress(85)

                try:
                    analysis = orchestrator.llm_analyzer.analyze_anomalies(all_findings)
                    add_log("✓ LLM analysis successful", "✅")
                    if analysis.get('summary'):
                        add_log(f"  → Summary: {analysis['summary'][:100]}...", "💡")
                    progress_bar.progress(90)
                except Exception as llm_error:
                    add_log(f"⚠ LLM analysis failed: {str(llm_error)}", "⚠️")
                    add_log("Continuing without LLM insights...", "⚠️")
                    progress_bar.progress(90)

                status_text.markdown("**✓ LLM analysis complete**")
            else:
                agent_display.markdown("### Agent: LLM Analysis Agent (Disabled)")
                add_log("LLM analysis disabled (skipped)", "⊘")
                status_text.markdown("**LLM analysis disabled**")
                progress_bar.progress(90)

            # Step 6: Finalize
            add_log("", "")
            step_display.markdown("### 📍 Step 6/6")
            agent_display.markdown("### Agent: Report Generation Agent")
            status_text.markdown("**Finalizing detection report...**")
            add_log("**[Report Generation Agent]** Generating summary statistics...", "📊")
            progress_bar.progress(92)

            critical_high = sum(1 for a in alerts if a.risk_score >= 70)
            add_log(f"  → Total alerts: {len(alerts)}", "📋")
            add_log(f"  → Critical/High risk: {critical_high}", "📋")
            add_log(f"  → Total findings: {len(all_findings)}", "📋")
            progress_bar.progress(95)

            add_log("Preparing alert data for display...", "🎨")
            progress_bar.progress(98)

            # Complete
            progress_bar.progress(100)
            add_log("", "")
            add_log("✓ Detection pipeline completed successfully!", "🎉")

            step_display.markdown("### ✅ Complete")
            agent_display.markdown("### Status: All Agents Complete")
            status_text.markdown(f"### ✅ Detection Complete!")

            st.session_state.alerts = alerts
            st.success(f"✓ Found {len(alerts)} alerts ({len(all_findings)} total findings) - {critical_high} critical/high risk")

        except Exception as e:
            st.error(f"Error during detection: {str(e)}")
            add_log(f"✗ Error: {str(e)}", "❌")
            st.exception(e)

    # Display results
    if st.session_state.alerts:
        alerts = st.session_state.alerts

        # Filter alerts
        filtered_alerts = [
            alert for alert in alerts
            if alert.risk_score >= min_risk_score
            and alert.confidence_level.value.upper() in severity_filter
        ]

        # Summary metrics
        st.subheader("📊 Summary Statistics")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Alerts", len(alerts))

        with col2:
            critical_high = sum(1 for a in alerts if a.risk_score >= 70)
            st.metric("Critical/High", critical_high)

        with col3:
            avg_score = sum(a.ensemble_score for a in alerts) / len(alerts) if alerts else 0
            st.metric("Avg Confidence", f"{avg_score:.2f}")

        with col4:
            avg_risk = sum(a.risk_score for a in alerts) / len(alerts) if alerts else 0
            st.metric("Avg Risk Score", f"{avg_risk:.1f}")

        # Risk distribution
        st.subheader("📈 Risk Distribution")

        risk_counts = {}
        for alert in alerts:
            level = alert.risk_level.upper()
            risk_counts[level] = risk_counts.get(level, 0) + 1

        if risk_counts:
            df_risk = pd.DataFrame([
                {"Risk Level": level, "Count": count}
                for level, count in sorted(risk_counts.items(),
                                          key=lambda x: ["CRITICAL", "HIGH", "MEDIUM", "LOW", "MINIMAL"].index(x[0]))
            ])
            st.bar_chart(df_risk.set_index("Risk Level"))

        # Alerts list
        st.subheader(f"🚨 Alerts ({len(filtered_alerts)} shown)")

        if filtered_alerts:
            # Sort by risk score
            filtered_alerts.sort(key=lambda x: x.risk_score, reverse=True)

            for idx, alert in enumerate(filtered_alerts):
                render_alert_card(alert, idx)
        else:
            st.info("No alerts match the current filters")

        # Export
        st.divider()

        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("📥 Export Report"):
                report = generate_text_report(alerts)
                st.download_button(
                    label="Download Report",
                    data=report,
                    file_name=f"anomaly_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )

    else:
        st.info("👈 Click 'Run Detection' in the sidebar to start")


def generate_text_report(alerts: List[Alert]) -> str:
    """Generate text report for export"""
    report = []
    report.append("=" * 80)
    report.append("EXPOSURE MANAGER - ANOMALY DETECTION REPORT")
    report.append("=" * 80)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Total Alerts: {len(alerts)}")
    report.append("")

    # Summary
    risk_counts = {}
    for alert in alerts:
        level = alert.risk_level.upper()
        risk_counts[level] = risk_counts.get(level, 0) + 1

    report.append("Alerts by Risk Level:")
    for level, count in sorted(risk_counts.items()):
        report.append(f"  {level}: {count}")

    report.append("")
    report.append("=" * 80)
    report.append("ALERTS")
    report.append("=" * 80)

    # Sort by risk score
    sorted_alerts = sorted(alerts, key=lambda x: x.risk_score, reverse=True)

    for idx, alert in enumerate(sorted_alerts):
        report.append(f"\nAlert #{idx + 1}")
        report.append(f"  Entity: {alert.client_id}")
        report.append(f"  Risk Score: {alert.risk_score:.1f}/100 ({alert.risk_level.upper()})")
        report.append(f"  Ensemble Score: {alert.ensemble_score:.2f}")
        report.append(f"  Findings: {len(alert.agent_findings)}")

        if alert.risk_factors:
            report.append("  Key Risk Factors:")
            for factor in alert.risk_factors:
                report.append(f"    • {factor}")

        report.append("  Detected Issues:")
        for finding in alert.agent_findings:
            report.append(f"    - [{finding.error_type.value}] {finding.description}")

    report.append("\n" + "=" * 80)
    report.append("END OF REPORT")
    report.append("=" * 80)

    return "\n".join(report)


if __name__ == "__main__":
    main()
