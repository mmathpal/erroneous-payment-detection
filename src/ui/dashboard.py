#!/usr/bin/env python3
"""
Streamlit Dashboard for EM Payment Risk Management System
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
    page_title="EM Payment Risk Management",
    page_icon="🛡️",
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
        border-left: 6px solid;
        padding: 1.5rem;
        margin: 1.5rem 0;
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 0.75rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .alert-card:hover {
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        transform: translateY(-2px);
    }
    .alert-critical {
        border-left-color: #d32f2f;
        background: linear-gradient(135deg, #fff5f5 0%, #ffe8e8 100%);
    }
    .alert-high {
        border-left-color: #f57c00;
        background: linear-gradient(135deg, #fff9f0 0%, #fff3e0 100%);
    }
    .alert-medium {
        border-left-color: #fbc02d;
        background: linear-gradient(135deg, #fffef0 0%, #fffde7 100%);
    }
    .alert-low {
        border-left-color: #388e3c;
        background: linear-gradient(135deg, #f5fff5 0%, #e8f5e9 100%);
    }
    .alert-minimal {
        border-left-color: #9e9e9e;
        background: linear-gradient(135deg, #fafafa 0%, #f5f5f5 100%);
    }
    .risk-score {
        font-size: 2rem;
        font-weight: bold;
    }
    .risk-critical { color: #d32f2f; }
    .risk-high { color: #f57c00; }
    .risk-medium { color: #fbc02d; }
    .risk-low { color: #388e3c; }
    .execution-log {
        background-color: rgba(128, 128, 128, 0.1);
        border: 1px solid rgba(128, 128, 128, 0.3);
        border-radius: 0.5rem;
        padding: 1rem;
        height: 500px;
        overflow-y: auto;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        line-height: 1.6;
        scroll-behavior: smooth;
        color: inherit;
    }
    .log-entry {
        margin: 0.25rem 0;
        white-space: pre-wrap;
        color: inherit;
    }
    button[data-testid="baseButton-secondary"] {
        min-width: 35px !important;
        height: 35px !important;
        padding: 0 !important;
        border-radius: 4px !important;
    }
    button[data-testid="baseButton-secondary"] p {
        font-size: 1.5rem !important;
        font-weight: 300 !important;
        margin: 0 !important;
    }
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


def get_alert_title(alert: Alert) -> str:
    """Generate descriptive alert title based on findings"""
    if not alert.agent_findings:
        return "Unknown Issue Detected"

    # Get primary error type from highest severity finding
    primary_finding = max(alert.agent_findings, key=lambda f: f.confidence_score)
    error_type = primary_finding.error_type.value

    # Map error types to user-friendly titles
    title_map = {
        "duplicate": f"🔄 Duplicate Payment - {alert.client_id}",
        "date_anomaly": f"📅 Date Anomaly - {alert.client_id}",
        "exposure_limit": f"⚠️ Exposure Limit Breach - {alert.client_id}",
        "pv_discrepancy": f"💰 PV Discrepancy - {alert.client_id}",
        "negative_value": f"➖ Negative Value Issue - {alert.client_id}",
        "expired_trade": f"⏰ Expired Active Trade - {alert.client_id}",
        "ml_anomaly": f"🤖 Unusual Pattern Detected - {alert.client_id}",
        "data_quality": f"📊 Data Quality Issue - {alert.client_id}",
    }

    # Find matching title or use default
    for key, title in title_map.items():
        if key in error_type.lower():
            return title

    return f"🔍 Anomaly Detected - {alert.client_id}"


def get_alert_icon(risk_level: str) -> str:
    """Get icon for risk level"""
    icons = {
        "critical": "🚨",
        "high": "⚠️",
        "medium": "🟡",
        "low": "ℹ️",
        "minimal": "✅"
    }
    return icons.get(risk_level.lower(), "🔔")


def render_alert_card(alert: Alert, index: int):
    """Render a single alert card with improved layout"""

    # Determine card class based on risk level
    card_class = f"alert-{alert.risk_level}"
    alert_title = get_alert_title(alert)
    risk_icon = get_alert_icon(alert.risk_level)

    with st.container():
        st.markdown(f'<div class="alert-card {card_class}">', unsafe_allow_html=True)

        # Header row with title and risk badge
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"### {risk_icon} {alert_title}")
            st.caption(f"Alert ID: {alert.alert_id[:8]}... | {len(alert.agent_findings)} findings detected")

        with col2:
            st.markdown(format_risk_badge(alert.risk_score, alert.risk_level), unsafe_allow_html=True)
            st.caption(f"Confidence: {alert.ensemble_score:.0%}")

        # Quick summary metrics in cards
        st.markdown("")
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        with metric_col1:
            st.metric("Risk Score", f"{alert.risk_score:.0f}/100")
        with metric_col2:
            st.metric("Severity", alert.confidence_level.value.title())
        with metric_col3:
            st.metric("Issues", len(alert.agent_findings))
        with metric_col4:
            st.metric("Risk Factors", len(alert.risk_factors))

        # Expandable details
        with st.expander("🔍 View Full Details", expanded=False):

            # Two-column layout for better organization
            detail_col1, detail_col2 = st.columns([1, 1])

            with detail_col1:
                # Risk factors
                st.markdown("#### 🎯 Key Risk Factors")
                if alert.risk_factors:
                    for idx, factor in enumerate(alert.risk_factors, 1):
                        st.markdown(f"**{idx}.** {factor}")
                else:
                    st.info("No specific risk factors identified")

            with detail_col2:
                # Mitigating factors
                st.markdown("#### ✅ Mitigating Factors")
                mitigating_factors = getattr(alert, 'mitigating_factors', [])
                if mitigating_factors:
                    for idx, factor in enumerate(mitigating_factors, 1):
                        st.markdown(f"**{idx}.** {factor}")
                else:
                    st.info("No mitigating factors found")

            st.markdown("---")

            # Findings with better formatting
            st.markdown("#### 📋 Detected Issues")
            for idx, finding in enumerate(alert.agent_findings, 1):
                severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "minimal": "⚪"}.get(finding.severity.value.lower(), "⚫")

                with st.container():
                    st.markdown(f"""
                    **{idx}. {severity_emoji} {finding.error_type.value.replace('_', ' ').title()}**
                    📝 {finding.description}
                    🎯 Confidence: {finding.confidence_score:.0%} | 🤖 Agent: {finding.agent_name}
                    """)
                    st.markdown("")

            # Evidence section
            st.markdown("---")
            st.markdown("#### 🔬 Technical Evidence")
            show_evidence = st.checkbox("Show detailed technical data", key=f"evidence_{alert.alert_id}")
            if show_evidence:
                for idx, finding in enumerate(alert.agent_findings, 1):
                    with st.container():
                        st.markdown(f"**Evidence {idx}** - {finding.agent_name}")
                        st.json(finding.evidence)
                        st.markdown("")

        # Action buttons
        st.markdown("---")
        st.markdown("#### ⚡ Actions")
        action_col1, action_col2, action_col3, action_col4 = st.columns(4)
        with action_col1:
            if st.button("✅ Mark Reviewed", key=f"review_{alert.alert_id}", use_container_width=True):
                st.success("✓ Marked as reviewed")
        with action_col2:
            if st.button("🚨 Raise Case", key=f"case_{alert.alert_id}", use_container_width=True, type="primary"):
                st.info("Case raised to operations team")
        with action_col3:
            if st.button("📧 Send Alert", key=f"email_{alert.alert_id}", use_container_width=True):
                st.info("Alert sent to stakeholders")
        with action_col4:
            if st.button("❌ Dismiss", key=f"dismiss_{alert.alert_id}", use_container_width=True):
                st.warning("Alert dismissed")

        st.markdown('</div>', unsafe_allow_html=True)


def main():
    """Main dashboard"""

    # Header
    st.markdown('<div class="main-header">🛡️ EM Payment Risk Management System</div>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")

        # API Key Status
        api_key = os.getenv("OPENAI_API_KEY")
        has_api_key = bool(api_key) and api_key != "your-openai-api-key-here"

        # Detection options
        st.subheader("Risk Detection Engines")
        use_rules = st.checkbox("Enable Rule-Based Detection", value=True, help="Deterministic rules for known payment error patterns")
        use_ml = st.checkbox("Enable ML Detection", value=True, help="Machine learning anomaly detection (Isolation Forest)")
        use_llm = st.checkbox("Enable LLM Analysis", value=has_api_key, disabled=not has_api_key, help="AI-powered risk analysis and insights (GPT-4o-mini)")

        st.subheader("Filters")
        min_risk_score = st.slider("Minimum Risk Score", 0, 100, 50)

        severity_filter = st.multiselect(
            "Severity Levels",
            ["CRITICAL", "HIGH", "MEDIUM", "LOW", "MINIMAL"],
            default=["CRITICAL", "HIGH", "MEDIUM"]
        )

        st.subheader("Actions")
        run_detection = st.button("🔄 Run Risk Analysis", type="primary", use_container_width=True)

        st.divider()

        st.caption(f"Last run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize session state
    if 'alerts' not in st.session_state:
        st.session_state.alerts = None
    if 'show_progress' not in st.session_state:
        st.session_state.show_progress = True

    # Toggle arrow for progress panel (top right corner)
    col1, col2, col3 = st.columns([5, 0.5, 0.5])
    with col3:
        arrow_symbol = "›" if st.session_state.show_progress else "‹"
        if st.button(arrow_symbol, key="toggle_progress", help="Toggle progress tracker", type="secondary"):
            st.session_state.show_progress = not st.session_state.show_progress
            st.rerun()

    # Create layout based on toggle state
    if st.session_state.show_progress:
        main_col, progress_col = st.columns([2, 1])
    else:
        main_col = st.container()
        progress_col = None

    # Right column - Progress tracking (persistent placeholders)
    if st.session_state.show_progress:
        with progress_col:
            st.markdown("### 🔄 Risk Analysis Progress")
            step_display = st.empty()
            agent_display = st.empty()
            progress_bar_placeholder = st.empty()
            status_text = st.empty()

            st.markdown("---")
            st.markdown("**📋 Execution Log:**")
            log_placeholder = st.empty()
    else:
        # Create None placeholders when collapsed (no-op)
        class NoOpPlaceholder:
            def markdown(self, *args, **kwargs): pass
            def progress(self, *args, **kwargs): pass

        step_display = NoOpPlaceholder()
        agent_display = NoOpPlaceholder()
        progress_bar_placeholder = NoOpPlaceholder()
        status_text = NoOpPlaceholder()
        log_placeholder = NoOpPlaceholder()

    # Initialize progress tracking state
    if 'logs' not in st.session_state:
        st.session_state.logs = []

    # Display existing logs if available (when toggling or after detection)
    if st.session_state.show_progress and st.session_state.logs and progress_col:
        with progress_col:
            log_entries = "".join([f'<div class="log-entry">{log}</div>' for log in st.session_state.logs])
            log_html = f'''
            <div class="execution-log" id="log-container">
                {log_entries}
            </div>
            <script>
                var logContainer = document.getElementById('log-container');
                if (logContainer) {{
                    logContainer.scrollTop = logContainer.scrollHeight;
                }}
            </script>
            '''
            log_placeholder.markdown(log_html, unsafe_allow_html=True)

    # Run detection
    if run_detection:
        try:
            # Reset logs
            st.session_state.logs = []

            # Create progress bar (only if progress panel is shown)
            if st.session_state.show_progress and progress_col:
                with progress_col:
                    progress_bar = progress_bar_placeholder.progress(0)
            else:
                progress_bar = None

            # Helper function for progress bar updates
            def update_progress(value):
                if progress_bar:
                    progress_bar.progress(value)

            # Progress tracking function
            def add_log(message, emoji="•"):
                st.session_state.logs.append(f"{emoji} {message}")
                if st.session_state.show_progress and progress_col:
                    with progress_col:
                        # Wrap logs in scrollable div with all logs
                        log_entries = "".join([f'<div class="log-entry">{log}</div>' for log in st.session_state.logs])
                        log_html = f'''
                        <div class="execution-log" id="log-container">
                            {log_entries}
                        </div>
                        <script>
                            var logContainer = document.getElementById('log-container');
                            if (logContainer) {{
                                logContainer.scrollTop = logContainer.scrollHeight;
                            }}
                        </script>
                        '''
                        log_placeholder.markdown(log_html, unsafe_allow_html=True)

            # Step 1: Initialize
            step_display.markdown("### 📍 Step 1/6")
            agent_display.markdown("### Agent: Orchestration Agent")
            status_text.markdown("**Initializing payment risk analysis...**")
            update_progress(5)
            add_log("**[Orchestration Agent]** Initializing payment risk analysis system...", "🔧")

            add_log("Loading configuration from .env", "⚙️")
            add_log(f"Database: SQL Server ({os.getenv('SQL_SERVER_HOST', 'localhost')})", "💾")
            update_progress(8)

            orchestrator = AnomalyDetectionOrchestrator(
                use_ml=use_ml,
                use_llm=use_llm and has_api_key,
                openai_api_key=api_key if has_api_key else None
            )
            if use_rules:
                add_log("✓ Rule-based engine initialized (8 rules)", "✅")
            if use_ml:
                add_log("✓ ML engine initialized (Isolation Forest)", "✅")
            if use_llm and has_api_key:
                add_log("✓ LLM engine initialized (GPT-4o-mini)", "✅")
            update_progress(10)

            # Step 2: Rule-based detection
            step_display.markdown("### 📍 Step 2/6")
            if use_rules:
                agent_display.markdown("### Agent: Rule-Based Detection Agent")
                status_text.markdown("**Running rule-based detection (8 rules)...**")
                add_log("", "")
                add_log("**[Rule-Based Detection Agent]** Starting rule-based detection (8 rules)...", "🔍")
                update_progress(12)

                # Split booking duplicates
                add_log("Running Rule 1/8: Split booking duplicate detection...", "📌")
                split_findings = orchestrator.rule_detector.detect_split_booking_duplicates()
                add_log(f"  → Found {len(split_findings)} split booking duplicates", "📊")
                update_progress(15)

                # DRA duplicates
                add_log("Running Rule 2/8: DRA duplicate detection...", "📌")
                dra_findings = orchestrator.rule_detector.detect_dra_duplicates()
                add_log(f"  → Found {len(dra_findings)} DRA duplicates", "📊")
                update_progress(18)

                # Trade duplicates
                add_log("Running Rule 3/8: Trade duplicate detection...", "📌")
                trade_dup_findings = orchestrator.rule_detector.detect_trade_duplicates()
                add_log(f"  → Found {len(trade_dup_findings)} trade duplicates", "📊")
                update_progress(21)

                # Date anomalies
                add_log("Running Rule 4/8: Date anomaly detection...", "📌")
                date_findings = orchestrator.rule_detector.detect_date_anomalies()
                add_log(f"  → Found {len(date_findings)} date anomalies", "📊")
                update_progress(24)

                # Exposure anomalies
                add_log("Running Rule 5/8: Exposure anomaly detection...", "📌")
                exposure_findings = orchestrator.rule_detector.detect_exposure_anomalies()
                add_log(f"  → Found {len(exposure_findings)} exposure anomalies", "📊")
                update_progress(27)

                # Expired active trades
                add_log("Running Rule 6/8: Expired active trade detection...", "📌")
                expired_findings = orchestrator.rule_detector.detect_expired_active_trades()
                add_log(f"  → Found {len(expired_findings)} expired active trades", "📊")
                update_progress(30)

                # Negative values
                add_log("Running Rule 7/8: Negative value detection...", "📌")
                negative_findings = orchestrator.rule_detector.detect_negative_values()
                add_log(f"  → Found {len(negative_findings)} negative value issues", "📊")
                update_progress(33)

                # PV discrepancies
                add_log("Running Rule 8/8: PV discrepancy detection...", "📌")
                pv_findings = orchestrator.rule_detector.detect_pv_discrepancies()
                add_log(f"  → Found {len(pv_findings)} PV discrepancies", "📊")
                update_progress(36)

                rule_findings = (split_findings + dra_findings + trade_dup_findings +
                               date_findings + exposure_findings + expired_findings +
                               negative_findings + pv_findings)

                add_log(f"✓ Rule-based detection complete: {len(rule_findings)} total findings", "✅")
                status_text.markdown(f"**✓ Rule-based detection complete - {len(rule_findings)} findings**")
                update_progress(40)
            else:
                agent_display.markdown("### Agent: Rule-Based Detection Agent (Disabled)")
                rule_findings = []
                add_log("", "")
                add_log("Rule-based detection disabled (skipped)", "⊘")
                status_text.markdown("**Rule-based detection disabled**")
                update_progress(40)

            # Step 3: ML detection
            add_log("", "")
            step_display.markdown("### 📍 Step 3/6")
            if use_ml:
                agent_display.markdown("### Agent: ML Detection Agent")
                status_text.markdown("**Running ML-based detection (Isolation Forest)...**")
                add_log("**[ML Detection Agent]** Starting ML-based detection (Isolation Forest)...", "🤖")
                update_progress(42)

                add_log("Loading trade data for ML analysis...", "📥")
                update_progress(45)

                add_log("Detecting trade anomalies with Isolation Forest...", "🧮")
                trade_ml = orchestrator.ml_detector.detect_trade_anomalies()
                add_log(f"  → Found {len(trade_ml)} trade anomalies", "📊")
                update_progress(50)

                add_log("Loading collateral movement data for ML analysis...", "📥")
                update_progress(52)

                add_log("Detecting collateral anomalies with Isolation Forest...", "🧮")
                collateral_ml = orchestrator.ml_detector.detect_collateral_anomalies()
                add_log(f"  → Found {len(collateral_ml)} collateral movement anomalies", "📊")
                update_progress(55)

                ml_findings = trade_ml + collateral_ml
                add_log(f"✓ ML detection complete: {len(ml_findings)} total findings", "✅")
                status_text.markdown(f"**✓ ML detection complete - {len(ml_findings)} findings**")
                update_progress(60)
            else:
                agent_display.markdown("### Agent: ML Detection Agent (Disabled)")
                ml_findings = []
                add_log("ML detection disabled (skipped)", "⊘")
                status_text.markdown("**ML detection disabled**")
                update_progress(60)

            # Step 4: Group findings
            add_log("", "")
            step_display.markdown("### 📍 Step 4/6")
            agent_display.markdown("### Agent: Risk Scoring Agent")
            status_text.markdown("**Grouping findings and calculating risk scores...**")
            add_log("**[Risk Scoring Agent]** Grouping findings by entity/client...", "📊")
            update_progress(62)

            all_findings = rule_findings + ml_findings
            grouped_findings = orchestrator._group_findings(all_findings)
            add_log(f"✓ Grouped into {len(grouped_findings)} unique entities", "✅")
            update_progress(70)

            # Create alerts with risk scoring
            add_log("Calculating risk scores for each entity...", "🎯")
            alerts = []
            entity_count = len(grouped_findings)
            for idx, (entity_id, findings) in enumerate(grouped_findings.items()):
                alert = orchestrator._create_alert(entity_id, findings)
                alerts.append(alert)
                if idx < 5:  # Show first 5
                    add_log(f"  → Entity {entity_id}: Risk score {alert.risk_score:.1f}/100 ({alert.risk_level})", "📈")
                update_progress(70 + int((idx + 1) / entity_count * 10))

            if entity_count > 5:
                add_log(f"  → ... and {entity_count - 5} more entities", "📈")

            add_log(f"✓ Created {len(alerts)} alerts with comprehensive risk assessments", "✅")
            status_text.markdown(f"**✓ Risk scoring complete - {len(alerts)} alerts**")
            update_progress(80)

            # Step 5: LLM analysis
            add_log("", "")
            step_display.markdown("### 📍 Step 5/6")
            if use_llm and has_api_key:
                agent_display.markdown("### Agent: LLM Analysis Agent")
                status_text.markdown("**Running LLM analysis (GPT-4o-mini)...**")
                add_log("**[LLM Analysis Agent]** Preparing context for LLM analysis...", "🧠")
                update_progress(82)

                add_log("Sending request to OpenAI GPT-4o-mini...", "📡")
                add_log(f"  → Model: gpt-4o-mini", "ℹ️")
                add_log(f"  → Analyzing {len(all_findings)} findings", "ℹ️")
                update_progress(85)

                try:
                    analysis = orchestrator.llm_analyzer.analyze_anomalies(all_findings)
                    add_log("✓ LLM analysis successful", "✅")
                    if analysis.get('summary'):
                        add_log(f"  → Summary: {analysis['summary'][:100]}...", "💡")
                    update_progress(90)
                except Exception as llm_error:
                    add_log(f"⚠ LLM analysis failed: {str(llm_error)}", "⚠️")
                    add_log("Continuing without LLM insights...", "⚠️")
                    update_progress(90)

                status_text.markdown("**✓ LLM analysis complete**")
            else:
                agent_display.markdown("### Agent: LLM Analysis Agent (Disabled)")
                add_log("LLM analysis disabled (skipped)", "⊘")
                status_text.markdown("**LLM analysis disabled**")
                update_progress(90)

            # Step 6: Finalize
            add_log("", "")
            step_display.markdown("### 📍 Step 6/6")
            agent_display.markdown("### Agent: Report Generation Agent")
            status_text.markdown("**Finalizing detection report...**")
            add_log("**[Report Generation Agent]** Generating summary statistics...", "📊")
            update_progress(92)

            critical_high = sum(1 for a in alerts if a.risk_score >= 70)
            add_log(f"  → Total alerts: {len(alerts)}", "📋")
            add_log(f"  → Critical/High risk: {critical_high}", "📋")
            add_log(f"  → Total findings: {len(all_findings)}", "📋")
            update_progress(95)

            add_log("Preparing alert data for display...", "🎨")
            update_progress(98)

            # Complete
            update_progress(100)
            add_log("", "")
            add_log("✓ Risk analysis completed successfully!", "🎉")

            step_display.markdown("### ✅ Complete")
            agent_display.markdown("### Status: All Agents Complete")
            status_text.markdown(f"### ✅ Risk Analysis Complete!")

            st.session_state.alerts = alerts

            # Show success in main column
            with main_col:
                st.success(f"✓ Risk Analysis Complete! Found {len(alerts)} payment risk alerts ({len(all_findings)} total findings) - {critical_high} critical/high risk")

        except Exception as e:
            st.error(f"Error during risk analysis: {str(e)}")
            add_log(f"✗ Error: {str(e)}", "❌")
            st.exception(e)

    # Display results in main column
    with main_col:
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

            # Alerts table with pagination
            st.subheader(f"🚨 Alerts ({len(filtered_alerts)} shown)")
            st.caption("💡 Click the 'View' button on any row to see full alert details")

            if filtered_alerts:
                # Sort by risk score
                filtered_alerts.sort(key=lambda x: x.risk_score, reverse=True)

                # Pagination setup
                if 'page_number' not in st.session_state:
                    st.session_state.page_number = 0
                if 'items_per_page' not in st.session_state:
                    st.session_state.items_per_page = 10

                # Pagination controls at top with items per page
                col1, col2, col3, col4, col5, col6 = st.columns([0.8, 0.8, 1.5, 0.8, 0.8, 1.3])

                with col1:
                    if st.button("⏮️ First", disabled=st.session_state.page_number == 0, key="first_page"):
                        st.session_state.page_number = 0
                        # Clear any open modals
                        for key in list(st.session_state.keys()):
                            if key.startswith('show_modal_'):
                                del st.session_state[key]
                        st.rerun()

                with col2:
                    if st.button("◀️ Prev", disabled=st.session_state.page_number == 0, key="prev_page"):
                        st.session_state.page_number -= 1
                        # Clear any open modals
                        for key in list(st.session_state.keys()):
                            if key.startswith('show_modal_'):
                                del st.session_state[key]
                        st.rerun()

                with col3:
                    items_per_page = st.session_state.items_per_page
                    total_pages = (len(filtered_alerts) - 1) // items_per_page + 1
                    st.markdown(f"<div style='text-align: center; padding-top: 0.5rem;'>Page {st.session_state.page_number + 1} of {total_pages}</div>", unsafe_allow_html=True)

                with col4:
                    if st.button("Next ▶️", disabled=st.session_state.page_number >= total_pages - 1, key="next_page"):
                        st.session_state.page_number += 1
                        # Clear any open modals
                        for key in list(st.session_state.keys()):
                            if key.startswith('show_modal_'):
                                del st.session_state[key]
                        st.rerun()

                with col5:
                    if st.button("Last ⏭️", disabled=st.session_state.page_number >= total_pages - 1, key="last_page"):
                        st.session_state.page_number = total_pages - 1
                        # Clear any open modals
                        for key in list(st.session_state.keys()):
                            if key.startswith('show_modal_'):
                                del st.session_state[key]
                        st.rerun()

                with col6:
                    new_items = st.selectbox("Per page", [10, 25, 50, 100], index=[10, 25, 50, 100].index(st.session_state.items_per_page), key="items_per_page_select", label_visibility="visible")
                    if new_items != st.session_state.items_per_page:
                        st.session_state.items_per_page = new_items
                        st.session_state.page_number = 0
                        # Clear any open modals
                        for key in list(st.session_state.keys()):
                            if key.startswith('show_modal_'):
                                del st.session_state[key]
                        st.rerun()

                # Paginate with current settings
                items_per_page = st.session_state.items_per_page
                total_pages = (len(filtered_alerts) - 1) // items_per_page + 1
                start_idx = st.session_state.page_number * items_per_page
                end_idx = start_idx + items_per_page
                page_alerts = filtered_alerts[start_idx:end_idx]

                # Track which modal to show
                modal_to_show = None
                modal_alert = None
                modal_idx = None

                # Display alerts as rows with action buttons
                for idx, alert in enumerate(page_alerts):
                    alert_title = get_alert_title(alert)
                    risk_icon = get_alert_icon(alert.risk_level)

                    # Check if this alert's modal should be shown
                    if st.session_state.get(f'show_modal_{alert.alert_id}', False):
                        modal_to_show = alert.alert_id
                        modal_alert = alert
                        modal_idx = start_idx + idx

                    # Determine background color
                    if alert.risk_level.upper() == 'CRITICAL':
                        bg_color = '#ffe8e8'
                    elif alert.risk_level.upper() == 'HIGH':
                        bg_color = '#fff3e0'
                    elif alert.risk_level.upper() == 'MEDIUM':
                        bg_color = '#fffde7'
                    elif alert.risk_level.upper() == 'LOW':
                        bg_color = '#e8f5e9'
                    else:
                        bg_color = '#f5f5f5'

                    # Create container with colored background
                    with st.container():
                        st.markdown(f'<div style="background-color: {bg_color}; padding: 0.75rem; border-radius: 0.5rem; margin-bottom: 0.25rem; border-left: 5px solid {get_risk_color(alert.risk_level)};">', unsafe_allow_html=True)

                        col1, col2, col3, col4, col5, col6 = st.columns([0.5, 3, 1.5, 1, 1.2, 1])

                        with col1:
                            st.markdown(f"<div style='font-size: 2rem; text-align: center;'>{risk_icon}</div>", unsafe_allow_html=True)

                        with col2:
                            st.markdown(f"**{alert_title.replace(risk_icon, '').strip()}**")
                            st.caption(f"ID: {alert.alert_id[:8]} | {alert.timestamp.strftime('%Y-%m-%d %H:%M')}")

                        with col3:
                            st.markdown(f"<div style='text-align: center;'><small>Risk Score</small><br><strong style='font-size: 1.1rem;'>{alert.risk_score:.0f}/100</strong></div>", unsafe_allow_html=True)

                        with col4:
                            st.markdown(f"<div style='text-align: center;'><small>Issues</small><br><strong style='font-size: 1.1rem;'>{len(alert.agent_findings)}</strong></div>", unsafe_allow_html=True)

                        with col5:
                            st.markdown(f"<div style='padding-top: 0.5rem;'>{format_risk_badge(alert.risk_score, alert.risk_level)}</div>", unsafe_allow_html=True)

                        with col6:
                            # View button that opens modal
                            if st.button("👁️ View", key=f"view_{alert.alert_id}", use_container_width=True):
                                # Clear all other modals
                                for key in list(st.session_state.keys()):
                                    if key.startswith('show_modal_'):
                                        st.session_state[key] = False
                                st.session_state[f'show_modal_{alert.alert_id}'] = True
                                st.rerun()

                        st.markdown('</div>', unsafe_allow_html=True)

                # Show modal after loop (only one at a time)
                if modal_to_show and modal_alert:
                    @st.dialog(get_alert_title(modal_alert), width="large")
                    def show_alert_details():
                        render_alert_card(modal_alert, modal_idx)
                        if st.button("Close", use_container_width=True):
                            st.session_state[f'show_modal_{modal_to_show}'] = False
                            st.rerun()

                    show_alert_details()

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
                        file_name=f"payment_risk_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain"
                    )

        else:
            st.info("👈 Click 'Run Risk Analysis' in the sidebar to start payment risk assessment")


def generate_text_report(alerts: List[Alert]) -> str:
    """Generate text report for export"""
    report = []
    report.append("=" * 80)
    report.append("EM PAYMENT RISK MANAGEMENT SYSTEM - RISK ASSESSMENT REPORT")
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
