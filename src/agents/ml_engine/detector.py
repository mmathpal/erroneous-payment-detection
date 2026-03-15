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
import joblib
import pandas as pd

from src.agents.base import FindingsObject, ErrorType, SeverityLevel
from src.database.connection import DatabaseConnection
from src.config.settings import settings


MODEL_PATH = settings.models_dir / "trade_anomaly_model.pkl"


class MLAnomalyDetector:
    """ML-based anomaly detection using a pre-trained Isolation Forest model."""

    def __init__(self):
        """
        Initialize ML detector by loading the pre-trained model from disk.

        Raises:
            FileNotFoundError: If the model file does not exist. Run train_ml_model.py first.
        """
        self.db = DatabaseConnection(database="EM")
        self.agent_name = "MLAnomalyDetector"

        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model file not found at {MODEL_PATH}. "
                "Please run: poetry run python train_ml_model.py"
            )

        artifact = joblib.load(MODEL_PATH)
        self.model = artifact["model"]
        self.scaler = artifact["scaler"]
        self.feature_names = artifact["feature_names"]
        self.contamination = artifact["contamination"]
        print(f"[MLAnomalyDetector] Loaded model trained on {artifact['training_samples']} samples ({artifact['trained_date']})")

    def detect_trade_anomalies(self) -> List[FindingsObject]:
        """
        Detect trade anomalies using Isolation Forest (simplified for POC)

        Returns:
            List of FindingsObject for anomalous trades
        """
        # Fetch trade data (simplified query)
        query = """
            SELECT TOP 100
                src_trade_ref,
                exposure,
                notional_1,
                component_use_pv,
                used_pv
            FROM trade
            WHERE exposure IS NOT NULL
              AND notional_1 IS NOT NULL
              AND notional_1 != 0
        """

        results = self.db.execute_query(query)

        if not results or len(results) < 10:
            return []

        # Convert to DataFrame
        df = pd.DataFrame(results)

        # Simple feature engineering (only 3 key features for POC)
        df['exposure_ratio'] = df['exposure'] / df['notional_1']
        df['pv_discrepancy'] = df.apply(
            lambda x: abs(x['component_use_pv'] - x['used_pv']) / x['component_use_pv']
            if x['component_use_pv'] != 0 else 0,
            axis=1
        )

        # Select only 3 core features
        feature_cols = ['exposure', 'exposure_ratio', 'pv_discrepancy']
        X = df[feature_cols].fillna(0).replace([np.inf, -np.inf], 0)

        # Scale features using the scaler fitted during training
        X_scaled = self.scaler.transform(X)

        # Predict using the pre-trained model (no retraining)
        predictions = self.model.predict(X_scaled)
        scores = self.model.score_samples(X_scaled)

        # Normalize scores
        min_score = scores.min()
        max_score = scores.max()
        normalized_scores = 1 - (scores - min_score) / (max_score - min_score) if max_score > min_score else scores

        # Create findings (limit to top anomalies)
        findings = []
        for idx, (pred, score) in enumerate(zip(predictions, normalized_scores)):
            if pred == -1 and score > 0.5:  # Only report medium+ confidence
                row = results[idx]

                # Simple severity mapping
                severity = SeverityLevel.HIGH if score > 0.7 else SeverityLevel.MEDIUM

                # Simple error type
                pv_disc = X.iloc[idx]['pv_discrepancy']
                if pv_disc > 0.2:
                    error_type = ErrorType.PV_DISCREPANCY
                    description = f"ML detected PV discrepancy for {row['src_trade_ref']}"
                else:
                    error_type = ErrorType.UNKNOWN
                    description = f"ML detected anomaly for {row['src_trade_ref']}"

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
                        "pv_discrepancy": float(X.iloc[idx]['pv_discrepancy'])
                    },
                    recommendation="Review trade details for potential anomaly."
                )
                findings.append(finding)

        return findings

    def detect_collateral_anomalies(self) -> List[FindingsObject]:
        """
        Detect collateral movement anomalies (simplified - disabled for POC)

        Returns:
            Empty list (disabled for POC simplicity)
        """
        # Disabled for POC simplicity - focus on trade anomalies only
        return []

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
    detector = MLAnomalyDetector()
    findings = detector.detect_all_anomalies()

    print(f"=== ML-Based Detection Results ===\n")
    print(f"Total anomalies found: {len(findings)}\n")

    for finding in findings:
        print(f"[{finding.severity.value.upper()}] {finding.error_type.value}")
        print(f"  {finding.description}")
        print(f"  Confidence: {finding.confidence_score:.2f}")
        print()
