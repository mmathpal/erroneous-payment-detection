# Erroneous Payment Detection System - Complete Code Explanation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Project Structure](#project-structure)
3. [Core Files Explained](#core-files-explained)
4. [Agent Files Explained](#agent-files-explained)
5. [RAG System Explained](#rag-system-explained)
6. [Database Files Explained](#database-files-explained)
7. [UI Dashboard Explained](#ui-dashboard-explained)
8. [How Everything Works Together](#how-everything-works-together)

---

## Project Overview

This is an **AI-powered payment risk detection system** for the Exposure Manager (EM) application. It detects erroneous payments in OTC (Over-The-Counter) clearing using multiple detection methods:

- **Rule-Based Detection**: Checks for known error patterns
- **ML Detection**: Uses machine learning to find anomalies
- **LLM Analysis**: Uses AI (GPT-4) for intelligent analysis
- **RAG System**: Retrieves similar past incidents and recommends solutions

---

## Project Structure

```
erroneous-payment-detection/
├── run_detection.py          # Main script to run detection from command line
├── run_dashboard.py           # Script to launch the web dashboard
├── pyproject.toml            # Project dependencies and configuration
├── .env                      # Environment variables (database credentials, API keys)
│
├── src/                      # Source code directory
│   ├── agents/              # Detection agents
│   │   ├── base.py         # Base classes used by all agents
│   │   ├── rule_engine/    # Rule-based detection
│   │   ├── ml_engine/      # Machine learning detection
│   │   ├── llm_engine/     # LLM-powered analysis
│   │   ├── risk_scoring/   # Risk scoring system
│   │   ├── orchestration/  # Orchestrator that coordinates all agents
│   │   └── resolution_agent.py  # RAG-powered resolution recommendations
│   │
│   ├── rag/                 # RAG (Retrieval-Augmented Generation) system
│   │   ├── indexer.py      # Vector search and similarity matching
│   │   └── sample_incidents.py  # Sample historical incidents
│   │
│   ├── database/            # Database connection and setup
│   │   ├── connection.py   # Database connection handler
│   │   ├── setup_database.py  # Database initialization
│   │   └── load_csv_data.py    # Load sample data
│   │
│   ├── config/              # Configuration management
│   │   └── settings.py     # Application settings
│   │
│   └── ui/                  # User interface
│       └── dashboard.py    # Streamlit web dashboard
│
└── data/                    # Data files
    ├── csv/                # Sample CSV data
    └── rag/                # RAG index files
```

---

## Core Files Explained

### 1. **run_dashboard.py** - Dashboard Launcher

```python
#!/usr/bin/env python3
```
**Shebang line**: Tells the system this is a Python 3 script. The `#!` is called a "shebang".

```python
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
```
**What it does**:
- `Path(__file__).parent` gets the directory containing this script
- `sys.path.insert(0, ...)` adds that directory to Python's search path
- This allows Python to find and import modules from the `src/` folder

```python
import subprocess
import os

if __name__ == "__main__":
    dashboard_path = project_root / "src" / "ui" / "dashboard.py"

    subprocess.run([
        "streamlit", "run", str(dashboard_path),
        "--server.port", "8501",
        "--server.address", "localhost"
    ])
```
**What it does**:
- `if __name__ == "__main__":` means "only run this if the script is executed directly"
- `subprocess.run()` launches the Streamlit web server
- `streamlit run` starts the dashboard on http://localhost:8501

---

### 2. **src/config/settings.py** - Application Configuration

```python
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
```
**Imports**:
- `Path`: For handling file paths
- `BaseSettings`: From Pydantic, validates configuration
- `load_dotenv`: Loads variables from `.env` file

```python
# Load .env file
load_dotenv()
```
Reads the `.env` file and loads all KEY=VALUE pairs as environment variables.

```python
class Settings(BaseSettings):
    """Application configuration"""

    # Project paths
    project_root: Path = Path(__file__).parent.parent.parent
    data_dir: Path = project_root / "data"
    csv_dir: Path = data_dir / "csv"
```
**What this does**:
- Creates a configuration class
- `project_root` = 3 levels up from this file (to main project folder)
- `data_dir` = project_root/data
- `csv_dir` = project_root/data/csv

```python
    # Database settings
    SQL_SERVER_HOST: str = "localhost"
    SQL_SERVER_PORT: int = 1433
    SQL_SERVER_USER: str = "sa"
    SQL_SERVER_PASSWORD: str = ""
    SQL_SERVER_DATABASE: str = "EM"
```
**Database configuration**:
- Host: Where SQL Server is running (default: your computer)
- Port: 1433 is the standard SQL Server port
- User: Username for database login
- Password: Database password (loaded from .env)
- Database: Which database to connect to

```python
    class Config:
        env_file = ".env"
        case_sensitive = False
```
Tells Pydantic to load settings from `.env` file and ignore case.

```python
settings = Settings()
```
Creates a single instance of settings that the whole application uses.

---

### 3. **src/agents/base.py** - Foundation Classes

This file defines the data structures (classes) used throughout the application.

```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
```
**Imports**:
- `dataclass`: Makes it easy to create classes that just store data
- `datetime`: For timestamps
- `Enum`: For creating fixed sets of values
- `typing`: For type hints (tells you what type of data to expect)

```python
class ErrorType(Enum):
    """Types of errors that can be detected"""
    DUPLICATE_BOOKING = "duplicate_booking"
    SPLIT_BOOKING_ERROR = "split_booking_error"
    DRA_MISMATCH = "dra_mismatch"
    # ... more error types
```
**What it does**:
- Creates a list of all possible error types
- Using Enum prevents typos (you can only use defined values)
- Example: `ErrorType.DUPLICATE_BOOKING` instead of typing "duplicate_booking"

```python
class SeverityLevel(Enum):
    """Severity levels for alerts"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"
```
Defines how serious each alert is.

```python
@dataclass
class FindingsObject:
    """Represents a single finding from a detection agent"""
    agent_name: str              # Which agent found this
    timestamp: datetime          # When it was found
    client_id: str              # Which client is affected
    value_date: Optional[str]   # Date of the transaction
    error_type: ErrorType       # What kind of error
    severity: SeverityLevel     # How serious it is
    confidence_score: float     # How confident (0.0 to 1.0)
    description: str            # Human-readable description
    evidence: Dict[str, Any]    # Proof/details
    recommendation: str         # What to do about it
```
**What it does**:
- Stores all information about one detected problem
- `@dataclass` automatically creates `__init__`, `__repr__`, etc.
- `Optional[str]` means "can be a string or None"
- `Dict[str, Any]` means "dictionary with string keys and any type of values"

```python
@dataclass
class Alert:
    """Complete alert combining multiple findings"""
    alert_id: str
    timestamp: datetime
    client_id: str
    value_date: Optional[str]
    agent_findings: List[FindingsObject]  # All findings for this client
    ensemble_score: float                 # Combined confidence
    risk_score: float                     # Risk score (0-100)
    risk_level: str                       # critical/high/medium/low
    confidence_level: SeverityLevel
    risk_factors: List[str]               # List of risk factors
    resolution_recommendation: Optional[str]  # How to fix it
    audit_log: List[Dict[str, Any]]      # History of what was done
```
An alert groups multiple findings for the same client/transaction.

---

## Agent Files Explained

### 4. **src/agents/rule_engine/detector.py** - Rule-Based Detection

```python
class RuleBasedDetector:
    """Rule-based anomaly detection engine"""

    def __init__(self):
        """Initialize the rule-based detector"""
        self.db = DatabaseConnection(database="EM")
        self.agent_name = "RuleBasedDetector"
```
**What it does**:
- `__init__` is the constructor (runs when creating a new detector)
- Creates a database connection
- Sets the agent name

```python
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
```
**SQL Query Explanation**:
- `WITH balance_groups AS (...)`: Creates a temporary table
- `r_records`: Filters for Return movements (R)
- `d_records`: Filters for Delivery movements (D)
- Main query: Finds cases where R + D1 = D2 (split booking pattern)
- `ABS(...) < 0.01`: Checks if amounts match within 0.01 (floating point tolerance)

```python
        results = self.db.execute_query(query)

        for row in results:
            finding = FindingsObject(
                agent_name=self.agent_name,
                timestamp=datetime.now(),
                client_id=str(row['collateral_balance_id']),
                value_date=str(row['transaction_date']),
                error_type=ErrorType.SPLIT_BOOKING_ERROR,
                severity=SeverityLevel.HIGH,
                confidence_score=1.0,  # 100% confident (it's a rule)
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
```
**What it does**:
- Executes the SQL query
- For each result row, creates a FindingsObject
- Confidence is 1.0 (100%) because rule-based detection is deterministic
- Stores all the evidence (IDs, amounts)
- Returns the list of findings

---

### 5. **src/agents/ml_engine/detector.py** - ML Detection

```python
from sklearn.ensemble import IsolationForest
import pandas as pd
import numpy as np
```
**Imports**:
- `IsolationForest`: Machine learning algorithm for anomaly detection
- `pandas`: For working with data tables
- `numpy`: For numerical operations

```python
class MLAnomalyDetector:
    """Machine Learning-based anomaly detector using Isolation Forest"""

    def __init__(self, contamination=0.1, random_state=42):
        """
        Initialize ML detector

        Args:
            contamination: Expected percentage of anomalies (0.1 = 10%)
            random_state: Random seed for reproducibility
        """
        self.db = DatabaseConnection(database="EM")
        self.agent_name = "MLAnomalyDetector"
        self.contamination = contamination
        self.random_state = random_state
```
**Parameters**:
- `contamination=0.1`: Expects 10% of data to be anomalies
- `random_state=42`: Using same seed gives same results (reproducible)

```python
    def detect_trade_anomalies(self) -> List[FindingsObject]:
        """Detect anomalies in trade data using Isolation Forest"""
        findings = []

        # Load trade data
        query = """
            SELECT
                src_trade_ref,
                notional_1,
                exposure,
                exposure_in_usd,
                component_use_pv,
                used_pv
            FROM trade
            WHERE notional_1 > 0
        """

        df = pd.read_sql(query, self.db.connection)
```
**What it does**:
- Loads trade data into a pandas DataFrame (like an Excel table)
- Only gets trades with positive notional values

```python
        if df.empty or len(df) < 10:
            return findings

        # Feature engineering
        df['exposure_ratio'] = df['exposure'] / df['notional_1']
        df['pv_diff'] = abs(df['component_use_pv'] - df['used_pv'])
        df['pv_diff_pct'] = df['pv_diff'] / df['component_use_pv'].abs()
```
**Feature Engineering**:
- Creates new calculated columns that help detect anomalies
- `exposure_ratio`: How much exposure vs notional
- `pv_diff`: Difference between two PV calculations
- `pv_diff_pct`: Percentage difference

```python
        # Prepare features for ML model
        features = ['notional_1', 'exposure', 'exposure_in_usd',
                   'exposure_ratio', 'pv_diff', 'pv_diff_pct']

        X = df[features].fillna(0)
```
**Prepare Data**:
- Select which columns to use
- `fillna(0)`: Replace missing values with 0

```python
        # Train Isolation Forest
        model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=100
        )

        predictions = model.fit_predict(X)
```
**Train Model**:
- `n_estimators=100`: Use 100 decision trees
- `fit_predict`: Train the model and get predictions
- Returns -1 for anomalies, 1 for normal

```python
        # Get anomaly scores
        scores = model.score_samples(X)

        # Process anomalies
        anomaly_indices = np.where(predictions == -1)[0]
```
**Get Results**:
- `score_samples`: Get anomaly scores (lower = more anomalous)
- `np.where(predictions == -1)`: Find indices where prediction is -1 (anomaly)

```python
        for idx in anomaly_indices:
            row = df.iloc[idx]
            score = scores[idx]

            # Convert score to confidence (0-1)
            # Isolation Forest scores are negative, lower is more anomalous
            confidence = min(abs(score) / 2.0, 1.0)
```
**Convert Score**:
- Isolation Forest gives negative scores
- More negative = more anomalous
- Convert to 0-1 scale for confidence

```python
            finding = FindingsObject(
                agent_name=self.agent_name,
                timestamp=datetime.now(),
                client_id=row['src_trade_ref'],
                value_date=None,
                error_type=ErrorType.MARGIN_SWING,
                severity=SeverityLevel.MEDIUM,
                confidence_score=confidence,
                description=f"Trade anomaly detected with ML confidence {confidence:.2%}",
                evidence={
                    "src_trade_ref": row['src_trade_ref'],
                    "notional": float(row['notional_1']),
                    "exposure": float(row['exposure']),
                    "exposure_ratio": float(row['exposure_ratio']),
                    "anomaly_score": float(score),
                    "ml_confidence": float(confidence)
                },
                recommendation="Review trade parameters for unusual patterns detected by ML model."
            )
            findings.append(finding)

        return findings
```
Creates a finding for each anomaly detected.

---

### 6. **src/agents/orchestration/orchestrator.py** - The Coordinator

```python
class AnomalyDetectionOrchestrator:
    """
    Orchestrates all detection agents

    This is the "brain" that coordinates:
    1. Rule-based detection
    2. ML detection
    3. LLM analysis (optional)
    4. Risk scoring
    5. RAG-based resolution recommendations
    """

    def __init__(self, use_ml=True, use_llm=False, use_rag=True, openai_api_key=None):
        """
        Initialize orchestrator

        Args:
            use_ml: Enable ML detection
            use_llm: Enable LLM analysis
            use_rag: Enable RAG recommendations
            openai_api_key: OpenAI API key for LLM
        """
        self.use_ml = use_ml
        self.use_llm = use_llm
        self.use_rag = use_rag

        # Initialize agents
        self.rule_detector = RuleBasedDetector()

        if use_ml:
            self.ml_detector = MLAnomalyDetector()

        if use_llm and openai_api_key:
            self.llm_analyzer = LLMAnalyzer(api_key=openai_api_key)

        if use_rag:
            self.resolution_agent = ResolutionAgent()

        self.risk_scorer = RiskScorer()
```
**What it does**:
- Creates instances of all detection agents
- Only creates what's needed based on flags
- This is the main entry point for running detection

```python
    def run_full_detection(self) -> List[Alert]:
        """
        Run complete detection pipeline

        Steps:
        1. Run rule-based detection
        2. Run ML detection (if enabled)
        3. Group findings by client
        4. Create alerts with risk scores
        5. Add resolution recommendations (if RAG enabled)
        6. Run LLM analysis (if enabled)

        Returns:
            List of Alert objects
        """
        all_findings = []

        # Step 1: Rule-based detection
        rule_findings = self.rule_detector.detect_all_anomalies()
        all_findings.extend(rule_findings)

        # Step 2: ML detection
        if self.use_ml:
            ml_findings = self.ml_detector.detect_trade_anomalies()
            ml_findings.extend(self.ml_detector.detect_collateral_anomalies())
            all_findings.extend(ml_findings)

        # Step 3: Group findings by client
        grouped_findings = self._group_findings(all_findings)

        # Step 4: Create alerts
        alerts = []
        for client_id, findings in grouped_findings.items():
            alert = self._create_alert(client_id, findings)
            alerts.append(alert)

        # Step 5: Add RAG recommendations
        if self.use_rag:
            for alert in alerts:
                if alert.ensemble_score >= 0.5:  # Only for high confidence
                    recommendation = self.resolution_agent.analyze_findings(
                        alert.agent_findings,
                        alert.ensemble_score
                    )
                    if recommendation:
                        alert.resolution_recommendation = recommendation.explanation
                        # Add to audit log
                        alert.audit_log.append({
                            "action": "rag_resolution_analysis",
                            "timestamp": datetime.now().isoformat(),
                            "similar_incidents_found": len(recommendation.similar_incidents),
                            "recommended_steps": recommendation.recommended_steps,
                            "rag_confidence": recommendation.confidence
                        })

        return alerts
```
**Pipeline Explanation**:
1. Runs all detectors
2. Groups findings (multiple findings for same client = 1 alert)
3. Scores each alert for risk
4. Gets recommendations from RAG system
5. Returns complete alerts

```python
    def _group_findings(self, findings: List[FindingsObject]) -> Dict[str, List[FindingsObject]]:
        """Group findings by client_id"""
        grouped = {}
        for finding in findings:
            if finding.client_id not in grouped:
                grouped[finding.client_id] = []
            grouped[finding.client_id].append(finding)
        return grouped
```
Groups all findings for the same client together.

```python
    def _create_alert(self, client_id: str, findings: List[FindingsObject]) -> Alert:
        """Create an alert from findings"""

        # Calculate ensemble score (average of all confidences)
        ensemble_score = sum(f.confidence_score for f in findings) / len(findings)

        # Calculate risk score
        risk_score = self.risk_scorer.calculate_risk_score(findings, ensemble_score)

        # Determine risk level
        risk_level = self._get_risk_level(risk_score)

        # Extract risk factors
        risk_factors = self._extract_risk_factors(findings)

        # Create alert
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            client_id=client_id,
            value_date=findings[0].value_date if findings else None,
            agent_findings=findings,
            ensemble_score=ensemble_score,
            risk_score=risk_score,
            risk_level=risk_level,
            confidence_level=self._get_confidence_level(ensemble_score),
            risk_factors=risk_factors,
            resolution_recommendation=None,
            audit_log=[]
        )

        return alert
```
**Creates Complete Alert**:
- Calculates ensemble score (average confidence)
- Gets risk score from risk scorer
- Determines severity level
- Generates unique alert ID with UUID
- Stores all findings and metadata

---

## RAG System Explained

### 7. **src/rag/indexer.py** - Vector Search Engine

```python
class InMemoryRAGIndexer:
    """
    In-memory RAG system using FAISS and sentence-transformers

    RAG = Retrieval-Augmented Generation

    How it works:
    1. Store historical incidents as vectors (embeddings)
    2. When new anomaly found, convert to vector
    3. Find similar past incidents using vector similarity
    4. Return resolutions from similar incidents
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", persist_dir: str = "data/rag"):
        """
        Initialize RAG indexer

        Args:
            model_name: Embedding model (converts text to vectors)
            persist_dir: Where to save the index
        """
        self.model_name = model_name
        self.embedding_model = None
        self.index = None
        self.documents: List[IncidentDocument] = []
        self.embeddings: Optional[np.ndarray] = None
        self.embedding_dim = 384  # all-MiniLM-L6-v2 dimension
        self.persist_dir = persist_dir
```
**What it does**:
- `embedding_model`: Converts text to numbers (vectors)
- `index`: FAISS index for fast similarity search
- `documents`: List of historical incidents
- `embeddings`: Numerical representations of incidents

```python
    def _load_model(self):
        """Lazy load sentence-transformers model"""
        if not self._model_loaded:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer(self.model_name)
            self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
            self._model_loaded = True
```
**Lazy Loading**:
- Only loads the model when first needed
- Saves memory and startup time
- `SentenceTransformer`: Converts sentences to vectors

```python
    def add_incident(self, incident: IncidentDocument) -> None:
        """Add incident to the index"""
        self._load_model()

        # Generate embedding
        text = self._create_document_text(incident)
        embedding = self.embedding_model.encode(text, convert_to_numpy=True)

        # Add to documents
        self.documents.append(incident)

        # Add to embeddings
        if self.embeddings is None:
            self.embeddings = embedding.reshape(1, -1)
        else:
            self.embeddings = np.vstack([self.embeddings, embedding])

        # Rebuild FAISS index
        self._rebuild_index()
```
**How It Works**:
1. Convert incident text to vector (embedding)
2. Store incident in documents list
3. Store embedding in embeddings array
4. Rebuild search index

```python
    def _create_document_text(self, doc: IncidentDocument) -> str:
        """Create searchable text from incident document"""
        parts = [
            f"Title: {doc.title}",
            f"Type: {doc.incident_type}",
            f"Description: {doc.description}",
            f"Resolution: {' '.join(doc.resolution_steps)}",
            f"Outcome: {doc.outcome}"
        ]
        return "\n".join(parts)
```
Combines all incident information into one text block.

```python
    def search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.0
    ) -> List[IncidentMatch]:
        """
        Semantic search for similar incidents

        Args:
            query: Description of current anomaly
            top_k: Return top 5 most similar
            min_similarity: Minimum similarity threshold

        Returns:
            List of similar incidents with similarity scores
        """
        if not self.documents:
            return []

        self._load_model()

        # Generate query embedding
        query_embedding = self.embedding_model.encode(query, convert_to_numpy=True)
        query_embedding = query_embedding.reshape(1, -1).astype('float32')

        # Search FAISS index
        distances, indices = self.index.search(query_embedding, min(top_k, len(self.documents)))

        # Convert distances to similarity scores (L2 to cosine-like)
        similarities = 1.0 / (1.0 + distances[0])

        # Build results
        results = []
        for rank, (idx, sim) in enumerate(zip(indices[0], similarities)):
            if sim >= min_similarity:
                match = IncidentMatch(
                    incident=self.documents[idx],
                    similarity_score=float(sim),
                    rank=rank + 1
                )
                results.append(match)

        return results
```
**Semantic Search**:
1. Convert query to vector
2. Find nearest vectors in index (similar incidents)
3. Return incidents ranked by similarity

---

### 8. **src/agents/resolution_agent.py** - Resolution Recommendations

```python
class ResolutionAgent:
    """
    RAG-powered resolution agent

    Responsibilities:
    1. Take findings from other agents
    2. Use RAG to retrieve similar historical incidents
    3. Extract common resolution patterns
    4. Generate recommended action steps
    """

    def __init__(self, min_similarity: float = 0.3):
        self.min_similarity = min_similarity
        self.indexer = get_rag_indexer()

        # Load sample incidents if empty
        if self.indexer.get_stats()['total_documents'] == 0:
            num_loaded = load_incidents_to_rag(self.indexer)
            self.indexer.save_to_disk()
```
**What it does**:
- Gets the RAG indexer
- Loads historical incidents if not already loaded
- Saves to disk for future use

```python
    def analyze_findings(
        self,
        findings: List[FindingsObject],
        ensemble_score: float
    ) -> Optional[ResolutionRecommendation]:
        """
        Analyze findings and generate resolution recommendation

        Only processes high-confidence findings (>= 0.5)
        """
        if ensemble_score < 0.5:
            return None

        # Group findings by error type
        findings_by_type = {}
        for finding in findings:
            error_type = finding.error_type.value
            if error_type not in findings_by_type:
                findings_by_type[error_type] = []
            findings_by_type[error_type].append(finding)
```
Groups findings by type (e.g., all "duplicate_booking" together).

```python
        # Get similar incidents for each error type
        all_similar_incidents = []
        for error_type, type_findings in findings_by_type.items():
            # Use highest confidence finding for this type
            primary_finding = max(type_findings, key=lambda f: f.confidence_score)

            # Search RAG
            query = self._build_search_query(primary_finding)
            matches = self.indexer.search(query, top_k=3, min_similarity=self.min_similarity)

            for match in matches:
                all_similar_incidents.append({
                    "incident_id": match.incident.incident_id,
                    "title": match.incident.title,
                    "description": match.incident.description,
                    "incident_type": match.incident.incident_type,
                    "similarity_score": match.similarity_score,
                    "resolution_steps": match.incident.resolution_steps,
                    "outcome": match.incident.outcome,
                    "metadata": match.incident.metadata
                })
```
**Finds Similar Incidents**:
1. For each error type, get the highest confidence finding
2. Search RAG for similar past incidents
3. Collect all similar incidents

```python
        # Generate explanation
        explanation = self._generate_explanation(findings, top_incidents, ensemble_score)

        # Extract common resolution steps
        recommended_steps = self._extract_resolution_steps(top_incidents, findings)

        # Calculate confidence
        confidence = self._calculate_confidence(top_incidents, ensemble_score)

        return ResolutionRecommendation(
            similar_incidents=top_incidents,
            explanation=explanation,
            recommended_steps=recommended_steps,
            confidence=confidence,
            generated_at=datetime.now()
        )
```
**Generates Recommendation**:
- Explains what was found
- Lists recommended steps from similar incidents
- Calculates confidence in recommendation

---

## UI Dashboard Explained

### 9. **src/ui/dashboard.py** - Streamlit Web Interface

This is a long file, so I'll explain the key sections:

```python
import streamlit as st
import pandas as pd
from datetime import datetime
```
**Streamlit**: Framework for creating web dashboards with Python

```python
st.set_page_config(
    page_title="EM Payment Risk Management",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)
```
**Configure Page**:
- Sets browser tab title
- Sets favicon
- Uses wide layout
- Shows sidebar by default

```python
st.markdown("""
<style>
    .execution-log {
        background-color: var(--background-color);
        border: 1px solid var(--secondary-background-color);
        ...
    }
</style>
""", unsafe_allow_html=True)
```
**Custom CSS**:
- Styles the execution log
- Uses Streamlit's theme variables
- `unsafe_allow_html=True` allows HTML/CSS

```python
with st.sidebar:
    st.header("⚙️ Settings")

    # Detection options
    use_rules = st.checkbox("Enable Rule-Based Detection", value=True)
    use_ml = st.checkbox("Enable ML Detection", value=True)
    use_llm = st.checkbox("Enable LLM Analysis", value=False)

    # Filters
    min_confidence_score = st.slider("Minimum Confidence Score", 0, 100, 50)
    severity_filter = st.multiselect(
        "Severity Levels",
        ["CRITICAL", "HIGH", "MEDIUM", "LOW", "MINIMAL"],
        default=["CRITICAL", "HIGH", "MEDIUM"]
    )
```
**Sidebar Controls**:
- Checkboxes to enable/disable detectors
- Slider to filter by confidence
- Multiselect for severity filtering

```python
    run_detection = st.button("🔄 Run Risk Analysis", type="primary")
```
Main button to trigger detection.

```python
if run_detection:
    try:
        # Reset logs
        st.session_state.logs = []

        # Progress tracking function
        def add_log(message, emoji="•"):
            log_entry = f"{emoji} {message}"
            st.session_state.logs.append(log_entry)

            # Update sidebar log in real-time
            with st.sidebar:
                # Calculate progress
                total_logs = len(st.session_state.logs)
                major_steps = [log for log in st.session_state.logs if '**[' in log]
                current_step = len(major_steps)

                # Update log display
                log_placeholder.markdown(log_html, unsafe_allow_html=True)
```
**Live Logging**:
- `st.session_state`: Stores data between reruns
- `add_log()`: Adds log and updates sidebar in real-time
- Shows progress (Step X/Y)

```python
        # Step 1: Initialize orchestrator
        orchestrator = AnomalyDetectionOrchestrator(
            use_ml=use_ml,
            use_llm=use_llm and has_api_key,
            use_rag=True,
            openai_api_key=api_key if has_api_key else None
        )

        # Step 2: Run detection
        alerts = orchestrator.run_full_detection()

        # Step 3: Store results
        st.session_state.alerts = alerts
```
**Run Detection**:
1. Create orchestrator with selected options
2. Run full detection pipeline
3. Store results in session state

```python
# Display results
if st.session_state.alerts:
    alerts = st.session_state.alerts

    # Filter alerts
    filtered_alerts = [a for a in alerts if meets_criteria(a)]

    # Pagination
    page_alerts = filtered_alerts[start_idx:end_idx]

    # Display each alert
    for alert in page_alerts:
        render_alert_card(alert, idx)
```
**Display Alerts**:
1. Get alerts from session state
2. Apply filters
3. Paginate (show 10 per page)
4. Render each alert as a card

```python
def render_alert_card(alert: Alert, index: int):
    """Render a single alert card"""

    # Header
    st.markdown(f"### {risk_icon} {alert_title}")

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Confidence", f"{confidence:.0%}")
    with col2:
        st.metric("Severity", alert.confidence_level)

    # Expandable details
    with st.expander("🔍 View Full Details"):
        # Risk factors
        for factor in alert.risk_factors:
            st.markdown(f"• {factor}")

        # Findings
        for finding in alert.agent_findings:
            st.markdown(f"**{finding.error_type}**")
            st.write(finding.description)

        # Resolution recommendation
        if alert.resolution_recommendation:
            st.info(alert.resolution_recommendation)
```
**Alert Card**:
- Shows summary at top
- Expandable section for details
- Shows all findings
- Shows RAG recommendations

---

## How Everything Works Together

### Complete Flow:

1. **User clicks "Run Risk Analysis"** in dashboard

2. **Orchestrator is created** with selected options

3. **Rule-Based Detection runs**:
   - Executes SQL queries
   - Finds known error patterns
   - Returns FindingsObject for each issue

4. **ML Detection runs** (if enabled):
   - Loads trade data
   - Trains Isolation Forest
   - Identifies statistical anomalies
   - Returns FindingsObject for each anomaly

5. **Findings are grouped** by client_id

6. **Alerts are created**:
   - One alert per client
   - Contains all findings for that client
   - Risk score calculated
   - Severity determined

7. **RAG Resolution runs** (for high confidence alerts):
   - Searches for similar past incidents
   - Extracts resolution steps
   - Generates recommendation
   - Adds to alert

8. **LLM Analysis runs** (if enabled):
   - Sends findings to GPT-4
   - Gets AI analysis and insights
   - Adds to audit log

9. **Results displayed** in dashboard:
   - Summary statistics
   - Paginated alert list
   - Detailed view for each alert
   - Export option

### Data Flow Diagram:

```
Database (SQL Server)
    ↓
Rule Detector → FindingsObject
    ↓
ML Detector → FindingsObject
    ↓
Orchestrator groups findings
    ↓
Risk Scorer calculates scores
    ↓
Alert created with all findings
    ↓
RAG searches similar incidents
    ↓
Resolution added to alert
    ↓
Dashboard displays results
    ↓
User takes action
```

---

## Key Concepts for Beginners

### 1. **Object-Oriented Programming (OOP)**
- **Class**: Blueprint for creating objects (like a recipe)
- **Object**: Instance of a class (like a cake made from recipe)
- **Method**: Function inside a class
- **`self`**: Refers to the current object

Example:
```python
class Car:
    def __init__(self, color):  # Constructor
        self.color = color      # Instance variable

    def drive(self):            # Method
        print(f"Driving {self.color} car")

my_car = Car("red")             # Create object
my_car.drive()                  # Call method
```

### 2. **Type Hints**
```python
def add(a: int, b: int) -> int:
    return a + b
```
- `a: int` means "a should be an integer"
- `-> int` means "returns an integer"
- Not enforced, just documentation

### 3. **List Comprehension**
```python
# Instead of:
squares = []
for x in range(10):
    squares.append(x**2)

# Write:
squares = [x**2 for x in range(10)]
```

### 4. **Context Managers (`with`)**
```python
with open("file.txt") as f:
    data = f.read()
# File automatically closed
```

### 5. **Decorators**
```python
@dataclass
class Person:
    name: str
    age: int
```
- `@dataclass` modifies the class
- Automatically adds `__init__`, `__repr__`, etc.

### 6. **Session State (Streamlit)**
```python
if 'counter' not in st.session_state:
    st.session_state.counter = 0

st.session_state.counter += 1
```
- Persists data between page reloads
- Like variables that survive reruns

---

## Common Patterns in This Codebase

### 1. **Singleton Pattern** (RAG Indexer)
```python
_global_indexer = None

def get_rag_indexer():
    global _global_indexer
    if _global_indexer is None:
        _global_indexer = InMemoryRAGIndexer()
    return _global_indexer
```
Only one instance created and reused.

### 2. **Factory Pattern** (Creating Findings)
```python
def create_finding(error_type, data):
    return FindingsObject(
        agent_name=self.agent_name,
        timestamp=datetime.now(),
        # ... more fields
    )
```
Centralized object creation.

### 3. **Pipeline Pattern** (Orchestrator)
```python
def run_full_detection():
    findings = detect_rules()
    findings += detect_ml()
    alerts = group_and_score(findings)
    alerts = add_recommendations(alerts)
    return alerts
```
Data flows through stages.

### 4. **Observer Pattern** (Logging)
```python
def add_log(message):
    st.session_state.logs.append(message)
    update_display()
```
Observers notified when state changes.

---

## Glossary

- **Alert**: Complete detection result for one client
- **Anomaly**: Unusual pattern that might indicate error
- **Confidence**: How sure the system is (0-100%)
- **Embedding**: Text converted to numbers (vector)
- **Ensemble**: Combining multiple methods
- **Finding**: Single detected issue
- **Orchestrator**: Coordinator of all agents
- **RAG**: Retrieval-Augmented Generation (search + generate)
- **Severity**: How serious (critical/high/medium/low)
- **Vector**: Array of numbers representing text

---

## Next Steps for Learning

1. **Start Small**: Run the dashboard and observe
2. **Read One File**: Pick one detector, read carefully
3. **Add Logging**: Add print statements to understand flow
4. **Modify Rules**: Try changing detection thresholds
5. **Add Features**: Create your own detection rule
6. **Debug**: Use Python debugger to step through code

## Useful Resources

- **Streamlit Docs**: https://docs.streamlit.io/
- **Pandas Tutorial**: https://pandas.pydata.org/docs/getting_started/
- **Sklearn Guide**: https://scikit-learn.org/stable/tutorial/
- **Python OOP**: https://realpython.com/python3-object-oriented-programming/
- **SQL Tutorial**: https://www.w3schools.com/sql/

---

This documentation covers the core architecture. For specific questions about any function or section, feel free to ask!
