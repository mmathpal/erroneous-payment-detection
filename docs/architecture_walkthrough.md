# Architecture Walkthrough Script
## Exposure Manager — Erroneous Payment Detection
### Senior Management Presentation Guide

---

> **How to use this script:** Open `architecture.drawio` in diagrams.net (or the draw.io VS Code extension) on one screen. Use this script to talk through each numbered step. Each section tells you what to point at and what to say.

---

## Before You Start — Opening Statement

> *"What I'm going to show you is an AI system we've built that automatically watches our Exposure Manager platform and flags erroneous payments before they cause real financial harm. Today we have analysts doing this manually — checking logs, querying databases, reading emails. This system does all of that simultaneously, in seconds, and tells the analyst exactly what to look at and what to do about it."*

---

## ① DATA SOURCES
**Point at:** The six dark grey boxes at the top of the diagram

> *"The system monitors six data sources simultaneously — the same sources our analysts check today, but all at once.*

> *First, the **SQL Server database** — this is our live EM data, trades, collateral movements, DRA calculations.*

> *Second, the **application log files** — EM writes detailed logs every time something happens: EOD boundary crossings, timeouts, booking exceptions. Today these sit on a server and nobody reads them unless there's already a problem.*

> *Third, **Kafka** — this is our message queue where Margin Gen and MARK post their responses. If Margin Gen goes silent or sends a bad response, we need to know.*

> *Fourth, **MS Exchange email** — incident threads, resolution emails, anything that mentions a client ID or a booking. Institutional knowledge that currently lives only in people's inboxes.*

> *Fifth, **ChromaDB** — this is our AI memory. Every time we've had a payment incident in the past and resolved it, we've stored that knowledge here as a searchable knowledge base.*

> *And sixth, the **ML Model Store** — our pre-trained machine learning model that has learned what 'normal' trade data looks like."*

---

## ② MCP SERVERS
**Point at:** The six teal/green boxes in the second row

> *"Now — a key design decision. Each data source has a dedicated **MCP Server** in front of it.*

> *MCP stands for Model Context Protocol — think of it as a standardised plug socket. Each MCP server wraps a data source and exposes it as a set of clean, structured tools: `query_trade()`, `read_log_file()`, `consume_topic()`, `search_mailbox()`.*

> *Why does this matter? Two reasons:*
> *One — every agent speaks the same language. Whether it's querying a database or reading an email, it calls an MCP tool and gets back structured JSON.*
> *Two — we can swap out or upgrade any data source without touching the agents. If we move from SQL Server to a different database, only the MCP Server changes. The agents above it don't know or care."*

---

## ③ SPECIALIST AGENTS
**Point at:** The six boxes in the third row — highlight the blue ones first, then the orange ones

> *"Above the MCP servers sit our **specialist agents**. Each agent is an expert in one data source.*

> *The **blue ones are built and running today in our POC:**"*

> - *"The **Database Agent** applies three core rules: detecting split booking duplicates — that's where EM creates both an R and D leg that together equal a separate D booking. It also checks for duplicate DRA calculations and PV discrepancies between what the margin component should use versus what it actually used.*

> - *The **ML Agent** runs an Isolation Forest model — a machine learning algorithm that has learned what normal trade data looks like. When it sees a trade with an unusual combination of exposure, notional ratio and PV discrepancy, it flags it as an anomaly and gives a confidence score.*

> - *The **Resolution Agent** sits in this row because it is an agent — but unlike the others, it doesn't run as part of the initial detection sweep. It's invoked conditionally by the Orchestrator only when the risk score crosses 50. I'll explain exactly what it does in step 5."*

> *"The **orange dashed boxes are on our roadmap** — they're designed and ready to build:*

> - *The **Log Agent** will parse EM application logs in real time — catching EOD boundary crossings, Margin Gen timeouts, zero margin events.*
> - *The **Kafka Agent** will watch our message queues — detecting when Margin Gen goes quiet, when MARK messages arrive out of sequence, or when message lag builds up.*
> - *The **Email Agent** will search Exchange using the Microsoft Graph API — finding incident threads and resolution history that our analysts currently have to find manually."*

> *"Every agent — regardless of what it does — returns exactly the same thing: a **FindingsObject**. This is the contract between agents and the system. It contains: what was found, how confident we are, the severity, and the raw evidence."*

---

## ④ ORCHESTRATOR
**Point at:** The purple band spanning the full width

> *"All those FindingsObjects flow into the **Orchestrator** — the brain of the system.*

> *Look at the pipeline inside it — it's a five-step process:*

> *First, **Parallel Execution** — it runs all agents simultaneously using async Python. The Database Agent, ML Agent, Log Agent, Kafka Agent, and Email Agent all run at the same time, not one after another. This means a full detection sweep takes seconds, not minutes.*

> *Second, **Findings Aggregator** — it collects all the FindingsObjects into a single evidence chain for each entity — each client or trade.*

> *Third, **Risk Scorer** — this is where the weighted formula runs. We score on five dimensions: Severity of the error type — 30%. Financial impact — 30%. Confidence from the detectors — 25%. How many agents flagged the same thing — 10%. And time urgency — 5%. The result is a single number: **Risk Score 0 to 100**.*

> *Fourth, the **50 gate** — if the score is above 50, the system automatically invokes the Resolution Agent to find similar past incidents and generate a recommendation.*

> *Fifth, the **80 gate** — if the score is above 80, the alert is automatically raised. No human needs to decide whether to escalate it."*

---

## ⑤ RESOLUTION AGENT
**Point at:** The four blue boxes in row 5

> *"When the score crosses 50, the **Resolution Agent** kicks in. This is where the RAG — Retrieval Augmented Generation — component comes in.*

> *Step one: **RAG Retrieval** — it takes the findings and searches our ChromaDB knowledge base for the three most similar past incidents. It uses semantic search — not keyword matching — so 'split booking with R+D=D pattern' matches against historical incidents described differently but about the same problem.*

> *Step two: **LLM Recommendation** — it takes those similar incidents and the current findings and asks GPT-4o-mini to write a clear explanation: what was detected, what probably caused it based on past cases, and the specific steps to fix it.*

> *Step three: all of this is packaged into an **Alert Object** — alert ID, client ID, risk score, the full evidence from every agent, and the recommendation.*

> *Step four: the Alert Object is sent to the **FastAPI backend** which serves it to the dashboard."*

---

## ⑥ OUTPUT & DASHBOARD
**Point at:** The six boxes at the bottom

> *"Finally — what the analyst sees.*

> *Alerts are **colour coded by risk score**:*
> - *🔴 **Red** — score above 80 — auto-raised, immediate action required*
> - *🟡 **Amber** — score 50 to 80 — resolution recommendation shown, manual review*
> - *🟢 **Green** — score below 50 — logged for information only*

> *Each alert has an **Evidence Panel** — the analyst can expand it and see exactly what the Database Agent found, what the ML Agent scored, what the Log Agent detected — everything in one place, not spread across four different tools.*

> *And three action buttons: **Mark as Reviewed**, **Raise Case** into our incident system, or **Dismiss** with a reason.*

> *The dashboard also shows last run time and total alerts today — so the ops team can see at a glance whether the system is running and what's happening."*

---

## ⚙️ OFFLINE TRAINING (Side Panel, Bottom Left)
**Point at:** The yellow dashed box on the left

> *"One last thing — the yellow panel on the left. The ML model is not trained live. We run a separate training script periodically — `train_ml_model.py` — which reads the full database, trains the Isolation Forest model, and saves it as a file. The ML Agent at runtime just loads that file. This means the model is stable and consistent — it doesn't change between detection runs — and we can retrain it with one command whenever we get new data."*

---

## ⚡ LANGGRAPH — Production Evolution
**Point at:** The amber panel on the right side of the diagram

> *"The amber panel on the right shows the technology evolution path for the Orchestrator.*

> *In the POC, the Orchestrator is a fixed Python pipeline — it calls the Database Agent, then the ML Agent, then the Resolution Agent, in sequence. That works perfectly for three agents. But when we add Log, Kafka, and Email agents, we need something smarter.*

> *This is where **LangGraph** comes in. LangGraph is a framework for building agent systems as a graph — where each node is an agent, edges are the connections between them, and the whole thing shares a common state object.*

> *In production, the Orchestrator becomes a LangGraph StateGraph. This gives us four things the fixed pipeline can't do:*

> *First — **parallel execution**. The Database Agent, Log Agent, Kafka Agent, and Email Agent all run simultaneously as parallel graph nodes, not one after another.*

> *Second — **conditional routing**. The score gates — above 50, invoke Resolution Agent; above 80, auto-raise — become conditional edges in the graph. The graph decides the path at runtime based on the score.*

> *Third — **re-investigation loops**. If the Email Agent finds an incident thread mentioning a specific trade, the graph can loop back and re-run the Database Agent for that trade. The fixed pipeline can't do that — it has no concept of going back.*

> *Fourth — **persistent state**. All five agents share a single AgentState object. Every finding, every score, every piece of evidence accumulates in one place as the graph runs. No passing data manually between steps.*

> *The MCP servers, the agents themselves, the FindingsObject contract — none of that changes. LangGraph only replaces the Orchestrator layer. Everything we've built in the POC slots straight in."*

---

## Closing Statement

> *"So to summarise what we've built in the POC and what's coming:*

> | | Status |
> |---|---|
> | Database Agent — 3 core detection rules | ✅ Built |
> | ML Agent — Isolation Forest anomaly detection | ✅ Built |
> | Resolution Agent — RAG + LLM recommendations | ✅ Built |
> | Risk Scorer — weighted 0–100 score | ✅ Built |
> | Streamlit Dashboard — alert triage UI | ✅ Built |
> | Log Agent | 🔲 Roadmap |
> | Kafka Agent | 🔲 Roadmap |
> | Email Agent | 🔲 Roadmap |
> | LangGraph Orchestrator | 🔲 Roadmap |
> | MLflow model tracking | 🔲 Roadmap |

> *The POC demonstrates the full end-to-end architecture works. The roadmap agents — Log, Kafka, Email — are the natural next sprint. They slot straight into the existing MCP + Agent pattern we've already proven. And when we have five agents running, LangGraph gives us the parallel execution, conditional routing, and shared state we'll need at production scale."*

---

## Likely Questions & Answers

**Q: How is this different from the rules we already have?**
> The rules engine is one part of it — the three SQL rules in the Database Agent. But the ML Agent finds anomalies that don't match any known rule — novel patterns the rules wouldn't catch. And the RAG component means the system learns from every incident we've ever resolved, not just the ones someone thought to write a rule for.

**Q: What happens if the ML model flags something incorrectly?**
> Two things. First, the double filter — Isolation Forest must flag it AND the confidence score must exceed 50%, so borderline cases are dropped. Second, if only the ML flagged it and no rule agreed, the Risk Scorer marks it as "ML-only detection (statistical)" in the mitigating factors, which reduces the overall risk score. The analyst sees that caveat in the dashboard.

**Q: How often does it run?**
> In the POC, manually via the dashboard button. In production, it would run on a schedule — every 15 minutes during trading hours — or triggered by an event from Kafka.

**Q: Is our data leaving the building?**
> The LLM call goes to OpenAI GPT-4o-mini. We send findings summaries — error type, severity, confidence — not raw trade data or client names. Everything else runs on-premise: the ML model, the RAG search, the rule engine, the database queries. We can also switch to an on-premise LLM if required.

**Q: Why not use LangChain instead of LangGraph?**
> LangChain is a toolkit — it has wrappers for LLM calls, document loaders, and chains. It's useful but it doesn't give you a graph execution model. LangGraph does — it's built on top of LangChain and adds the StateGraph, parallel nodes, conditional edges, and looping that a multi-agent system needs. For the POC with three agents and a fixed pipeline, neither is needed. For production with five-plus agents making dynamic decisions, LangGraph is the right tool.

**Q: Does switching to LangGraph mean rewriting everything?**
> No. The agents themselves — Database Agent, ML Agent, Log Agent — don't change. The FindingsObject they return doesn't change. The MCP servers don't change. LangGraph only replaces the `orchestrator.py` coordination layer. It's a controlled, isolated upgrade.

**Q: How long did this take to build?**
> The POC was built iteratively sprint by sprint. The core detection pipeline — rules, ML, RAG, dashboard — is functional now. The roadmap agents are the next phase.

---

*File: `docs/architecture_walkthrough.md` | Diagram: `docs/architecture.drawio`*
