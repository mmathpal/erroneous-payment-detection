#!/usr/bin/env python3
"""
ML-Based Anomaly Detection Agent

Uses Isolation Forest for unsupervised anomaly detection
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from typing import List, Dict, Any
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import pandas as pd

from src.agents.base import FindingsObject, ErrorType, SeverityLevel
from src.database.connection import DatabaseConnection


class MLAnomalyDetector:
    """ML-based anomaly detection using Isolation Forest"""

    def __init__(self, contamination: float = 0.1):
        """
        Initialize ML detector

        Args:
            contamination: Expected proportion of anomalies (default 0.1 = 10%)
        """
        self.db = DatabaseConnection(database="EM")
        self.agent_name = "MLAnomalyDetector"
        self.contamination = contamination
        self.model = None
        self.scaler = StandardScaler()

    def detect_trade_anomalies(self) -> List[FindingsObject]:
        """
        Detect trade anomalies using Isolation Forest

        Returns:
            List of FindingsObject for anomalous trades
        """
        # Fetch trade data
        query = """
            SELECT
                src_trade_ref,
                generation_id,
                arrangement_id,
                exposure,
                exposure_in_usd,
                notional_1,
                notional_2,
                component_use_pv,
                used_pv,
                DATEDIFF(day, trade_date, maturity_date) as days_to_maturity,
                DATEDIFF(day, trade_date, GETDATE()) as days_since_trade,
                status
            FROM trade
        """

        results = self.db.execute_query(query)

        if not results or len(results) < 2:
            return []

        # Convert to DataFrame
        df = pd.DataFrame(results)

        # Feature engineering
        df['exposure_ratio'] = df.apply(
            lambda x: x['exposure'] / x['notional_1'] if x['notional_1'] != 0 else 0,
            axis=1
        )
        df['pv_discrepancy'] = df.apply(
            lambda x: abs(x['component_use_pv'] - x['used_pv']) / x['component_use_pv']
            if x['component_use_pv'] != 0 else 0,
            axis=1
        )
        df['notional_ratio'] = df.apply(
            lambda x: x['notional_2'] / x['notional_1'] if x['notional_1'] != 0 else 1,
            axis=1
        )

        # Select features for ML
        feature_cols = [
            'exposure',
            'exposure_in_usd',
            'notional_1',
            'days_to_maturity',
            'days_since_trade',
            'exposure_ratio',
            'pv_discrepancy',
            'notional_ratio'
        ]

        X = df[feature_cols].fillna(0)

        # Handle inf values
        X = X.replace([np.inf, -np.inf], 0)

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Train Isolation Forest
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=42,
            n_estimators=100
        )

        # Predict anomalies (-1 for anomaly, 1 for normal)
        predictions = self.model.fit_predict(X_scaled)

        # Get anomaly scores
        scores = self.model.score_samples(X_scaled)

        # Normalize scores to 0-1 (lower score = more anomalous)
        min_score = scores.min()
        max_score = scores.max()
        normalized_scores = 1 - (scores - min_score) / (max_score - min_score) if max_score > min_score else scores

        # Create findings for anomalies
        findings = []
        for idx, (pred, score) in enumerate(zip(predictions, normalized_scores)):
            if pred == -1:  # Anomaly detected
                row = results[idx]

                # Determine severity based on score
                if score > 0.8:
                    severity = SeverityLevel.CRITICAL
                elif score > 0.6:
                    severity = SeverityLevel.HIGH
                elif score > 0.4:
                    severity = SeverityLevel.MEDIUM
                else:
                    severity = SeverityLevel.LOW

                # Identify likely cause
                exposure_ratio = X.iloc[idx]['exposure_ratio']
                pv_disc = X.iloc[idx]['pv_discrepancy']

                if exposure_ratio > 5:
                    error_type = ErrorType.MARGIN_SWING
                    description = f"ML detected exposure anomaly for {row['src_trade_ref']}"
                elif pv_disc > 0.2:
                    error_type = ErrorType.UNKNOWN
                    description = f"ML detected PV discrepancy for {row['src_trade_ref']}"
                else:
                    error_type = ErrorType.UNKNOWN
                    description = f"ML detected statistical anomaly for {row['src_trade_ref']}"

                finding = FindingsObject(
                    agent_name=self.agent_name,
                    timestamp=datetime.now(),
                    client_id=row['src_trade_ref'],
                    value_date=None,
                    error_type=error_type,
                    severity=severity,
                    confidence_score=float(score),
                    description=description,
                    evidence={
                        "src_trade_ref": row['src_trade_ref'],
                        "anomaly_score": float(score),
                        "exposure": float(row['exposure']),
                        "notional": float(row['notional_1']),
                        "exposure_ratio": float(exposure_ratio),
                        "pv_discrepancy": float(pv_disc),
                        "features": {k: float(v) for k, v in X.iloc[idx].items()}
                    },
                    recommendation="ML model detected statistical anomaly. Manual review recommended."
                )
                findings.append(finding)

        return findings

    def detect_collateral_anomalies(self) -> List[FindingsObject]:
        """
        Detect collateral movement anomalies

        Returns:
            List of FindingsObject for anomalous movements
        """
        query = """
            SELECT
                collateral_movement_id,
                collateral_balance_id,
                nominal,
                delivery_or_return,
                DATEDIFF(day, transaction_date, expected_settlement_date) as settlement_days
            FROM ci_collateral_movement
        """

        results = self.db.execute_query(query)

        if not results or len(results) < 2:
            return []

        df = pd.DataFrame(results)

        # Feature engineering
        df['is_delivery'] = (df['delivery_or_return'] == 'D').astype(int)
        df['is_return'] = (df['delivery_or_return'] == 'R').astype(int)
        df['abs_nominal'] = df['nominal'].abs()

        feature_cols = ['nominal', 'settlement_days', 'is_delivery', 'is_return', 'abs_nominal']
        X = df[feature_cols].fillna(0)
        X_scaled = self.scaler.fit_transform(X)

        # Train model
        model = IsolationForest(contamination=self.contamination, random_state=42)
        predictions = model.fit_predict(X_scaled)
        scores = model.score_samples(X_scaled)

        # Normalize scores
        min_score = scores.min()
        max_score = scores.max()
        normalized_scores = 1 - (scores - min_score) / (max_score - min_score) if max_score > min_score else scores

        findings = []
        for idx, (pred, score) in enumerate(zip(predictions, normalized_scores)):
            if pred == -1:
                row = results[idx]

                if score > 0.7:
                    severity = SeverityLevel.HIGH
                else:
                    severity = SeverityLevel.MEDIUM

                finding = FindingsObject(
                    agent_name=self.agent_name,
                    timestamp=datetime.now(),
                    client_id=str(row['collateral_balance_id']),
                    value_date=None,
                    error_type=ErrorType.UNKNOWN,
                    severity=severity,
                    confidence_score=float(score),
                    description=f"ML detected anomalous collateral movement {row['collateral_movement_id']}",
                    evidence={
                        "collateral_movement_id": row['collateral_movement_id'],
                        "collateral_balance_id": row['collateral_balance_id'],
                        "nominal": float(row['nominal']),
                        "anomaly_score": float(score)
                    },
                    recommendation="Statistical anomaly detected in collateral movement pattern."
                )
                findings.append(finding)

        return findings

    def detect_all_anomalies(self) -> List[FindingsObject]:
        """
        Run all ML-based detections

        Returns:
            Combined list of all findings
        """
        findings = []
        findings.extend(self.detect_trade_anomalies())
        findings.extend(self.detect_collateral_anomalies())
        return findings


if __name__ == "__main__":
    # Test the detector
    detector = MLAnomalyDetector(contamination=0.15)
    findings = detector.detect_all_anomalies()

    print(f"=== ML-Based Detection Results ===\n")
    print(f"Total anomalies found: {len(findings)}\n")

    for finding in findings:
        print(f"[{finding.severity.value.upper()}] {finding.error_type.value}")
        print(f"  {finding.description}")
        print(f"  Confidence: {finding.confidence_score:.2f}")
        print()
