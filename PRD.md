# Product Requirements Document (PRD) — StartupLens AI

## 1. Problem
Entrepreneurs, students, and innovation teams face significant friction when evaluating new venture ideas. Market signals, technical trends, incumbent competitor footprints, and customer pain points are scattered across disparate reports, press releases, forums, and technical articles. 

Manual research is time-intensive, unstructured, and susceptible to confirmation bias. Furthermore, general-purpose LLMs frequently hallucinate sources, fabricate market sizing numbers, and conflate speculative opinions with verified facts.

---

## 2. Product Goal
StartupLens AI is an AI-powered startup research and opportunity intelligence platform. It systematically analyzes any industry or technology topic, gathers real-world web research, synthesizes market and competitive intelligence, and formulates evidence-backed startup opportunity hypotheses accompanied by actionable MVP definitions and source citations.

---

## 3. Target Users
- **Student Founders & University Innovators:** Seeking high-potential domain topics grounded in current market signals.
- **Early-Stage Entrepreneurs:** Validating problem spaces, identifying unmet customer pain points, and discovering incumbent gaps.
- **Venture Analysts & Incubators:** Conducting preliminary market mapping, competitive landscapes, and timing analysis.
- **Product Builders & Hackathon Participants:** Sourcing concrete MVP feature hypotheses for rapid prototyping.

---

## 4. Core User Story
> **As an aspiring founder or researcher,**  
> I want to enter an emerging technology or industry topic (e.g., *"AI Robotics"*, *"Synthetic Biology"*, *"Autonomous Freight"*),  
> **so that I can receive an evidence-backed intelligence report** detailing market trends, competitor gaps, customer pain points, viable startup opportunity hypotheses, MVP features, and verifiable web sources.

---

## 5. Core Product Philosophy & Reliability Principles
StartupLens AI is built upon rigorous intelligence standards:
1. **Current Web Evidence > LLM Memory:** For current factual questions (latest startups, recent funding, new competitors, current pricing, recent news), fresh web research via Tavily takes precedence. The model must NOT rely on internal pre-training memory for current facts.
2. **Evidence Before Conclusions:** Every claim, competitor name, and market trend must be grounded in real-world search evidence.
3. **Strict Separation of Facts and Hypotheses:** 
   - **FACT:** Directly supported by retrieved evidence.
   - **INTERPRETATION:** Analysis and synthesis of the evidence.
   - **OPPORTUNITY HYPOTHESIS:** Testable startup concepts derived from evidence (never guarantees).
4. **Zero Fabricated Sources or Facts:** Never invent companies, funding amounts, dates, statistics, products, competitors, URLs, or citations. When evidence is insufficient, state: *"Insufficient recent evidence found."*
5. **Source Freshness & Stale Source Protection:** Capture `title`, `url`, `published_at`, `source_type`, `snippet`, and `retrieved_at`. Identify and label older sources (>2.5 years) as historical context rather than current evidence. Never fabricate a publication date.
6. **Duplicate Source Protection:** Deduplicate sources across canonical URLs (stripping tracking parameters) and domain + title normalization.
7. **Mandatory Web Research:** If Tavily search fails or returns zero sources, the system halts with *"Current web research could not be completed. Try again when web research is available."* rather than hallucinating from LLM memory.
8. **Structured Outputs:** All agent reasoning outputs strictly adhere to strongly-typed JSON schemas.
9. **No Hidden Reasoning:** Communicate high-level progress indicators without dumping raw chain-of-thought into the UI.

---

## 6. Functional Features & Implementation Status

### 6.1 Topic Ingestion & Input Validation
- **Status:** **IMPLEMENTED**
- Accepts industry or technology query string (minimum 2 characters).
- Enforces strict validation with descriptive error responses (`INVALID_TOPIC`).

### 6.2 Live Web Research & Evidence Acquisition
- **Status:** **IMPLEMENTED**
- Integrates Tavily Search API to acquire up-to-date web articles, news, and reports.
- Extracts source title, URL, published date, and relevant snippets.
- Deduplicates and normalizes sources prior to analysis.

### 6.3 Market & Competitive Intelligence Synthesis
- **Status:** **IMPLEMENTED** (Optimized pipeline via Google Gemini)
- Extracts emerging market trends, adoption signals, and customer pain points.
- Identifies active market participants, competitors, and potential unmet gaps.
- Analyzes "Why Now" macroeconomic, technological, or regulatory timing drivers.

### 6.4 Startup Opportunity Generation
- **Status:** **IMPLEMENTED**
- Synthesizes 3–5 structured opportunity hypotheses per session.
- Output schema per opportunity:
  - `title`: Compelling name for the venture concept
  - `problem`: Specific customer friction point
  - `customer`: Distinct target buyer or user segment
  - `solution`: Proposed product or platform concept
  - `why_now`: Catalysts enabling adoption today
  - `competitors`: Incumbents or alternative solutions
  - `mvp_features`: 3–4 concrete features for an initial build
  - `risks`: Key execution, market, or technological risks
  - `evidence`: Bulleted citations linking directly to gathered search findings

### 6.5 Chat-First Research Workspace
- **Status:** **IMPLEMENTED**
- Modern dark/light theme interface with sidebar navigation, research composer, and instant suggestion chips.
- Visual real-time agent pipeline progress indicators.
- Interactive opportunity cards with expandable MVP feature sets and direct source drawer.
- Save opportunities to local storage for quick access.

### 6.6 Session Persistence & History
- **Status:** **IMPLEMENTED**
- SQLite persistence storing sessions, reports, sources, and opportunity cards with cascading referential integrity.
- Sidebar search and history view enabling retrieval and safe deletion of previous research runs.

### 6.7 Multi-Agent Role Expansion
- **Status:** **PLANNED**
- Modularization of the intelligence pipeline into 8 dedicated logical agents:
  1. Research Coordinator
  2. Web Research Agent
  3. Market Intelligence Agent
  4. Competitive Intelligence Agent
  5. Customer Insights Agent
  6. Startup Opportunity Agent
  7. Opportunity Validation Agent (evidence-based scoring)
  8. Research Summary Agent
- *Note:* Logical modularity does not imply 8 separate Gemini API requests; execution may combine stages for performance and rate-limit conservation.

### 6.8 Multi-Model Registry & Dynamic Selection
- **Status:** **PLANNED**
- Configurable model tiers powered by Google Gemini:
  - `FAST_MODEL`: Low latency, rapid extraction.
  - `BALANCED_MODEL`: Default tier balancing latency and analytical depth.
  - `DEEP_MODEL`: In-depth opportunity validation and scoring.
- Selection controlled via configuration and UI settings without hardcoding.

### 6.9 Lightweight Research Automation
- **Status:** **PLANNED**
- Asynchronous monitoring layer without heavy infrastructure (no Redis, Celery, or Kubernetes):
  - **Research Tracker:** Watchlist topic registration.
  - **Scheduled Research Update:** Periodic refresh of monitored domains.
  - **Market Change Detection:** Delta comparison against baseline findings.
  - **Opportunity Monitoring:** Re-scoring hypotheses when new evidence arises.
  - **Weekly Startup Brief:** Synthesized update summary for tracked topics.

### 6.10 Follow-Up Interactive Chat
- **Status:** **PLANNED** (Backend endpoint not yet implemented)
- Ability to conduct multi-turn conversational exploration over a completed research session.

---

## 7. Success Criteria
1. **Pipeline Execution:** A user enters a topic and receives a comprehensive, structured report within 30–60 seconds.
2. **Evidence Integrity:** 100% of cited sources correspond to verified Tavily web results.
3. **Structured Reliability:** All pipeline outputs conform strictly to predefined Pydantic and TypeScript contracts.
4. **Zero Fluff:** Hypotheses provide specific, concrete MVP features and explicit risks rather than generic marketing statements.
5. **Robust Error Handling:** Clear user feedback for invalid topics, network interruptions, or LLM rate limits (`HTTP 429`).

---

## 8. Non-Goals
To preserve focus and rapid execution, the following are explicitly out of scope:
- **No Third-Party Model Aggregators:** Sole LLM provider is Google Gemini; OpenRouter is strictly excluded.
- **No Heavy Distributed Orchestration:** No Celery, Redis, Apache Airflow, Kafka, or Kubernetes.
- **No Vector Database Overhead:** Standard relational SQLite fulfills all persistence and retrieval requirements.
- **No Financial / Investment Guarantees:** StartupLens produces qualitative research hypotheses, not automated financial advice.
- **No User Monetization / Payment Gateways:** Not applicable to the research and academic prototype scope.
