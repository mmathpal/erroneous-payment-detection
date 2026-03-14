#!/usr/bin/env python3
"""
Rule-Based Detection Agent

Applies deterministic rules to detect known anomaly patterns
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from typing import List, Dict, Any
from src.agents.base import FindingsObject, ErrorType, SeverityLevel
from src.database.connection import DatabaseConnection


class RuleBasedDetector:
    """Rule-based anomaly detection engine"""

    def __init__(self):
        """Initialize the rule-based detector"""
        self.db = DatabaseConnection(database="EM")
        self.agent_name = "RuleBasedDetector"

    def detect_all_anomalies(self) -> List[FindingsObject]:
        """
        Run all rule-based detections (simplified POC - 3 core rules only)

        Returns:
            List of FindingsObject for each anomaly detected
        """
        findings = []

        # Run 3 core detections for POC
        findings.extend(self.detect_split_booking_duplicates())
        findings.extend(self.detect_dra_duplicates())
        findings.extend(self.detect_pv_discrepancies())

        return findings

    def detect_split_booking_duplicates(self) -> List[FindingsObject]:
        """
        Detect split booking duplicate pattern: R + D = D

        Rule: Same collateral_balance_id with R + D legs equaling another D leg
        """
        findings = []

        query = """
            WITH balance_groups AS (
                SELECT
                    collateral_balance_id,
                    collateral_movement_id,
                    delivery_or_return,
                    nominal,
                    transaction_date
                FROM ci_collateral_movement
            ),
            r_records AS (
                SELECT * FROM balance_groups WHERE delivery_or_return = 'R'
            ),
            d_records AS (
                SELECT * FROM balance_groups WHERE delivery_or_return = 'D'
            )
            SELECT
                r.collateral_balance_id,
                r.collateral_movement_id as r_movement_id,
                r.nominal as r_nominal,
                d1.collateral_movement_id as d1_movement_id,
                d1.nominal as d1_nominal,
                d2.collateral_movement_id as d2_movement_id,
                d2.nominal as d2_nominal,
                r.transaction_date
            FROM r_records r
            JOIN d_records d1 ON r.collateral_balance_id = d1.collateral_balance_id
            JOIN d_records d2 ON r.collateral_balance_id = d2.collateral_balance_id
            WHERE d1.collateral_movement_id != d2.collateral_movement_id
              AND ABS((r.nominal + d1.nominal) - d2.nominal) < 0.01
        """

        results = self.db.execute_query(query)

        for row in results:
            finding = FindingsObject(
                agent_name=self.agent_name,
                timestamp=datetime.now(),
                client_id=str(row['collateral_balance_id']),
                value_date=str(row['transaction_date']),
                error_type=ErrorType.SPLIT_BOOKING_ERROR,
                severity=SeverityLevel.HIGH,
                confidence_score=1.0,
                description=f"Split booking duplicate detected for balance {row['collateral_balance_id']}",
                evidence={
                    "collateral_balance_id": row['collateral_balance_id'],
                    "return_movement": {
                        "id": row['r_movement_id'],
                        "amount": float(row['r_nominal'])
                    },
                    "delivery_movement_1": {
                        "id": row['d1_movement_id'],
                        "amount": float(row['d1_nominal'])
                    },
                    "duplicate_movement": {
                        "id": row['d2_movement_id'],
                        "amount": float(row['d2_nominal'])
                    },
                    "calculated_sum": float(row['r_nominal'] + row['d1_nominal']),
                    "duplicate_amount": float(row['d2_nominal'])
                },
                recommendation="Investigate duplicate booking. Check if both split (R+D) and combined (D) bookings were processed."
            )
            findings.append(finding)

        return findings

    def detect_dra_duplicates(self) -> List[FindingsObject]:
        """
        Detect duplicate DRA records

        Rule: Multiple records with same arrangement_id + generation_id + calculation_date
        """
        findings = []

        query = """
            SELECT
                arrangement_id,
                generation_id,
                calculation_date,
                COUNT(*) as duplicate_count,
                STRING_AGG(CAST(id AS VARCHAR), ', ') as duplicate_ids,
                STRING_AGG(CAST(cashflow_dra AS VARCHAR), ', ') as cashflow_values
            FROM arrangement_clearing_dra
            GROUP BY arrangement_id, generation_id, calculation_date
            HAVING COUNT(*) > 1
        """

        results = self.db.execute_query(query)

        for row in results:
            finding = FindingsObject(
                agent_name=self.agent_name,
                timestamp=datetime.now(),
                client_id=str(row['arrangement_id']),
                value_date=str(row['calculation_date']),
                error_type=ErrorType.DRA_MISMATCH,
                severity=SeverityLevel.HIGH,
                confidence_score=0.90,
                description=f"Duplicate DRA calculation for arrangement {row['arrangement_id']}",
                evidence={
                    "arrangement_id": row['arrangement_id'],
                    "generation_id": row['generation_id'],
                    "calculation_date": str(row['calculation_date']),
                    "duplicate_count": row['duplicate_count'],
                    "duplicate_ids": row['duplicate_ids'],
                    "cashflow_values": row['cashflow_values']
                },
                recommendation="Review DRA calculation process. Multiple calculations exist for the same date."
            )
            findings.append(finding)

        return findings

    def detect_trade_duplicates(self) -> List[FindingsObject]:
        """
        Detect duplicate trade references

        Rule: Multiple trades with same src_trade_ref
        """
        findings = []

        query = """
            SELECT
                src_trade_ref,
                COUNT(*) as count,
                STRING_AGG(CAST(arrangement_id AS VARCHAR), ', ') as arrangement_ids
            FROM trade
            GROUP BY src_trade_ref
            HAVING COUNT(*) > 1
        """

        results = self.db.execute_query(query)

        for row in results:
            finding = FindingsObject(
                agent_name=self.agent_name,
                timestamp=datetime.now(),
                client_id=row['src_trade_ref'],
                value_date=None,
                error_type=ErrorType.DUPLICATE_BOOKING,
                severity=SeverityLevel.HIGH,
                confidence_score=1.0,
                description=f"Duplicate trade reference: {row['src_trade_ref']}",
                evidence={
                    "src_trade_ref": row['src_trade_ref'],
                    "duplicate_count": row['count'],
                    "arrangement_ids": row['arrangement_ids']
                },
                recommendation="Verify if this is a legitimate duplicate or data entry error."
            )
            findings.append(finding)

        return findings

    def detect_date_anomalies(self) -> List[FindingsObject]:
        """
        Detect date anomalies in trades

        Rule: effective_date > maturity_date (impossible scenario)
        """
        findings = []

        query = """
            SELECT
                src_trade_ref,
                effective_date,
                maturity_date,
                DATEDIFF(day, maturity_date, effective_date) as days_diff
            FROM trade
            WHERE effective_date > maturity_date
        """

        results = self.db.execute_query(query)

        for row in results:
            finding = FindingsObject(
                agent_name=self.agent_name,
                timestamp=datetime.now(),
                client_id=row['src_trade_ref'],
                value_date=str(row['effective_date']),
                error_type=ErrorType.UNKNOWN,
                severity=SeverityLevel.CRITICAL,
                confidence_score=1.0,
                description=f"Date anomaly: Effective date after maturity date for {row['src_trade_ref']}",
                evidence={
                    "src_trade_ref": row['src_trade_ref'],
                    "effective_date": str(row['effective_date']),
                    "maturity_date": str(row['maturity_date']),
                    "days_difference": row['days_diff']
                },
                recommendation="Critical data error. Effective date cannot be after maturity date. Correct immediately."
            )
            findings.append(finding)

        return findings

    def detect_exposure_anomalies(self) -> List[FindingsObject]:
        """
        Detect exposure anomalies

        Rule: Exposure > 5x notional (suspicious)
        """
        findings = []

        query = """
            SELECT
                src_trade_ref,
                notional_1,
                exposure,
                exposure/notional_1 as ratio
            FROM trade
            WHERE notional_1 > 0 AND exposure > notional_1 * 5
        """

        results = self.db.execute_query(query)

        for row in results:
            finding = FindingsObject(
                agent_name=self.agent_name,
                timestamp=datetime.now(),
                client_id=row['src_trade_ref'],
                value_date=None,
                error_type=ErrorType.MARGIN_SWING,
                severity=SeverityLevel.HIGH,
                confidence_score=1.0,
                description=f"Exposure anomaly: Exposure {row['ratio']:.1f}x notional for {row['src_trade_ref']}",
                evidence={
                    "src_trade_ref": row['src_trade_ref'],
                    "notional": float(row['notional_1']),
                    "exposure": float(row['exposure']),
                    "ratio": float(row['ratio'])
                },
                recommendation="Review exposure calculation. Ratio exceeds 5x threshold."
            )
            findings.append(finding)

        return findings

    def detect_expired_active_trades(self) -> List[FindingsObject]:
        """
        Detect active trades past maturity

        Rule: status = 1 (active) but maturity_date < today
        """
        findings = []

        query = """
            SELECT
                src_trade_ref,
                maturity_date,
                status,
                DATEDIFF(day, maturity_date, GETDATE()) as days_overdue
            FROM trade
            WHERE status = 1 AND maturity_date < GETDATE()
        """

        results = self.db.execute_query(query)

        for row in results:
            finding = FindingsObject(
                agent_name=self.agent_name,
                timestamp=datetime.now(),
                client_id=row['src_trade_ref'],
                value_date=str(row['maturity_date']),
                error_type=ErrorType.EOD_BOUNDARY_CROSSING,
                severity=SeverityLevel.MEDIUM,
                confidence_score=1.0,
                description=f"Active trade past maturity: {row['src_trade_ref']}",
                evidence={
                    "src_trade_ref": row['src_trade_ref'],
                    "maturity_date": str(row['maturity_date']),
                    "status": row['status'],
                    "days_overdue": row['days_overdue']
                },
                recommendation="Close or roll over matured trade."
            )
            findings.append(finding)

        return findings

    def detect_negative_values(self) -> List[FindingsObject]:
        """
        Detect negative exposure values

        Rule: exposure < 0 OR exposure_in_usd < 0 (invalid)
        """
        findings = []

        query = """
            SELECT
                src_trade_ref,
                exposure,
                exposure_in_usd
            FROM trade
            WHERE exposure < 0 OR exposure_in_usd < 0
        """

        results = self.db.execute_query(query)

        for row in results:
            finding = FindingsObject(
                agent_name=self.agent_name,
                timestamp=datetime.now(),
                client_id=row['src_trade_ref'],
                value_date=None,
                error_type=ErrorType.UNKNOWN,
                severity=SeverityLevel.CRITICAL,
                confidence_score=1.0,
                description=f"Negative exposure value for {row['src_trade_ref']}",
                evidence={
                    "src_trade_ref": row['src_trade_ref'],
                    "exposure": float(row['exposure']),
                    "exposure_in_usd": float(row['exposure_in_usd'])
                },
                recommendation="Critical data error. Exposure cannot be negative. Investigate calculation."
            )
            findings.append(finding)

        return findings

    def detect_pv_discrepancies(self) -> List[FindingsObject]:
        """
        Detect PV discrepancies

        Rule: |component_use_pv - used_pv| > 10% (suspicious)
        """
        findings = []

        query = """
            SELECT
                src_trade_ref,
                component_use_pv,
                used_pv,
                ABS(component_use_pv - used_pv) / component_use_pv * 100 as pct_diff
            FROM trade
            WHERE component_use_pv > 0
              AND ABS(component_use_pv - used_pv) / component_use_pv > 0.1
        """

        results = self.db.execute_query(query)

        for row in results:
            finding = FindingsObject(
                agent_name=self.agent_name,
                timestamp=datetime.now(),
                client_id=row['src_trade_ref'],
                value_date=None,
                error_type=ErrorType.UNKNOWN,
                severity=SeverityLevel.MEDIUM,
                confidence_score=0.75,
                description=f"PV discrepancy of {row['pct_diff']:.1f}% for {row['src_trade_ref']}",
                evidence={
                    "src_trade_ref": row['src_trade_ref'],
                    "component_use_pv": float(row['component_use_pv']),
                    "used_pv": float(row['used_pv']),
                    "percentage_difference": float(row['pct_diff'])
                },
                recommendation="Review PV calculations. Significant discrepancy detected."
            )
            findings.append(finding)

        return findings


if __name__ == "__main__":
    # Test the detector
    detector = RuleBasedDetector()
    findings = detector.detect_all_anomalies()

    print(f"=== Rule-Based Detection Results ===\n")
    print(f"Total anomalies found: {len(findings)}\n")

    for finding in findings:
        print(f"[{finding.severity.value.upper()}] {finding.error_type.value}")
        print(f"  {finding.description}")
        print(f"  Confidence: {finding.confidence_score:.2f}")
        print()
