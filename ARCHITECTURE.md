# System Architecture — StartupLens AI

## 1. High-Level Logical Architecture

StartupLens AI operates a modular, intelligence-gathering pipeline that converts raw topic inputs into structured, evidence-backed startup opportunity analyses.

```text
               ┌────────────────────────────────────────────────────────┐
               │              Next.js Chat-First UI                     │
               │  Sidebar • Research Composer • Report & Cards • Sources│
               └──────────────────────────┬─────────────────────────────┘
                                          │ HTTP / JSON (Port 8003)
                                          ▼
               ┌────────────────────────────────────────────────────────┐
               │                     FastAPI API                        │
               │  Input Validation • Routing • Exception Handling       │
               └──────────────────────────┬─────────────────────────────┘
                                          │
                                          ▼
                      ┌──────────────────────────────────────┐
                      │    (1) Research Coordinator          │
                      │  Workflow lifecycle & state control  │
                      └──────────────────┬───────────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 │                                               │
                 ▼                                               ▼
   ┌───────────────────────────┐                   ┌───────────────────────────┐
   │    (2) Web Research       │                   │    Gemini Model Router    │
   │  Tavily API search & docs │                   │   [FAST | BALANCED | DEEP]│
   └─────────────┬─────────────┘                   └─────────────┬─────────────┘
                 │                                               │
                 └───────────────────────┬───────────────────────┘
                                         ▼
                      ┌──────────────────────────────────────┐
                      │    (3) Market Intelligence           │
                      │  Trends, signals & market segments   │
                      └──────────────────┬───────────────────┘
                                         │
                                         ▼
                      ┌──────────────────────────────────────┐
                      │  (4) Competitive Intelligence        │
                      │  Incumbents, positioning & gaps      │
                      └──────────────────┬───────────────────┘
                                         │
                                         ▼
                      ┌──────────────────────────────────────┐
                      │     (5) Customer Insights            │
                      │  Personas, pain points & evidence    │
                      └──────────────────┬───────────────────┘
                                         │
                                         ▼
                      ┌──────────────────────────────────────┐
                      │   (6) Startup Opportunity            │
                      │  3–5 venture hypotheses & MVPs       │
                      └──────────────────┬───────────────────┘
                                         │
                                         ▼
                      ┌──────────────────────────────────────┐
                      │   (7) Opportunity Validation         │
                      │  Evidence-based criteria scoring     │
                      └──────────────────┬───────────────────┘
                                         │
                                         ▼
                      ┌──────────────────────────────────────┐
                      │     (8) Research Summary             │
                      │  Executive brief & source linking    │
                      └──────────────────┬───────────────────┘
                                         │
                                         ▼
               ┌────────────────────────────────────────────────────────┐
               │                 SQLite Persistence                     │
               │       sessions • sources • reports • opportunities     │
               └────────────────────────────────────────────────────────┘
```

> **Important Design Principle:** The 8 numbered components above represent **logical agent roles**, defining clear boundaries of responsibility. In practice, logical agent roles do not require 8 discrete Gemini API calls. For latency, cost, and rate-limit conservation, execution can combine related reasoning roles into optimized requests.

---

## 2. Implemented vs. Planned Architectural Stages

### Implemented Pipeline (Current MVP)
- **FastAPI Backend (`http://127.0.0.1:8003`):** Validates input and orchestrates the live workflow.
- **Tavily Service:** Executes web queries and extracts real URLs, publication dates, and snippets.
- **Consolidated AI Execution:**
  - *Call 1 (Research + Market Analysis):* Merges Web Research normalization, Market Intelligence, Competitive Intelligence, and Customer Insights into one Gemini JSON extraction (`gemini-3.5-flash`).
  - *Call 2 (Opportunity Synthesis):* Generates 3–5 concrete venture hypotheses with problem statements, solutions, MVPs, risks, and evidence citations.
- **Relational Persistence:** SQLite saves sessions, sources, reports, and opportunity cards with cascade deletion.
- **Next.js Frontend:** Displays conversational thread, animated agent status steps, interactive tabs, cards, and source drawer.

### Planned Extensions
- **Granular Multi-Agent Execution:** Dedicated Coordinator, explicit Opportunity Validation scoring agent, and Research Summary Agent.
- **Model Registry & Dynamic Routing:** Ability to route specific agent roles to `FAST_MODEL`, `BALANCED_MODEL`, or `DEEP_MODEL` tiers of Google Gemini.
- **Lightweight Automation Boundary:** In-process scheduling for topic monitoring, change detection, and periodic briefs without heavy task queues (no Celery, Redis, or Kubernetes).
- **Conversational Context Extension:** Follow-up chat endpoint for querying completed research sessions.

---

## 3. Module Boundaries

### Backend Modules (`backend/`)
```text
backend/
├── main.py                  # FastAPI application, lifecycle, CORS, route handlers, error handlers
├── config.py                # Pydantic BaseSettings, environment variables, key validation
├── agents/                  # AI agent orchestration
│   ├── research_agent.py    # Tavily search + Gemini research & market analysis
│   └── opportunity_agent.py # Gemini opportunity hypothesis synthesis
├── services/                # External service clients
│   ├── gemini_service.py    # Google Gemini client (google-genai SDK), JSON mode, exponential backoff
│   └── tavily_service.py    # Tavily Search API client, error handling, normalization
├── database/                # Persistence layer
│   └── db.py                # DatabaseManager, SQLite schema, connection pooling, queries
└── schemas/                 # Strongly typed Pydantic v2 schemas
    ├── api.py               # Request/Response contracts (/analyze, /health, /research)
    ├── research.py          # ResearchOutput and ResearchSource contracts
    ├── analysis.py          # MarketAnalysisOutput contract
    └── opportunity.py       # Opportunity and OpportunityOutput contracts
```

### Frontend Modules (`frontend/src/`)
```text
frontend/src/
├── app/
│   ├── layout.tsx           # Global layout, fonts, HTML metadata
│   ├── page.tsx             # Main chat-first workspace, state management, keyboard shortcuts
│   └── globals.css          # Design system tokens (dark/light themes, spacing, typography)
├── components/
│   ├── Sidebar.tsx          # Navigation, recent research list, search, session deletion
│   ├── Composer.tsx         # User input textarea, prompt suggestions, submit actions
│   ├── AgentStatus.tsx      # Step-by-step pipeline progress indicator
│   ├── ResearchReport.tsx   # Structured findings viewer (executive summary, signals, gaps)
│   ├── OpportunityCard.tsx  # Interactive opportunity cards with MVP toggle and save action
│   ├── Sources.tsx          # Verified evidence cards with external links
│   ├── HistoryView.tsx      # Full-page table of previous research sessions
│   ├── SavedIdeasView.tsx   # Locally saved opportunity hypotheses
│   ├── SettingsModal.tsx    # API configuration and model status display
│   ├── SuggestedPrompts.tsx # Quick-start topic inspiration chips
│   └── ThemeToggle.tsx      # Theme switcher (dark/light mode)
└── lib/
    └── api.ts               # Typed client calling FastAPI (port 8003) with AbortController
```

---

## 4. End-to-End Data Flow

```text
1. Client Submission
   User enters topic → POST /analyze { "topic": "AI Robotics" }

2. Ingestion & Validation
   FastAPI validates len(topic) >= 2. Returns HTTP 400 (INVALID_TOPIC) if invalid.

3. External Web Research (Tavily)
   Query: "<topic> startup trends market signals customer problems emerging companies"
   Returns up to 6 deduplicated web sources with title, URL, published_at, snippet.

4. Research & Market Synthesis (Gemini)
   Prompt feeds real Tavily sources to Gemini.
   Enforces response_mime_type="application/json".
   Generates research trends, problems, market signals, customer segments, competitors, gaps, and why-now.

5. Opportunity Hypothesis Generation (Gemini)
   Extracted signals feed second Gemini call.
   Synthesizes 3–5 hypotheses with MVP features, risks, and evidence.

6. Atomic Database Persistence (SQLite)
   DatabaseManager writes to `sessions`, `sources`, `reports`, and `opportunities` in a single transaction.

7. Client Response & Rendering
   FastAPI returns HTTP 200 AnalyzeResponse JSON.
   Next.js UI updates message thread, stops status animation, and mounts research view.
```

---

## 5. Error Handling & Reliability Strategy

| Failure Scenario | Detection Mechanism | System Action & Response |
|---|---|---|
| **Invalid Topic** | Pydantic / FastAPI check | Returns `HTTP 400` with `INVALID_TOPIC` code; UI shows immediate validation toast. |
| **Tavily Search Error** | `TavilyServiceError` | Logged with warning; graceful degradation or user-facing `PIPELINE_ERROR`. |
| **Gemini Rate Limit (429)** | `GeminiRateLimitError` | Intercepted in `gemini_service.py`; maps to `HTTP 429` with `AI_RATE_LIMITED` code; UI prompts user to wait. |
| **Gemini Unavailable (503)** | Exponential backoff | Automatic 3-stage retry (2s, 4s, 8s) in `gemini_service.py` before returning `HTTP 500`. |
| **Malformed LLM JSON** | `_parse_json` regex & `json.loads` | Strips markdown fences, logs parse errors; raises typed `GeminiServiceError`. |
| **Database Failure** | SQLite try-except block | Session transaction rolled back; returns `HTTP 500` with `PERSISTENCE_ERROR`. |
| **Network Timeout** | Frontend `AbortController` (120s) | Prevents hanging client; displays `TIMEOUT` error with retry action. |

---

## 6. Future Multi-Model & Automation Boundaries

### Future Model Routing Concept
```text
               ┌────────────────────────────────────────────────────────┐
               │                   Model Registry                       │
               │  FAST_MODEL  │  BALANCED_MODEL (Default)  │  DEEP_MODEL│
               └──────────────────────────┬─────────────────────────────┘
                                          │
                                          ▼
                               ┌─────────────────────┐
                               │   Model Selector    │
                               │ Session / Task spec │
                               └──────────┬──────────┘
                                          │
                                          ▼
               ┌────────────────────────────────────────────────────────┐
               │                    Agent Execution                     │
               │ Web Research / Extract  ──> FAST_MODEL                 │
               │ Market & Competitive    ──> BALANCED_MODEL             │
               │ Deep Scoring & Synthesis──> DEEP_MODEL                 │
               └────────────────────────────────────────────────────────┘
```

### Future Automation Architecture
The future automation layer will run as a lightweight internal background process within the FastAPI lifecycle:
- **No Heavy Queues:** Uses lightweight asynchronous timers or standard cron-style polling.
- **Cache & Diff Engine:** Hashes previous research outputs per topic; runs Tavily and Gemini *only* when new queries return fresh URLs or updated timestamps.
- **Snapshot Storage:** Future `signals` and `watchlists` tables track temporal changes without overwriting original historical sessions.
