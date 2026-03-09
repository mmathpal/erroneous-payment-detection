#!/usr/bin/env python3
"""
Sample Incident Documents for RAG

These are historical incidents used to train the RAG system.
In production, these would come from a case management system.
"""

from datetime import datetime
from typing import List
from src.rag.indexer import IncidentDocument


def get_sample_incidents() -> List[IncidentDocument]:
    """
    Get sample historical incidents for RAG indexing

    Returns:
        List of incident documents
    """
    incidents = [
        # Incident 1: Split booking duplicate (matching the test case)
        IncidentDocument(
            incident_id="INC-2024-001",
            title="Split Booking Duplicate - Client XYZ",
            description=(
                "Client XYZ had duplicate bookings on 2024-03-05. "
                "Two collateral movements were detected within 45 minutes with amounts "
                "232+33 (split R+D legs) and 265 (single D leg). "
                "This matched the classic split booking duplicate pattern where EM "
                "splits a booking into Return and Delivery legs based on existing balance direction."
            ),
            client_id="XYZ",
            incident_type="split_booking_duplicate",
            value_date="2024-03-05",
            resolution_steps=[
                "Verified both bookings in ci_collateral_movement table",
                "Confirmed one booking has delivery_or_return='R' and 'D', other has only 'D'",
                "Checked amounts: 232 + 33 = 265 (exact match)",
                "Reviewed EM application logs for EOD boundary crossing",
                "Found that second booking crossed EOD boundary causing duplicate",
                "Reversed the duplicate booking with reversal_movement_flag=true",
                "Updated failed_flag and added failed_reason_code_id",
                "Notified trading desk of the reversal"
            ],
            outcome="SUCCESS - Duplicate reversed, no financial impact. Root cause: EOD boundary timing issue.",
            metadata={
                "amount": 265,
                "currency": "USD",
                "booking_timestamps": ["2024-03-05 14:23:00", "2024-03-05 15:08:00"],
                "gap_minutes": 45,
                "eod_boundary_crossed": True,
                "impact": "No financial loss",
                "severity": "HIGH",
                "resolution_time_hours": 2.5
            }
        ),

        # Incident 2: DRA duplicate
        IncidentDocument(
            incident_id="INC-2024-002",
            title="DRA Duplicate - Same Arrangement/Generation/Date",
            description=(
                "Detected duplicate DRA (Daily Return Amount) entries for the same "
                "arrangement, generation, and value date. Client ABC had two DRA "
                "calculations run for arrangement 12345, generation 1, on 2024-04-12. "
                "This occurred due to a Margin Gen timeout causing retry."
            ),
            client_id="ABC",
            incident_type="dra_duplicate",
            value_date="2024-04-12",
            resolution_steps=[
                "Queried arrangement_clearing_dra table for duplicates",
                "Identified two records: same arrangement_id, arrangement_generation, value_date",
                "Checked DRA amounts: both showing 15000 USD",
                "Reviewed Kafka logs for Margin Gen responses",
                "Found timeout on first request, retry created duplicate",
                "Verified MARK (synchronized margin calc) only processed once",
                "Soft-deleted the duplicate DRA record",
                "Added idempotency check to prevent future duplicates"
            ],
            outcome="SUCCESS - Duplicate removed, no downstream impact. Added idempotency guard.",
            metadata={
                "dra_amount": 15000,
                "arrangement_id": "12345",
                "arrangement_generation": 1,
                "margin_gen_timeout": True,
                "mark_processed": False,
                "severity": "MEDIUM",
                "resolution_time_hours": 1.5
            }
        ),

        # Incident 3: Exposure exceeds notional
        IncidentDocument(
            incident_id="INC-2024-003",
            title="Exposure Anomaly - 10x Notional Exceeded",
            description=(
                "Trade DEF-789 showed exposure of 50,000,000 against notional of 5,000,000 "
                "(10x ratio). This violated risk limits and required immediate investigation. "
                "Root cause was incorrect PV (Present Value) calculation in component pricing."
            ),
            client_id="DEF",
            incident_type="exposure_anomaly",
            value_date="2024-05-20",
            resolution_steps=[
                "Alerted risk management team immediately",
                "Put trade on hold - blocked settlement",
                "Reviewed trade details in trade table",
                "Checked component_pv vs used_pv: 73% discrepancy found",
                "Investigated pricing engine logs",
                "Found bug in zero-coupon bond valuation",
                "Recalculated PV with correct formula",
                "Updated exposure to 4,800,000 (within limits)",
                "Released trade hold after approval",
                "Deployed pricing engine fix to production"
            ],
            outcome="SUCCESS - Pricing bug fixed, trade corrected. No actual loss.",
            metadata={
                "exposure": 50000000,
                "notional": 5000000,
                "ratio": 10.0,
                "corrected_exposure": 4800000,
                "trade_id": "DEF-789",
                "pv_discrepancy_pct": 73.0,
                "pricing_bug": True,
                "severity": "CRITICAL",
                "resolution_time_hours": 6.0,
                "financial_impact": 0
            }
        ),

        # Incident 4: Date anomaly - effective > maturity
        IncidentDocument(
            incident_id="INC-2024-004",
            title="Trade Date Anomaly - Effective After Maturity",
            description=(
                "Trade GHI-456 had effective_date (2024-08-15) greater than maturity_date (2024-07-01). "
                "This is logically impossible and indicated data entry error in trade capture."
            ),
            client_id="GHI",
            incident_type="date_anomaly",
            value_date="2024-06-25",
            resolution_steps=[
                "Identified trade in rule-based detector scan",
                "Contacted trading desk for trade confirmation",
                "Retrieved original trade ticket",
                "Confirmed maturity_date should be 2025-07-01 (not 2024)",
                "Updated trade.maturity_date in database",
                "Re-ran exposure and margin calculations",
                "Verified correct lifecycle events now scheduled",
                "Enhanced trade capture validation to prevent recurrence"
            ],
            outcome="SUCCESS - Data corrected, validation improved. Trade now valid.",
            metadata={
                "trade_id": "GHI-456",
                "effective_date": "2024-08-15",
                "original_maturity": "2024-07-01",
                "corrected_maturity": "2025-07-01",
                "data_entry_error": True,
                "severity": "HIGH",
                "resolution_time_hours": 3.0
            }
        ),

        # Incident 5: Negative exposure (invalid)
        IncidentDocument(
            incident_id="INC-2024-005",
            title="Invalid Negative Exposure Detected",
            description=(
                "Trade JKL-999 showed negative exposure (-25000). Exposure should always be "
                "non-negative as it represents potential loss. Investigation revealed sign error "
                "in delta calculation for option positions."
            ),
            client_id="JKL",
            incident_type="negative_value",
            value_date="2024-07-10",
            resolution_steps=[
                "Flagged by rule-based detector (negative value check)",
                "Retrieved trade details: option position (call)",
                "Checked delta calculation in risk engine",
                "Found sign inversion in delta-to-exposure conversion",
                "Corrected calculation: exposure = abs(delta * spot * notional)",
                "Recalculated exposure as 25000 (positive)",
                "Updated trade record",
                "Applied fix to all option trades in system"
            ],
            outcome="SUCCESS - Calculation corrected for all option positions.",
            metadata={
                "trade_id": "JKL-999",
                "original_exposure": -25000,
                "corrected_exposure": 25000,
                "instrument_type": "option",
                "calculation_bug": True,
                "severity": "HIGH",
                "resolution_time_hours": 4.0,
                "trades_affected": 23
            }
        ),

        # Incident 6: Expired active trade
        IncidentDocument(
            incident_id="INC-2024-006",
            title="Active Trade Past Maturity - Lifecycle Issue",
            description=(
                "Trade MNO-111 remained in 'active' status despite maturity_date of 2024-01-15 "
                "(6 months past). This indicated failure in lifecycle management system."
            ),
            client_id="MNO",
            incident_type="expired_active_trade",
            value_date="2024-07-20",
            resolution_steps=[
                "Identified in rule-based scan for expired trades",
                "Checked settlement records - trade was settled on maturity",
                "Found lifecycle event processor had failed to update status",
                "Manually updated trade status to 'matured'",
                "Removed from active exposure calculations",
                "Investigated lifecycle queue - found stuck messages",
                "Reprocessed stuck lifecycle events (47 trades)",
                "Added monitoring alert for future stuck lifecycle events"
            ],
            outcome="SUCCESS - 47 trades corrected, monitoring improved.",
            metadata={
                "trade_id": "MNO-111",
                "maturity_date": "2024-01-15",
                "discovery_date": "2024-07-20",
                "months_overdue": 6,
                "lifecycle_bug": True,
                "trades_affected": 47,
                "severity": "MEDIUM",
                "resolution_time_hours": 5.0
            }
        )
    ]

    return incidents


def load_incidents_to_rag(indexer) -> int:
    """
    Load sample incidents into RAG indexer

    Args:
        indexer: InMemoryRAGIndexer instance

    Returns:
        Number of incidents loaded
    """
    incidents = get_sample_incidents()
    indexer.add_incidents_batch(incidents)
    return len(incidents)
