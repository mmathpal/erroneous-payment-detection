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
        background-color: var(--background-color);
        border: 1px solid var(--secondary-background-color);
        border-radius: 0.5rem;
        padding: 1rem;
        height: 500px;
        overflow-y: auto;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        line-height: 1.6;
        scroll-behavior: smooth;
    }
    .log-entry {
        margin: 0.25rem 0;
        white-space: pre-wrap;
    }
    .log-progress {
        font-weight: 600;
        margin-bottom: 0.5rem;
        padding: 0.25rem;
        border-bottom: 1px solid var(--secondary-background-color);
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
        return f"Payment Risk Detected - {alert.client_id}"

    # Get primary error type from highest confidence finding
    primary_finding = max(alert.agent_findings, key=lambda f: f.confidence_score)
    error_type = primary_finding.error_type.value

    # Map error types to user-friendly titles with descriptions
    title_map = {
        "duplicate_booking": f"Duplicate Booking Risk - {alert.client_id}",
        "split_booking": f"Split Booking Duplicate - {alert.client_id}",
        "dra_mismatch": f"DRA Mismatch Risk - {alert.client_id}",
        "zero_margin": f"Zero Margin Risk - {alert.client_id}",
        "margin_swing": f"Exposure Anomaly Risk - {alert.client_id}",
        "eod_boundary": f"EOD Boundary Crossing - {alert.client_id}",
        "timeout": f"System Timeout Risk - {alert.client_id}",
        "date_anomaly": f"Date Inconsistency Risk - {alert.client_id}",
        "exposure_limit": f"Exposure Limit Breach - {alert.client_id}",
        "pv_discrepancy": f"PV Calculation Risk - {alert.client_id}",
        "negative_value": f"Negative Value Risk - {alert.client_id}",
        "expired_trade": f"Expired Trade Risk - {alert.client_id}",
    }

    # Find matching title or use default
    for key, title in title_map.items():
        if key in error_type.lower():
            return title

    # Default for unknown or ML-detected risks
    return f"Payment Risk Detected - {alert.client_id}"


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
            st.caption(f"Alert ID: {alert.alert_id[:8]}... | {len(alert.agent_findings)} risks detected")

        with col2:
            # Calculate overall confidence by aggregating individual detector scores
            rule_findings = [f for f in alert.agent_findings if f.agent_name == "RuleBasedDetector"]
            ml_findings = [f for f in alert.agent_findings if f.agent_name == "MLAnomalyDetector"]

            # Aggregate scores: average of both detectors if both present, otherwise use whichever is available
            rule_confidence = 1.0 if rule_findings else 0.0
            ml_confidence = (sum(f.confidence_score for f in ml_findings) / len(ml_findings)) if ml_findings else 0.0

            if rule_findings and ml_findings:
                # Both detectors: weighted average (rule 70%, ML 30%)
                overall_confidence = (rule_confidence * 0.7) + (ml_confidence * 0.3)
            elif rule_findings:
                overall_confidence = rule_confidence
            elif ml_findings:
                overall_confidence = ml_confidence
            else:
                overall_confidence = alert.ensemble_score

            confidence_color = "#28a745" if overall_confidence >= 0.9 else ("#ffc107" if overall_confidence >= 0.6 else "#dc3545")
            st.markdown(f'<span style="background-color: {confidence_color}; color: white; padding: 0.2rem 0.6rem; border-radius: 0.75rem; font-weight: 600; font-size: 0.75rem;">{overall_confidence:.0%} Confidence</span>', unsafe_allow_html=True)

        # Quick summary metrics in cards (reduced font size)
        st.markdown("")
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        with metric_col1:
            # Use the same aggregated confidence calculation
            st.markdown(f'<div style="text-align: left;"><p style="font-size: 0.75rem; margin: 0; color: #666;">Overall Confidence</p><p style="font-size: 1.25rem; font-weight: 600; margin: 0.25rem 0 0 0;">{overall_confidence:.0%}</p></div>', unsafe_allow_html=True)
        with metric_col2:
            st.markdown(f'<div style="text-align: left;"><p style="font-size: 0.75rem; margin: 0; color: #666;">Severity</p><p style="font-size: 1.25rem; font-weight: 600; margin: 0.25rem 0 0 0;">{alert.confidence_level.value.title()}</p></div>', unsafe_allow_html=True)
        with metric_col3:
            st.markdown(f'<div style="text-align: left;"><p style="font-size: 0.75rem; margin: 0; color: #666;">Risks</p><p style="font-size: 1.25rem; font-weight: 600; margin: 0.25rem 0 0 0;">{len(alert.agent_findings)}</p></div>', unsafe_allow_html=True)
        with metric_col4:
            st.markdown(f'<div style="text-align: left;"><p style="font-size: 0.75rem; margin: 0; color: #666;">Risk Factors</p><p style="font-size: 1.25rem; font-weight: 600; margin: 0.25rem 0 0 0;">{len(alert.risk_factors)}</p></div>', unsafe_allow_html=True)

        # Expandable details
        with st.expander("🔍 View Full Details", expanded=False):

            # Two-column layout for better organization
            detail_col1, detail_col2 = st.columns([1, 1])

            with detail_col1:
                # Risk factors
                st.markdown('<p style="font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem;">🎯 Key Risk Factors</p>', unsafe_allow_html=True)
                if alert.risk_factors:
                    for idx, factor in enumerate(alert.risk_factors, 1):
                        st.markdown(f'<p style="font-size: 0.875rem; margin-bottom: 0.25rem;"><strong>{idx}.</strong> {factor}</p>', unsafe_allow_html=True)
                else:
                    st.info("No specific risk factors identified")

            with detail_col2:
                # Individual confidence scores
                st.markdown('<p style="font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem;">📊 Confidence Assessment</p>', unsafe_allow_html=True)

                # Detection consensus
                rule_findings_detail = [f for f in alert.agent_findings if f.agent_name == "RuleBasedDetector"]
                ml_findings_detail = [f for f in alert.agent_findings if f.agent_name == "MLAnomalyDetector"]

                if rule_findings_detail:
                    st.markdown('<p style="font-size: 0.875rem; font-weight: 600; margin-top: 0.5rem;">✅ Rule-Based Detection</p>', unsafe_allow_html=True)
                    st.markdown(f'<p style="font-size: 1.25rem; font-weight: bold; margin: 0.25rem 0;">100%</p>', unsafe_allow_html=True)
                    st.caption(f"Deterministic pattern match - {len(rule_findings_detail)} pattern(s)")

                if ml_findings_detail:
                    # Calculate average ML confidence
                    ml_avg_confidence = sum(f.confidence_score for f in ml_findings_detail) / len(ml_findings_detail)
                    st.markdown('<p style="font-size: 0.875rem; font-weight: 600; margin-top: 0.5rem;">📈 ML Detection</p>', unsafe_allow_html=True)
                    st.markdown(f'<p style="font-size: 1.25rem; font-weight: bold; margin: 0.25rem 0;">{ml_avg_confidence:.0%}</p>', unsafe_allow_html=True)
                    st.caption(f"Statistical anomaly - {len(ml_findings_detail)} detected")

                if rule_findings_detail and ml_findings_detail:
                    st.markdown('<p style="font-size: 0.8rem; color: #28a745; margin-top: 0.5rem;">🎯 Multiple detectors agree - High reliability</p>', unsafe_allow_html=True)
                elif not rule_findings_detail and not ml_findings_detail:
                    st.info("No detections")

            st.markdown("---")

            # Findings with better formatting
            st.markdown('<p style="font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem;">🚨 Risks Detected</p>', unsafe_allow_html=True)
            for idx, finding in enumerate(alert.agent_findings, 1):
                severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "minimal": "⚪"}.get(finding.severity.value.lower(), "⚫")

                with st.container():
                    st.markdown(f'<p style="font-size: 0.875rem; font-weight: 600; margin-bottom: 0.25rem;">{idx}. {severity_emoji} {finding.error_type.value.replace("_", " ").title()}</p>', unsafe_allow_html=True)
                    st.markdown(f'<p style="font-size: 0.8rem; margin-bottom: 0.25rem;">📝 {finding.description}</p>', unsafe_allow_html=True)
                    st.markdown(f'<p style="font-size: 0.75rem; color: #666; margin-bottom: 0.5rem;">🎯 Confidence: {finding.confidence_score:.0%} | 🤖 Agent: {finding.agent_name}</p>', unsafe_allow_html=True)

            # Resolution Recommendations
            st.markdown("---")
            st.markdown('<p style="font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem;">💡 Resolution Recommendations</p>', unsafe_allow_html=True)

            if hasattr(alert, 'resolution_recommendation') and alert.resolution_recommendation:
                st.info(alert.resolution_recommendation)

                # Show recommended steps from audit log if available
                resolution_audit = None
                if hasattr(alert, 'audit_log') and alert.audit_log:
                    resolution_audit = next((entry for entry in alert.audit_log if entry.get('action') == 'rag_resolution_analysis'), None)

                if resolution_audit:
                    if 'recommended_steps' in resolution_audit and resolution_audit['recommended_steps']:
                        st.markdown('<p style="font-size: 0.875rem; font-weight: 600; margin-top: 0.5rem;">📋 Recommended Action Steps:</p>', unsafe_allow_html=True)
                        for idx, step in enumerate(resolution_audit['recommended_steps'], 1):
                            st.markdown(f'<p style="font-size: 0.8rem; margin-bottom: 0.25rem;">{idx}. {step}</p>', unsafe_allow_html=True)

                    # Show similar incidents found
                    if 'similar_incidents_found' in resolution_audit and resolution_audit['similar_incidents_found'] > 0:
                        st.markdown(f'<p style="font-size: 0.75rem; color: #666; margin-top: 0.5rem;">🔍 Based on {resolution_audit["similar_incidents_found"]} similar historical incidents (confidence: {resolution_audit.get("rag_confidence", 0):.0%})</p>', unsafe_allow_html=True)
                    else:
                        st.caption("ℹ️ Recommendations based on best practices and general resolution patterns")
            else:
                st.info("No recommendations available for this alert. Run detection again with RAG enabled.")

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
        min_confidence_score = st.slider("Minimum Confidence Score", 0, 100, 50)

        severity_filter = st.multiselect(
            "Severity Levels",
            ["CRITICAL", "HIGH", "MEDIUM", "LOW", "MINIMAL"],
            default=["CRITICAL", "HIGH", "MEDIUM"]
        )

        st.subheader("Actions")
        run_detection = st.button("🔄 Run Risk Analysis", type="primary", use_container_width=True)

        st.divider()

        # Execution Log
        st.subheader("📋 Execution Log")

        # Create placeholder for live updates
        log_placeholder = st.empty()

        if 'logs' in st.session_state and st.session_state.logs:
            # Calculate progress
            total_logs = len(st.session_state.logs)

            # Count major steps (lines with **[...)
            major_steps = [log for log in st.session_state.logs if '**[' in log]
            current_step = len(major_steps)
            total_steps_count = st.session_state.get('total_steps', current_step)

            # Show last 20 logs
            recent_logs = st.session_state.logs[-20:]
            log_entries = "".join([f'<div class="log-entry">{log}</div>' for log in recent_logs])

            # Progress header with X/Y format
            if current_step > 0:
                progress_text = f'<div class="log-progress">Progress: Step {current_step}/{total_steps_count} | {total_logs} operations</div>'
            else:
                progress_text = f'<div class="log-progress">Initializing... | {total_logs} operations</div>'

            log_html = f'''
            <div class="execution-log">
                {progress_text}
                {log_entries}
            </div>
            '''
            log_placeholder.markdown(log_html, unsafe_allow_html=True)
        else:
            log_placeholder.caption("No execution logs yet. Run analysis to see logs.")

        st.divider()

        st.caption(f"Last run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize session state - FORCE CLEAR old alerts without RAG
    if 'alerts' not in st.session_state or st.session_state.alerts is None:
        st.session_state.alerts = None

    # Initialize progress tracking state
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    if 'total_steps' not in st.session_state:
        st.session_state.total_steps = 0

    # Main container (no right sidebar)
    main_col = st.container()

    # Run detection
    if run_detection:
        try:
            # Reset logs
            st.session_state.logs = []

            # Calculate total expected steps based on enabled detectors
            expected_steps = 1  # Orchestration Agent init
            if use_rules:
                expected_steps += 1  # Rule-based detection
            if use_ml:
                expected_steps += 1  # ML detection
            expected_steps += 1  # Risk scoring
            if use_llm and has_api_key:
                expected_steps += 1  # LLM analysis
            expected_steps += 1  # Report generation

            st.session_state.total_steps = expected_steps

            # Progress tracking function (updates sidebar log placeholder)
            def add_log(message, emoji="•"):
                log_entry = f"{emoji} {message}"
                st.session_state.logs.append(log_entry)

                # Update sidebar log in real-time
                with st.sidebar:
                    # Calculate progress
                    total_logs = len(st.session_state.logs)
                    major_steps = [log for log in st.session_state.logs if '**[' in log]
                    current_step = len(major_steps)
                    total_steps_count = st.session_state.total_steps

                    # Show last 20 logs
                    recent_logs = st.session_state.logs[-20:]
                    log_entries = "".join([f'<div class="log-entry">{log}</div>' for log in recent_logs])

                    # Progress header with X/Y format
                    if current_step > 0:
                        progress_text = f'<div class="log-progress">Progress: Step {current_step}/{total_steps_count} | {total_logs} operations</div>'
                    else:
                        progress_text = f'<div class="log-progress">Initializing... | {total_logs} operations</div>'

                    log_html = f'''
                    <div class="execution-log">
                        {progress_text}
                        {log_entries}
                    </div>
                    '''
                    log_placeholder.markdown(log_html, unsafe_allow_html=True)

            # Step 1: Initialize
            add_log("**[Orchestration Agent]** Initializing payment risk analysis system...", "🔧")

            add_log("Loading configuration from .env", "⚙️")
            add_log(f"Database: SQL Server ({os.getenv('SQL_SERVER_HOST', 'localhost')})", "💾")

            orchestrator = AnomalyDetectionOrchestrator(
                use_ml=use_ml,
                use_llm=use_llm and has_api_key,
                use_rag=True,  # Enable RAG-based resolution recommendations
                openai_api_key=api_key if has_api_key else None
            )
            if use_rules:
                add_log("✓ Rule-based engine initialized (8 rules)", "✅")
            if use_ml:
                add_log("✓ ML engine initialized (Isolation Forest)", "✅")
            if use_llm and has_api_key:
                add_log("✓ LLM engine initialized (GPT-4o-mini)", "✅")
            add_log("✓ RAG Resolution engine initialized (6 historical incidents)", "💡")

            # Step 2: Rule-based detection
            if use_rules:
                add_log("", "")
                add_log("**[Rule-Based Detection Agent]** Starting rule-based detection (8 rules)...", "🔍")

                # Split booking duplicates
                add_log("Running Rule 1/8: Split booking duplicate detection...", "📌")
                split_findings = orchestrator.rule_detector.detect_split_booking_duplicates()
                add_log(f"  → Found {len(split_findings)} split booking duplicates", "📊")

                # DRA duplicates
                add_log("Running Rule 2/8: DRA duplicate detection...", "📌")
                dra_findings = orchestrator.rule_detector.detect_dra_duplicates()
                add_log(f"  → Found {len(dra_findings)} DRA duplicates", "📊")

                # Trade duplicates
                add_log("Running Rule 3/8: Trade duplicate detection...", "📌")
                trade_dup_findings = orchestrator.rule_detector.detect_trade_duplicates()
                add_log(f"  → Found {len(trade_dup_findings)} trade duplicates", "📊")

                # Date anomalies
                add_log("Running Rule 4/8: Date anomaly detection...", "📌")
                date_findings = orchestrator.rule_detector.detect_date_anomalies()
                add_log(f"  → Found {len(date_findings)} date anomalies", "📊")

                # Exposure anomalies
                add_log("Running Rule 5/8: Exposure anomaly detection...", "📌")
                exposure_findings = orchestrator.rule_detector.detect_exposure_anomalies()
                add_log(f"  → Found {len(exposure_findings)} exposure anomalies", "📊")

                # Expired active trades
                add_log("Running Rule 6/8: Expired active trade detection...", "📌")
                expired_findings = orchestrator.rule_detector.detect_expired_active_trades()
                add_log(f"  → Found {len(expired_findings)} expired active trades", "📊")

                # Negative values
                add_log("Running Rule 7/8: Negative value detection...", "📌")
                negative_findings = orchestrator.rule_detector.detect_negative_values()
                add_log(f"  → Found {len(negative_findings)} negative value issues", "📊")

                # PV discrepancies
                add_log("Running Rule 8/8: PV discrepancy detection...", "📌")
                pv_findings = orchestrator.rule_detector.detect_pv_discrepancies()
                add_log(f"  → Found {len(pv_findings)} PV discrepancies", "📊")

                rule_findings = (split_findings + dra_findings + trade_dup_findings +
                               date_findings + exposure_findings + expired_findings +
                               negative_findings + pv_findings)

                add_log(f"✓ Rule-based detection complete: {len(rule_findings)} total findings", "✅")
            else:
                rule_findings = []
                add_log("", "")
                add_log("Rule-based detection disabled (skipped)", "⊘")

            # Step 3: ML detection
            add_log("", "")
            if use_ml:
                add_log("**[ML Detection Agent]** Starting ML-based detection (Isolation Forest)...", "🤖")

                add_log("Loading trade data for ML analysis...", "📥")

                add_log("Detecting trade anomalies with Isolation Forest...", "🧮")
                trade_ml = orchestrator.ml_detector.detect_trade_anomalies()
                add_log(f"  → Found {len(trade_ml)} trade anomalies", "📊")

                add_log("Loading collateral movement data for ML analysis...", "📥")

                add_log("Detecting collateral anomalies with Isolation Forest...", "🧮")
                collateral_ml = orchestrator.ml_detector.detect_collateral_anomalies()
                add_log(f"  → Found {len(collateral_ml)} collateral movement anomalies", "📊")

                ml_findings = trade_ml + collateral_ml
                add_log(f"✓ ML detection complete: {len(ml_findings)} total findings", "✅")
            else:
                ml_findings = []
                add_log("ML detection disabled (skipped)", "⊘")

            # Step 4: Group findings
            add_log("", "")
            add_log("**[Risk Scoring Agent]** Grouping findings by entity/client...", "📊")

            all_findings = rule_findings + ml_findings
            grouped_findings = orchestrator._group_findings(all_findings)
            add_log(f"✓ Grouped into {len(grouped_findings)} unique entities", "✅")

            # Create alerts with risk scoring
            add_log("Calculating risk scores for each entity...", "🎯")
            alerts = []
            entity_count = len(grouped_findings)
            for idx, (entity_id, findings) in enumerate(grouped_findings.items()):
                alert = orchestrator._create_alert(entity_id, findings)
                alerts.append(alert)
                if idx < 5:  # Show first 5
                    add_log(f"  → Entity {entity_id}: Risk score {alert.risk_score:.1f}/100 ({alert.risk_level})", "📈")

            if entity_count > 5:
                add_log(f"  → ... and {entity_count - 5} more entities", "📈")

            add_log(f"✓ Created {len(alerts)} alerts with comprehensive risk assessments", "✅")

            # Step 5: LLM analysis
            add_log("", "")
            if use_llm and has_api_key:
                add_log("**[LLM Analysis Agent]** Preparing context for LLM analysis...", "🧠")

                add_log("Sending request to OpenAI GPT-4o-mini...", "📡")
                add_log(f"  → Model: gpt-4o-mini", "ℹ️")
                add_log(f"  → Analyzing {len(all_findings)} findings", "ℹ️")

                try:
                    analysis = orchestrator.llm_analyzer.analyze_anomalies(all_findings)
                    add_log("✓ LLM analysis successful", "✅")
                    if analysis.get('summary'):
                        add_log(f"  → Summary: {analysis['summary'][:100]}...", "💡")
                except Exception as llm_error:
                    add_log(f"⚠ LLM analysis failed: {str(llm_error)}", "⚠️")
                    add_log("Continuing without LLM insights...", "⚠️")

            else:
                add_log("LLM analysis disabled (skipped)", "⊘")

            # Step 6: Finalize
            add_log("", "")
            add_log("**[Report Generation Agent]** Generating summary statistics...", "📊")

            critical_high = sum(1 for a in alerts if a.risk_score >= 70)
            add_log(f"  → Total alerts: {len(alerts)}", "📋")
            add_log(f"  → Critical/High risk: {critical_high}", "📋")
            add_log(f"  → Total findings: {len(all_findings)}", "📋")

            add_log("Preparing alert data for display...", "🎨")

            # Complete
            add_log("", "")
            add_log("✓ Risk analysis completed successfully!", "🎉")

            st.session_state.alerts = alerts

            # Show success in main column
            with main_col:
                st.success(f"✓ Risk Analysis Complete! Found {len(alerts)} payment risk alerts ({len(all_findings)} total findings) - {critical_high} critical/high risk")

        except Exception as e:
            add_log(f"✗ Error: {str(e)}", "❌")
            with main_col:
                st.error(f"Error during risk analysis: {str(e)}")
                st.exception(e)

    # Display results in main column
    with main_col:
        if st.session_state.alerts:
            alerts = st.session_state.alerts

            # Filter alerts by aggregated confidence
            filtered_alerts = []
            for alert in alerts:
                rule_findings_filter = [f for f in alert.agent_findings if f.agent_name == "RuleBasedDetector"]
                ml_findings_filter = [f for f in alert.agent_findings if f.agent_name == "MLAnomalyDetector"]

                # Calculate aggregated confidence (same logic as display)
                rule_conf_filter = 1.0 if rule_findings_filter else 0.0
                ml_conf_filter = (sum(f.confidence_score for f in ml_findings_filter) / len(ml_findings_filter)) if ml_findings_filter else 0.0

                if rule_findings_filter and ml_findings_filter:
                    filter_confidence = (rule_conf_filter * 0.7) + (ml_conf_filter * 0.3)
                elif rule_findings_filter:
                    filter_confidence = rule_conf_filter
                elif ml_findings_filter:
                    filter_confidence = ml_conf_filter
                else:
                    filter_confidence = alert.ensemble_score

                # Apply filter
                if (filter_confidence * 100) >= min_confidence_score and alert.confidence_level.value.upper() in severity_filter:
                    filtered_alerts.append(alert)

            # Summary metrics
            st.subheader("📊 Summary Statistics")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Alerts", len(alerts))

            with col2:
                critical_high = sum(1 for a in alerts if a.risk_score >= 70)
                st.metric("Critical/High", critical_high)

            with col3:
                total_findings = sum(len(a.agent_findings) for a in alerts)
                st.metric("Total Findings", total_findings)

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

                # Pagination controls at top with items per page and export
                col1, col2, col3, col4, col5, col6, col7 = st.columns([0.7, 0.7, 1.3, 0.7, 0.7, 1.1, 1.0])

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
                    # Use columns within col6 to place label and dropdown side by side
                    subcol1, subcol2 = st.columns([0.8, 1.2])
                    with subcol1:
                        st.markdown("<div style='padding-top: 0.5rem; white-space: nowrap; font-size: 0.9rem;'>Per page</div>", unsafe_allow_html=True)
                    with subcol2:
                        new_items = st.selectbox("items", [10, 25, 50, 100], index=[10, 25, 50, 100].index(st.session_state.items_per_page), key="items_per_page_select", label_visibility="collapsed")
                        if new_items != st.session_state.items_per_page:
                            st.session_state.items_per_page = new_items
                            st.session_state.page_number = 0
                            # Clear any open modals
                            for key in list(st.session_state.keys()):
                                if key.startswith('show_modal_'):
                                    del st.session_state[key]
                            st.rerun()

                with col7:
                    # Export button
                    report = generate_text_report(alerts)
                    st.download_button(
                        label="📥 Export",
                        data=report,
                        file_name=f"payment_risk_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )

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
                            # Calculate aggregated confidence for this alert
                            rule_findings_table = [f for f in alert.agent_findings if f.agent_name == "RuleBasedDetector"]
                            ml_findings_table = [f for f in alert.agent_findings if f.agent_name == "MLAnomalyDetector"]

                            # Aggregate scores: average of both detectors if both present
                            rule_conf = 1.0 if rule_findings_table else 0.0
                            ml_conf = (sum(f.confidence_score for f in ml_findings_table) / len(ml_findings_table)) if ml_findings_table else 0.0

                            if rule_findings_table and ml_findings_table:
                                # Both detectors: weighted average (rule 70%, ML 30%)
                                table_confidence = (rule_conf * 0.7) + (ml_conf * 0.3)
                            elif rule_findings_table:
                                table_confidence = rule_conf
                            elif ml_findings_table:
                                table_confidence = ml_conf
                            else:
                                table_confidence = alert.ensemble_score

                            st.markdown(f"<div style='text-align: center;'><small>Confidence</small><br><strong style='font-size: 1.1rem;'>{table_confidence:.0%}</strong></div>", unsafe_allow_html=True)

                        with col4:
                            st.markdown(f"<div style='text-align: center;'><small>Issues</small><br><strong style='font-size: 1.1rem;'>{len(alert.agent_findings)}</strong></div>", unsafe_allow_html=True)

                        with col5:
                            # Show severity badge instead
                            severity_color = get_risk_color(alert.risk_level)
                            st.markdown(f"<div style='padding-top: 0.5rem;'><span style='background-color: {severity_color}; color: white; padding: 0.25rem 0.75rem; border-radius: 1rem; font-weight: bold;'>{alert.risk_level.upper()}</span></div>", unsafe_allow_html=True)

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
        # Calculate confidence
        rule_findings = [f for f in alert.agent_findings if f.agent_name == "RuleBasedDetector"]
        confidence = 100 if rule_findings else int(alert.ensemble_score * 100)

        report.append(f"\nAlert #{idx + 1}")
        report.append(f"  Entity: {alert.client_id}")
        report.append(f"  Overall Confidence: {confidence}% ({alert.risk_level.upper()})")
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
