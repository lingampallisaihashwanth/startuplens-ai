# Engineering & Development Standards — StartupLens AI

This document establishes the architectural principles, safety guidelines, and development workflows for contributing to StartupLens AI.

---

## 1. Core Engineering Principles

1. **Inspect Before Modifying:** Always inspect existing code, schemas, and endpoints before introducing changes. Never assume an endpoint or interface exists without verification.
2. **Small, Reversible Changes:** Make atomic, focused edits that can be validated and rolled back easily. Avoid speculative broad-brush refactoring.
3. **No Fake Functionality:** Never mock fake backend responses or create UI controls that simulate non-existent capabilities. Label features accurately as `IMPLEMENTED` or `PLANNED`.
4. **Strong Typing Everywhere:** All backend data transfers must be validated via Pydantic v2 schemas; all frontend components must consume strongly typed TypeScript interfaces.
5. **Zero Secret Leaks:** API keys (`GEMINI_API_KEY`, `TAVILY_API_KEY`) must reside exclusively in `.env`. Never commit secrets or log raw tokens in logfiles or error responses.
6. **Evidence Integrity & Freshness (`CURRENT WEB EVIDENCE > LLM MEMORY`):** Never synthesize fake web citations, statistics, or company names. For any current or time-sensitive factual question, fresh web research via Tavily must supply the evidence; never rely on LLM memory alone. If web research fails, halt with an explicit error rather than hallucinating from model memory.

---

## 2. Multi-Agent & LLM Guidelines

- **Logical vs. Physical Execution:** Treat the 8 logical agent roles as architectural abstractions. Do not force 8 separate Gemini API requests if a combined prompt achieves equal or superior extraction with significantly lower token latency and cost.
- **No Hidden Reasoning:** Do not request chain-of-thought reasoning from the model or expose internal reasoning scratchpads in client UIs. Enforce strict JSON output with `response_mime_type="application/json"`.
- **Model Abstraction & Registry:** Route requests through configurable model placeholders (`FAST_MODEL`, `BALANCED_MODEL`, `DEEP_MODEL`) rather than hard-coding model name strings across multiple modules.
- **Quota & Rate-Limit Handling:** Always catch `GeminiRateLimitError` (`HTTP 429 RESOURCE_EXHAUSTED`). Implement exponential backoff for transient 503 errors and return descriptive guidance to the client when free-tier quotas are exhausted.

---

## 3. Automation Safety & Concurrency

- **Lightweight Infrastructure:** The automation layer must operate as lightweight in-process tasks or periodic polling. **Do not introduce heavy distributed frameworks** such as Redis, Celery, Apache Airflow, Kafka, or Kubernetes.
- **Deduplication of Work:** Avoid redundant Tavily and Gemini calls. Before executing research on a tracked topic, verify whether existing sources or findings remain current.
- **In-Flight Request Guarding:** Frontend and backend must guard against duplicate submissions (via ref-based state guards, UI button disabling, and client-side `AbortController`).
- **Data Change Verification:** The market change detection system must compute deterministic diffs; never fabricate "new trends" if underlying evidence has not shifted.

---

## 4. Database & Persistence Standards

- **Transactions & Cascades:** Maintain SQLite relational integrity. All related data across `sessions`, `sources`, `reports`, and `opportunities` must be committed atomically and deleted via cascading foreign keys (`PRAGMA foreign_keys = ON;`).
- **Concurrent Access:** Keep Write-Ahead Logging active (`PRAGMA journal_mode = WAL;`) with reasonable connection timeouts (e.g., 30.0s).
- **Schema Evolution:** When introducing future tables (`agent_runs`, `watchlists`, `signals`), implement explicit migrations or backwards-compatible `CREATE TABLE IF NOT EXISTS` checks.

---

## 5. Documentation Synchronization Rule

Whenever a feature is implemented or an architecture is updated:
- Cross-reference all 12 project documentation files.
- Maintain the strict rule:
  - **`IMPLEMENTED`**: Confirmed working in existing project code, configuration, or tests.
  - **`PLANNED`**: Desired future feature not yet implemented.
- Never document future functionality as already working.

---

## 6. Testing & Quality Verification

Run automated test suites to ensure zero regressions across changes:

```bash
# Run backend pytest suite (unit tests & API contracts)
pytest backend/tests/ -v

# Run database tests specifically
pytest backend/tests/test_database.py -v

# Run API endpoint tests
pytest backend/tests/test_api.py -v

# Build frontend to verify TypeScript types
cd frontend
npm run build
```
