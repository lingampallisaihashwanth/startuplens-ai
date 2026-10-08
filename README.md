# StartupLens AI

**StartupLens AI** is an AI-powered startup research and opportunity intelligence platform. It converts an industry or technology topic into an evidence-backed startup opportunity report, surfacing emerging trends, market signals, competitive gaps, and actionable MVP hypotheses grounded in real-world web research.

---

## Current Product Direction

StartupLens AI helps students, researchers, and early-stage founders answer the question: **"What viable startup opportunities exist in this domain right now, and what evidence supports them?"**

### Core Intelligence Flow

```text
User enters an industry or technology (e.g., "AI Robotics")
                    ↓
             Web Research (Tavily)
                    ↓
             Market Intelligence
                    ↓
          Competitive Intelligence
                    ↓
             Customer Insights
                    ↓
        Startup Opportunity Generation
                    ↓
            Opportunity Validation
                    ↓
              Research Summary
                    ↓
             Evidence + Sources
                    ↓
          SQLite Persistence
                    ↓
           Chat-First Frontend
```

---

## Technology Stack

StartupLens AI uses a disciplined, lightweight architecture avoiding unnecessary enterprise overhead:

| Layer | Technology | Role & Implementation Status |
|---|---|---|
| **Frontend** | **Next.js 16 + React 19 + TypeScript + Tailwind CSS** | **IMPLEMENTED** — Chat-first workspace, sidebar history, saved ideas, live pipeline status, dark/light theme |
| **Backend API** | **FastAPI (Python 3.11+)** | **IMPLEMENTED** — Asynchronous REST API running on port `8003`, Pydantic v2 validation, CORS middleware |
| **LLM Provider** | **Google Gemini** | **IMPLEMENTED** — `gemini-3.5-flash` via official `google-genai` SDK; strict JSON output mode; rate-limit backoff |
| **Web Research** | **Tavily Search API** | **IMPLEMENTED** — Live web search, source deduplication, snippet extraction |
| **Persistence** | **SQLite** | **IMPLEMENTED** — Relational storage (`sessions`, `sources`, `reports`, `opportunities`) with foreign keys and WAL mode |

> **Provider Scope Guard:** Google Gemini is the sole LLM provider. Tavily is the sole web research provider. OpenRouter and third-party LLM aggregators are explicitly **out of scope**.

---

## Current Architecture vs. Future Expansion

### Current Implemented Architecture (MVP)
The running implementation executes an optimized 2-step AI pipeline to minimize latency and manage Gemini free-tier rate limits:
1. **Web Research & Signal Extraction:** Tavily queries live web sources, followed by a merged Gemini extraction call producing structured research facts and initial market analysis.
2. **Opportunity Synthesis:** A second Gemini call converts extracted signals into 3–5 concrete startup hypotheses with target customers, solutions, MVP features, and risks.
3. **Storage & UI:** Complete findings and normalized sources are persisted to SQLite and rendered in the Next.js chat interface.

### Logical Multi-Agent Expansion (Planned)
The product architecture defines **8 specialized logical agent roles**:
1. **Research Coordinator:** Coordinates execution order, tracks lifecycle state, and manages errors without exposing raw chain-of-thought.
2. **Web Research Agent:** Queries Tavily, deduplicates results, normalizes metadata, and filters noise.
3. **Market Intelligence Agent:** Detects market growth drivers, adoption signals, and regulatory patterns.
4. **Competitive Intelligence Agent:** Maps direct/indirect incumbents, identifies positioning, and finds market gaps.
5. **Customer Insights Agent:** Pinpoints buyer personas, pain points, and willingness-to-pay signals.
6. **Startup Opportunity Agent:** Formulates 3–5 structured opportunity hypotheses with MVP specs and risks.
7. **Opportunity Validation Agent:** Scores hypotheses across market demand, competitive pressure, execution feasibility, market timing, and AI advantage.
8. **Research Summary Agent:** Assembles final structured executive synthesis, strictly separating facts from hypotheses.

> *Note:* Logical agent roles represent modular reasoning responsibilities; they do not each require a separate external LLM API request.

---

## Multi-Model Roadmap (Planned)

StartupLens AI will support configurable Gemini model tiers rather than hard-coding model strings:

```text
Model Registry ──> Model Selector ──> Selected Gemini Model ──> Agent Workflow
```

- **`FAST_MODEL` (e.g., Gemini Flash):** Low-latency execution for rapid web extraction and conversational iteration.
- **`BALANCED_MODEL` (e.g., Default Gemini Flash/Pro tier):** Balanced cost-performance for comprehensive market and competitive synthesis.
- **`DEEP_MODEL` (e.g., Gemini Pro):** Deep structural analysis for complex opportunity scoring and cross-domain validation.

---

## Lightweight Automation Roadmap (Planned)

A scheduled background automation layer will deliver continuous intelligence without requiring heavy distributed orchestration (no Redis, Celery, or Kubernetes):
1. **Research Tracker:** Save watchlist topics for continuous monitoring.
2. **Scheduled Research Update:** Periodically refresh saved research topics.
3. **Market Change Detection:** Compare newly gathered signals with historical baseline snapshots.
4. **Opportunity Monitoring:** Re-evaluate saved opportunity scores when significant evidence shifts.
5. **Weekly Startup Brief:** Generate periodic digests of important market shifts and fresh opportunities.

---

## User Interface

The frontend provides an intuitive, research-centric chat experience:
- **Collapsible Sidebar:** Navigation between New Research, Active Chat, Research History, Saved Ideas, and Settings.
- **Conversation Workspace:** Header with topic and model context, clear assistant messaging, and live agent status badges.
- **Structured Report Panels:** Tabbed or modular views for Executive Findings, Market Signals, Competitor Gaps, and Opportunity Cards.
- **Evidence Drawer:** Source cards showing verified titles, publication dates, and external links.
- **Interactive Composer:** Quick research prompts, follow-up query box, and keyboard shortcuts (`Cmd+K` / `Ctrl+K`).

---

## Getting Started Locally

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Google Gemini API Key
- Tavily Search API Key

### 1. Environment Configuration
Create a `.env` file in the project root:
```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.5-flash
TAVILY_API_KEY=your_tavily_api_key
DATABASE_URL=sqlite:///./startuplens.db
```

### 2. Backend Setup & Launch
```bash
# Activate virtual environment
.venv\Scripts\Activate.ps1   # Windows PowerShell
# or: source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt  # or install fastapi uvicorn google-genai tavily-python pydantic-settings

# Run backend on port 8003
uvicorn backend.main:app --host 127.0.0.1 --port 8003 --reload
```
Backend API will be available at: `http://127.0.0.1:8003` (Swagger Docs at `/docs`).

### 3. Frontend Setup & Launch
```bash
cd frontend
npm install
npm run dev
```
Frontend application will be available at: `http://localhost:3000`.

---

## Project Status

- **Status:** **Functional MVP (Core Pipeline Implemented)**
- **Backend API:** Implemented & tested on port `8003`.
- **Frontend UI:** Implemented with chat workspace, history viewer, and saved ideas.
- **Multi-Agent Expansion & Multi-Model:** Architected and documented; planned for implementation.
- **Automation Layer:** Designed; planned for implementation.
