# Development Roadmap & Evolution Plan — StartupLens AI

This roadmap outlines the disciplined rollout of StartupLens AI, prioritizing a reliable, evidence-grounded college MVP before expanding into advanced multi-agent modularity, multi-model selection, and lightweight research automation.

---

## Evolution Phases Overview

```text
┌─────────────────────────┐     ┌─────────────────────────┐     ┌─────────────────────────┐     ┌─────────────────────────┐
│        Phase 1          │     │        Phase 2          │     │        Phase 3          │     │        Phase 4          │
│       Current MVP       │ ──> │   Multi-Agent Expansion │ ──> │   Multi-Model Support   │ ──> │   Research Automation   │
│   (College Milestone)   │     │   (8 Logical Agents)    │     │  (Fast / Balanced / Deep│     │   (Tracker & Signals)   │
│       IMPLEMENTED       │     │         PLANNED         │     │         PLANNED         │     │         PLANNED         │
└─────────────────────────┘     └─────────────────────────┘     └─────────────────────────┘     └─────────────────────────┘
```

---

## Phase 1 — Current MVP: Working Intelligence Pipeline
**Status:** **IMPLEMENTED** (Core College MVP Foundation)

Focus: Deliver a robust end-to-end prototype validating live web research, signal extraction, opportunity synthesis, and relational persistence.

### Deliverables Completed
- [x] **Backend Infrastructure:** FastAPI asynchronous service running on port `8003`.
- [x] **Web Research Integration:** Tavily Search API client fetching live web sources and deduplicating citations.
- [x] **LLM Integration:** Google Gemini client (`google-genai` SDK) utilizing strict JSON mode and exponential retry logic.
- [x] **Consolidated AI Pipeline:** Two-stage pipeline (Research + Market Analysis, followed by Opportunity Synthesis) to preserve quota and minimize latency.
- [x] **Persistence:** SQLite relational database with cascading foreign keys (`sessions`, `sources`, `reports`, `opportunities`).
- [x] **Chat-First Frontend:** Next.js 16 + React 19 + TypeScript + Tailwind CSS application with custom dark/light theme tokens.
- [x] **Research Workspace:** Interactive conversation layout with live agent progress states, structured findings tabs, expandable opportunity cards, and external evidence links.
- [x] **Session History & Saved Ideas:** Client and server-backed session retrieval and idea bookmarking.
- [x] **Automated Testing:** Pytest suite covering database transactions and API endpoints with mocks.

---

## Phase 2 — Multi-Agent Expansion
**Status:** **PLANNED** (Next Architectural Milestone)

Focus: Expand internal modularity into the 8 dedicated logical agent roles without compromising latency or API rate limits.

### Planned Tasks
- [ ] **Dedicated Research Coordinator:** Formalize orchestrator class managing agent transitions and lifecycle events.
- [ ] **Granular Competitive Intelligence Agent:** Extract detailed competitor positioning matrices and incumbent limitations.
- [ ] **Customer Insights Agent:** Decompose user personas and map explicit pain points to supporting quotes.
- [ ] **Opportunity Validation Agent:** Implement 5-dimension scoring engine (Market Demand, Competitive Pressure, Feasibility, Timing, AI Advantage) with evidence-backed rationales.
- [ ] **Research Summary Agent:** Generate standalone executive synthesis highlighting critical assumptions and data limitations.
- [ ] **Follow-Up Conversational Endpoint:** Implement `POST /research/{session_id}/chat` for multi-turn Q&A over existing session context.

---

## Phase 3 — Multi-Model Support
**Status:** **PLANNED** (Model Abstraction & Tiering)

Focus: Introduce dynamic Gemini model selection without hardcoding specific model identifiers.

### Planned Tasks
- [ ] **Model Registry:** Define configured Gemini tiers (`FAST_MODEL`, `BALANCED_MODEL`, `DEEP_MODEL`).
- [ ] **Model Selector API:** Expose `GET /models` endpoint returning model metadata and capabilities.
- [ ] **Session Model Metadata:** Track which model was utilized per research run in database records.
- [ ] **Frontend Model Selector:** Add clean dropdown in the conversation header for user-driven model choice.
- [ ] **Tiered Agent Execution:** Route rapid web extraction to `FAST_MODEL` and deep validation to `DEEP_MODEL`.

---

## Phase 4 — Research Automation
**Status:** **PLANNED** (Continuous Intelligence Layer)

Focus: Enable continuous topic monitoring without heavy distributed orchestration (no Redis, Celery, or Kubernetes).

### Planned Tasks
- [ ] **Research Tracker:** Allow users to add research topics to an active watchlist (`watchlists` table).
- [ ] **Scheduled Refresh Jobs:** Lightweight background polling to check for updated Tavily search results.
- [ ] **Market Change Detection:** Compute semantic and structural deltas between historical and fresh research baselines (`signals` table).
- [ ] **Opportunity Re-Scoring:** Automatically re-evaluate opportunity viability when significant new evidence emerges.
- [ ] **Weekly Startup Brief:** Synthesize a weekly executive brief summarizing market shifts across all monitored topics.

---

## Summary: MVP vs. Next vs. Future

| Scope Classification | Key Features Included |
|---|---|
| **MVP (Current)** | Topic input, Tavily web search, 2-stage Gemini pipeline, 3–5 opportunity hypotheses, SQLite persistence, chat-first UI, history, saved ideas |
| **Next (Phase 2 & 3)** | 8 logical agent roles, explicit opportunity validation scoring, follow-up chat endpoint, Gemini multi-model registry and UI selector |
| **Future (Phase 4)** | Watchlist tracker, automated periodic updates, market change detection, opportunity re-scoring, weekly startup briefs |
