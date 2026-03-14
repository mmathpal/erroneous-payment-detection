#!/usr/bin/env python3
"""
Simple On-Demand ML Model Training Script (Simplified POC)

Usage:
    poetry run python train_ml_model.py

This trains an Isolation Forest model on current data and saves it.
Note: Current POC uses unsupervised learning (no labeled data needed).
For production, use supervised learning with labeled incident data.
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import pandas as pd
import joblib
import numpy as np

from src.database.connection import DatabaseConnection


def train_trade_anomaly_model(contamination: float = 0.15):
    """
    Train Isolation Forest model on trade data

    Args:
        contamination: Expected proportion of anomalies (default 15%)
    """
    print("=" * 60)
    print("TRAINING TRADE ANOMALY DETECTION MODEL")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Connect to database
    db = DatabaseConnection(database="EM")

    # Fetch trade data
    print("1. Fetching trade data from database...")
    query = """
        SELECT
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

    results = db.execute_query(query)
    print(f"   Fetched {len(results)} trade records\n")

    if len(results) < 50:
        print("⚠ Warning: Less than 50 records. Model may not be reliable.")
        print("   Minimum recommended: 100+ records\n")

    # Convert to DataFrame
    df = pd.DataFrame(results)

    # Feature engineering
    print("2. Engineering features...")
    df['exposure_ratio'] = df['exposure'] / df['notional_1']
    df['pv_discrepancy'] = df.apply(
        lambda x: abs(x['component_use_pv'] - x['used_pv']) / x['component_use_pv']
        if x['component_use_pv'] != 0 else 0,
        axis=1
    )

    # Select features
    feature_cols = ['exposure', 'exposure_ratio', 'pv_discrepancy']
    X = df[feature_cols].fillna(0).replace([np.inf, -np.inf], 0)
    print(f"   Features: {', '.join(feature_cols)}\n")

    # Scale features
    print("3. Scaling features...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    print("   ✓ Features scaled\n")

    # Train model
    print(f"4. Training Isolation Forest (contamination={contamination})...")
    model = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=100
    )
    model.fit(X_scaled)
    print("   ✓ Model trained\n")

    # Test predictions
    print("5. Testing model...")
    predictions = model.predict(X_scaled)
    anomaly_count = (predictions == -1).sum()
    print(f"   Detected {anomaly_count} anomalies ({anomaly_count/len(predictions)*100:.1f}%)\n")

    # Save model
    print("6. Saving model...")
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)

    model_artifact = {
        'model': model,
        'scaler': scaler,
        'feature_names': feature_cols,
        'contamination': contamination,
        'n_estimators': 100,
        'trained_date': datetime.now().isoformat(),
        'training_samples': len(df),
        'detected_anomalies': int(anomaly_count)
    }

    model_path = models_dir / "trade_anomaly_model.pkl"
    joblib.dump(model_artifact, model_path)

    file_size = model_path.stat().st_size / 1024
    print(f"   ✓ Model saved to: {model_path}")
    print(f"   Size: {file_size:.1f} KB\n")

    print("=" * 60)
    print("TRAINING COMPLETE!")
    print("=" * 60)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Training samples: {len(df)}")
    print(f"Anomalies detected: {anomaly_count} ({anomaly_count/len(df)*100:.1f}%)")
    print(f"Model file: {model_path}")
    print("\nNext steps:")
    print("  - Model will be used automatically by ML detector")
    print("  - Run detection to see results")
    print("  - Re-train periodically with: poetry run python train_ml_model.py")


def main():
    """Main training function"""
    try:
        train_trade_anomaly_model(contamination=0.15)
        print("\n✅ Training successful!\n")
    except Exception as e:
        print(f"\n❌ Training failed: {str(e)}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
