#!/usr/bin/env python3
"""
Launch Streamlit Dashboard for EM Anomaly Detection
"""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    dashboard_path = Path(__file__).parent / "src" / "ui" / "dashboard.py"

    print("=" * 80)
    print("Starting EM Anomaly Detection Dashboard...")
    print("=" * 80)
    print()
    print("Dashboard will open in your browser at http://localhost:8501")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 80)
    print()

    subprocess.run([
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(dashboard_path)
    ])
