# Architecture Diagrams for Presentation

These Mermaid diagrams can be rendered using:
- GitHub/GitLab (native support)
- https://mermaid.live (online editor - copy/paste and export as PNG/SVG)
- VS Code with Mermaid extension
- PowerPoint with Mermaid plugin

---

## Diagram 1: System Architecture Overview

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[Streamlit Dashboard<br/>User Interface]
    end

    subgraph "Application Layer"
        ORCH[Orchestrator Agent<br/>Coordination & Workflow]

        subgraph "Detection Agents"
            RULE[Rule Engine<br/>8 Deterministic Rules]
            ML[ML Engine<br/>Supervised Learning]
            LLM[LLM Analyzer<br/>GPT-4o-mini]
        end

        RISK[Risk Scoring Agent<br/>Ensemble Scoring]
        RES[Resolution Agent<br/>RAG-Based Recommendations]
        FB[Feedback Loop<br/>Continuous Learning]
    end

    subgraph "Data Layer"
        DB[(SQL Server<br/>EM Database)]
        VDB[(ChromaDB<br/>Vector Store)]
        MODELS[Trained Models<br/>.pkl Files]
        TRAIN[(Training Data<br/>Labeled Incidents)]
    end

    UI -->|User Actions| ORCH
    ORCH -->|Delegate| RULE
    ORCH -->|Delegate| ML
    ORCH -->|Delegate| LLM
    RULE -->|Findings| RISK
    ML -->|Findings| RISK
    LLM -->|Findings| RISK
    RISK -->|Alerts| RES
    RES -->|Recommendations| UI
    UI -->|Feedback| FB
    FB -->|Labels| TRAIN

    RULE -.->|Query| DB
    ML -.->|Query| DB
    ML -.->|Load Model| MODELS
    LLM -.->|Query| DB
    RES -.->|Similarity Search| VDB

    style UI fill:#e1f5ff
    style ORCH fill:#fff4e1
    style RISK fill:#ffe1e1
    style FB fill:#e1ffe1
```

---

## Diagram 2: Multi-Agent Detection Flow

```mermaid
sequenceDiagram
    participant User
    participant Dashboard
    participant Orchestrator
    participant RuleEngine
    participant MLEngine
    participant LLMAnalyzer
    participant RiskScorer
    participant ResolutionAgent

    User->>Dashboard: Click "Run Analysis"
    Dashboard->>Orchestrator: Trigger Detection

    par Rule-Based Detection
        Orchestrator->>RuleEngine: Detect Anomalies
        RuleEngine->>RuleEngine: Apply 8 Rules
        RuleEngine-->>Orchestrator: Findings (100% confidence)
    and ML Detection
        Orchestrator->>MLEngine: Detect Anomalies
        MLEngine->>MLEngine: Load Model & Predict
        MLEngine-->>Orchestrator: Findings (probabilistic)
    and LLM Analysis
        Orchestrator->>LLMAnalyzer: Analyze Patterns
        LLMAnalyzer->>LLMAnalyzer: GPT-4o-mini Processing
        LLMAnalyzer-->>Orchestrator: Insights
    end

    Orchestrator->>RiskScorer: Aggregate All Findings
    RiskScorer->>RiskScorer: Ensemble Scoring<br/>(50% Rules + 30% ML + 20% LLM)
    RiskScorer-->>Orchestrator: Risk Scores & Alerts

    alt High Risk (Score > 50)
        Orchestrator->>ResolutionAgent: Get Recommendations
        ResolutionAgent->>ResolutionAgent: RAG Similarity Search
        ResolutionAgent-->>Orchestrator: Similar Incidents + Steps
    end

    Orchestrator-->>Dashboard: Display Alerts
    Dashboard-->>User: Show Results

    User->>Dashboard: Take Action (Raise/Dismiss)
    Dashboard->>Orchestrator: Record Feedback
    Orchestrator->>Orchestrator: Store Label for Retraining
```

---

## Diagram 3: Continuous Learning Cycle

```mermaid
graph LR
    subgraph "1. Detection"
        A[AI Detects<br/>Potential Errors]
    end

    subgraph "2. Human Review"
        B[Operations Team<br/>Reviews Alerts]
        B1[Raise Case<br/>Confirmed Error]
        B2[Dismiss<br/>False Positive]
        B --> B1
        B --> B2
    end

    subgraph "3. Feedback Capture"
        C[System Records<br/>True/False Label]
    end

    subgraph "4. Retraining Trigger"
        D{Threshold Met?<br/>100+ labels OR<br/>30+ days}
        D -->|Yes| E[Automated Retraining]
        D -->|No| F[Continue Collecting]
    end

    subgraph "5. Model Training"
        E --> G[Train 3 Models<br/>RF, XGB, GB]
        G --> H[Evaluate Performance<br/>F1, Precision, Recall]
        H --> I[Select Best Model]
    end

    subgraph "6. Deployment"
        I --> J[Archive Old Model]
        J --> K[Deploy New Model]
        K --> L[Better Detection]
    end

    A --> B
    B1 --> C
    B2 --> C
    C --> D
    F --> A
    L --> A

    style A fill:#e1f5ff
    style B fill:#fff4e1
    style C fill:#ffe1e1
    style E fill:#e1ffe1
    style K fill:#e1ffe1
    style L fill:#d4f1d4
```

---

## Diagram 4: Database Schema - Training Data

```mermaid
erDiagram
    ml_training_incidents ||--o{ ml_prediction_feedback : tracks
    ml_model_training_history ||--o{ ml_prediction_feedback : generates

    ml_training_incidents {
        varchar incident_id PK
        varchar entity_id
        varchar entity_type
        bit is_true_positive
        varchar error_type
        float feature_exposure
        float feature_notional_1
        float feature_pv_discrepancy
        varchar action_taken
        varchar reviewed_by
        datetime confirmed_date
    }

    ml_model_training_history {
        varchar training_id PK
        varchar model_name
        varchar model_type
        int total_samples
        float test_f1_score
        varchar model_file_path
        varchar status
        datetime deployed_date
    }

    ml_prediction_feedback {
        varchar prediction_id PK
        varchar training_id FK
        varchar entity_id
        bit predicted_anomaly
        float predicted_probability
        bit actual_anomaly
        bit was_correct
        datetime feedback_received_date
    }
```

---

## Diagram 5: Dashboard User Flow

```mermaid
stateDiagram-v2
    [*] --> Dashboard
    Dashboard --> ConfigureSettings: Set Filters
    ConfigureSettings --> RunAnalysis: Click "Run Analysis"
    RunAnalysis --> ViewingResults: Detection Complete

    ViewingResults --> ViewAlertDetails: Click Alert
    ViewAlertDetails --> ViewEvidence: Expand Evidence
    ViewAlertDetails --> ViewRecommendations: View Recommendations

    ViewAlertDetails --> MarkReviewed: Click "Mark Reviewed"
    ViewAlertDetails --> RaiseCase: Click "Raise Case"
    ViewAlertDetails --> SendAlert: Click "Send Alert"
    ViewAlertDetails --> Dismiss: Click "Dismiss"

    MarkReviewed --> FeedbackRecorded: Label: Ambiguous (default True)
    RaiseCase --> FeedbackRecorded: Label: True Positive
    SendAlert --> FeedbackRecorded: Label: True Positive
    Dismiss --> FeedbackRecorded: Label: False Positive

    FeedbackRecorded --> TrainingData: Store for Retraining
    TrainingData --> ViewingResults: Continue Reviewing

    ViewingResults --> ExportReport: Download Report
    ExportReport --> [*]

    ViewingResults --> Dashboard: New Analysis
```

---

## Diagram 6: Ensemble Scoring Algorithm

```mermaid
graph TD
    A[Alert Detected] --> B{Rule Engine<br/>Matched?}
    B -->|Yes| C[Rule Score: 100%<br/>Weight: 50%]
    B -->|No| D[Rule Score: 0%<br/>Weight: 50%]

    A --> E{ML Engine<br/>Prediction}
    E --> F[ML Probability<br/>Weight: 30%]

    A --> G{LLM Analyzer<br/>Confidence}
    G --> H[LLM Score<br/>Weight: 20%]

    C --> I[Weighted Sum]
    D --> I
    F --> I
    H --> I

    I --> J{Calculate Final Score}
    J --> K[Score = 0.5×Rule + 0.3×ML + 0.2×LLM]

    K --> L{Score ≥ 90?}
    K --> M{Score 70-89?}
    K --> N{Score 50-69?}
    K --> O{Score < 50?}

    L -->|Yes| P[CRITICAL<br/>🔴]
    M -->|Yes| Q[HIGH<br/>🟠]
    N -->|Yes| R[MEDIUM<br/>🟡]
    O -->|Yes| S[LOW<br/>🟢]

    style C fill:#ff9999
    style F fill:#99ccff
    style H fill:#99ff99
    style P fill:#ff0000,color:#fff
    style Q fill:#ff9900,color:#fff
    style R fill:#ffff00
    style S fill:#00ff00
```

---

## Diagram 7: Deployment Architecture

```mermaid
graph TB
    subgraph "User Access"
        U1[Operations Team]
        U2[Analysts]
        U3[Managers]
    end

    subgraph "Load Balancer"
        LB[NGINX / AWS ALB]
    end

    subgraph "Application Tier - Kubernetes Cluster"
        subgraph "Pod 1"
            APP1[Streamlit Dashboard]
            API1[FastAPI Backend]
        end

        subgraph "Pod 2"
            APP2[Streamlit Dashboard]
            API2[FastAPI Backend]
        end

        subgraph "Pod 3 - Background Jobs"
            SCHED[Retraining Scheduler]
            TRAIN[Training Pipeline]
        end
    end

    subgraph "Data Tier"
        subgraph "Primary DB"
            DB[(SQL Server<br/>EM Production)]
        end

        subgraph "Read Replica"
            DBrep[(SQL Server<br/>Read Replica)]
        end

        subgraph "AI/ML Storage"
            S3[S3 / Blob Storage<br/>Models & Artifacts]
            CHROMA[(ChromaDB<br/>Vector Store)]
        end
    end

    subgraph "External Services"
        OPENAI[OpenAI API<br/>GPT-4o-mini]
    end

    subgraph "Monitoring & Logging"
        PROM[Prometheus<br/>Metrics]
        GRAF[Grafana<br/>Dashboards]
        ELK[ELK Stack<br/>Logs]
    end

    U1 --> LB
    U2 --> LB
    U3 --> LB

    LB --> APP1
    LB --> APP2

    APP1 --> API1
    APP2 --> API2

    API1 --> DBrep
    API2 --> DBrep
    API1 --> CHROMA
    API2 --> CHROMA
    API1 --> S3
    API2 --> S3

    API1 -.->|LLM Analysis| OPENAI
    API2 -.->|LLM Analysis| OPENAI

    SCHED --> TRAIN
    TRAIN --> DB
    TRAIN --> S3

    APP1 --> PROM
    APP2 --> PROM
    PROM --> GRAF

    APP1 --> ELK
    APP2 --> ELK
    SCHED --> ELK

    style LB fill:#ffcccc
    style APP1 fill:#cce5ff
    style APP2 fill:#cce5ff
    style SCHED fill:#ccffcc
    style DB fill:#ffffcc
```

---

## Diagram 8: Error Detection Rules Coverage

```mermaid
pie title Error Type Distribution (Last 6 Months)
    "Split Booking Duplicates" : 35
    "DRA Mismatches" : 18
    "Trade Duplicates" : 15
    "Date Anomalies" : 12
    "Exposure Anomalies" : 8
    "Expired Active Trades" : 5
    "Negative Values" : 4
    "PV Discrepancies" : 3
```

---

## Diagram 9: Performance Comparison

```mermaid
graph LR
    subgraph "Manual Process"
        M1[Detection Time:<br/>2-4 hours]
        M2[Accuracy:<br/>60%]
        M3[False Positives:<br/>40%]
        M4[Coverage:<br/>60%]
    end

    subgraph "AI-Powered System"
        A1[Detection Time:<br/>Real-time]
        A2[Accuracy:<br/>92%]
        A3[False Positives:<br/>12%]
        A4[Coverage:<br/>95%]
    end

    M1 -.->|100x faster| A1
    M2 -.->|+53%| A2
    M3 -.->|70% reduction| A3
    M4 -.->|+58%| A4

    style M1 fill:#ffcccc
    style M2 fill:#ffcccc
    style M3 fill:#ffcccc
    style M4 fill:#ffcccc
    style A1 fill:#ccffcc
    style A2 fill:#ccffcc
    style A3 fill:#ccffcc
    style A4 fill:#ccffcc
```

---

## Diagram 10: Retraining Decision Logic

```mermaid
flowchart TD
    START([Scheduled Check<br/>Daily at 2 AM]) --> QUERY[Query Training History]
    QUERY --> LASTDATE{Get Last<br/>Training Date}

    LASTDATE --> DAYS[Calculate Days Elapsed]
    LASTDATE --> COUNT[Count New<br/>Labeled Incidents]

    DAYS --> CHECK1{Days ≥ 30?}
    COUNT --> CHECK2{New Labels ≥ 100?}

    CHECK1 -->|Yes| RETRAIN[Trigger Retraining]
    CHECK2 -->|Yes| RETRAIN

    CHECK1 -->|No| COMBINE{Either<br/>Threshold Met?}
    CHECK2 -->|No| COMBINE

    COMBINE -->|Yes| RETRAIN
    COMBINE -->|No| WAIT[Wait Until<br/>Next Check]

    RETRAIN --> LOAD[Load Training Data]
    LOAD --> SPLIT[Train/Test Split<br/>80/20]
    SPLIT --> TRAIN[Train 3 Models:<br/>RF, XGB, GB]

    TRAIN --> EVAL[Evaluate on Test Set]
    EVAL --> COMPARE[Compare F1 Scores]
    COMPARE --> BEST[Select Best Model]

    BEST --> SAVE[Save Model + Metadata]
    SAVE --> ARCHIVE[Archive Old Model]
    ARCHIVE --> DEPLOY[Deploy New Model]

    DEPLOY --> NOTIFY[Notify Ops Team]
    NOTIFY --> END([End])

    WAIT --> END

    style RETRAIN fill:#ffe1e1
    style TRAIN fill:#e1f5ff
    style DEPLOY fill:#e1ffe1
```

---

## How to Export These Diagrams for PowerPoint

### Method 1: Mermaid Live Editor (Easiest)
1. Go to https://mermaid.live
2. Copy any diagram code above
3. Paste into the editor
4. Click "Actions" → "PNG" or "SVG"
5. Download and insert into PowerPoint

### Method 2: VS Code (For Batch Export)
1. Install "Markdown Preview Mermaid Support" extension
2. Open this file in VS Code
3. Right-click each diagram → "Export to PNG"
4. Insert all PNGs into PowerPoint

### Method 3: GitHub (If Repository is Private)
1. Push this file to GitHub
2. View the rendered diagrams
3. Take screenshots or use browser extensions to export

### Method 4: Command Line (Mermaid CLI)
```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i ARCHITECTURE_DIAGRAMS.md -o diagrams/ -e png
```

---

## Diagram Color Legend

- **Blue** (#e1f5ff): Frontend/User-facing
- **Yellow** (#fff4e1): Application Logic
- **Red** (#ffe1e1): Critical Paths
- **Green** (#e1ffe1): Success States/Positive Actions
- **Gray** (#f5f5f5): Data Storage
