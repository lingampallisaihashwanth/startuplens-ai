# Agent Specifications — StartupLens AI

This document defines the **8 logical agent roles** that govern the research and intelligence pipeline of StartupLens AI.

> **Architectural Note on Execution:**  
> A *logical agent role* defines a modular boundary of analytical responsibility. A logical agent role does **not** necessarily equal one independent LLM API call. In production and resource-constrained environments, related reasoning roles can be consolidated into optimized multi-part prompts to reduce token overhead, minimize latency, and stay within API rate limits.

---

## 1. Research Coordinator

- **Purpose:** Coordinates the end-to-end intelligence workflow, controls agent execution sequence, manages task state, and aggregates outputs.
- **Inputs:** User topic string, user execution preferences (e.g., target model tier).
- **Responsibilities:**
  - Validates incoming topic parameters.
  - Sequentially invokes the research, analysis, opportunity, validation, and summary stages.
  - Tracks high-level execution milestones (`searching`, `extracting`, `analyzing`, `generating`, `validating`, `done`).
  - Catches upstream errors and triggers graceful fallback or user-facing messaging.
  - Ensures no raw hidden reasoning or chain-of-thought tokens are exposed to the client.
- **Outputs:** Consolidated pipeline payload ready for database persistence and client presentation.
- **Evidence Requirements:** Enforces that downstream stages retain source references before persisting.
- **Failure Behavior:** If a critical stage fails, marks the session as failed, logs the error internally, and issues a structured API error response.

---

## 2. Web Research Agent

- **Purpose:** Queries live web sources using Tavily to acquire fresh, verifiable domain evidence.
- **Inputs:** Verified user topic and domain keywords.
- **Responsibilities:**
  - Formulates targeted search queries for market signals, customer problems, and emerging ventures.
  - Queries the Tavily Search API.
  - Cleans and deduplicates retrieved URLs and snippets.
  - Normalizes metadata (source title, URL, published timestamp, source type).
- **Outputs:** Normalized list of search source objects (`title`, `url`, `published_at`, `source_type`, `snippet`, `retrieved_at`, `freshness_label`, `is_historical`).
- **Evidence Requirements:** 100% genuine external URLs and titles; never generates mock or synthesized web links. Preserves publication dates when available; identifies older sources (>2.5 years) as historical context.
- **Failure Behavior:** If search yields zero results or Tavily fails, halts the pipeline immediately with `WEB_RESEARCH_FAILED` ("Current web research could not be completed. Try again when web research is available.") rather than falling back to LLM internal knowledge.

---

## 3. Market Intelligence Agent

- **Purpose:** Identifies macroeconomic trends, technological breakthroughs, adoption indicators, and market segments strictly from retrieved web evidence.
- **Inputs:** Normalized search evidence from the Web Research Agent.
- **Responsibilities:**
  - Enforces `CURRENT WEB EVIDENCE > LLM MEMORY` for all current market observations.
  - Identifies emerging trends shaping the industry.
  - Detects market signals (recent funding rounds, corporate investments, regulatory shifts, growth metrics) linked directly to retrieved sources.
  - Categorizes market segments and maturity stages.
  - Analyzes the "Why Now" catalyst driving rapid adoption today.
  - If evidence is sparse for any signal, explicitly outputs *"Insufficient recent evidence found."* rather than inventing data.
- **Outputs:** Structured market intelligence payload containing trends, signals, segments, and timing drivers.
- **Evidence Requirements:** Every reported trend and market signal must be directly supported by or traceable to one or more retrieved sources.
- **Failure Behavior:** If evidence is sparse, notes limited market visibility and restricts conclusions to verifiable observations.

---

## 4. Competitive Intelligence Agent

- **Purpose:** Analyzes existing incumbents, direct/indirect competitors, and identifies potential market gaps.
- **Inputs:** Normalized search evidence and preliminary market trends.
- **Responsibilities:**
  - Extracts names of active startups and incumbent organizations mentioned in research.
  - Compares competitor positioning, target audiences, and legacy approaches.
  - Evaluates observed strengths and limitations based strictly on reported evidence.
  - Identifies underserved niches and viable market gaps.
- **Outputs:** Structured competitive landscape containing competitor listings, positioning summaries, and market gaps.
- **Evidence Requirements:** Competitor names must be verified entities found in the research data; no fictional company names.
- **Failure Behavior:** If no direct competitors appear in search results, notes the landscape as nascent or fragmented rather than inventing competitors.

---

## 5. Customer Insights Agent

- **Purpose:** Identifies buyer personas, workflows, and recurring customer friction points.
- **Inputs:** Normalized search evidence and market signals.
- **Responsibilities:**
  - Identifies customer segments experiencing acute pain points.
  - Catalogs specific operational, financial, or technical problems.
  - Connects customer complaints to corroborating web evidence.
  - Clearly distinguishes reported customer pain points from speculative interpretations.
- **Outputs:** Structured list of customer personas, validated problem statements, and associated evidence links.
- **Evidence Requirements:** Pain points must be grounded in real-world user feedback, forum discussions, surveys, or news reports present in search data.
- **Failure Behavior:** If customer signals are ambiguous, clearly labels them as preliminary observations.

---

## 6. Startup Opportunity Agent

- **Purpose:** Formulates 3–5 high-leverage startup opportunity hypotheses based on market gaps and customer problems.
- **Inputs:** Market intelligence, competitive landscape, customer pain points, and supporting sources.
- **Responsibilities:**
  - Generates 3–5 distinct venture concepts addressing identified market gaps.
  - Defines target customer profiles and specific solution mechanisms.
  - Explains the "Why Now" adoption catalyst.
  - Details 3–4 concrete MVP features scoped for rapid execution (e.g., a 4-week build).
  - Identifies key execution, technological, and market risks.
  - Links relevant web evidence to each opportunity hypothesis.
- **Outputs:** List of structured `Opportunity` objects conforming to the agreed schema.
- **Evidence Requirements:** Opportunities are explicitly framed as **hypotheses**, grounded in gathered evidence, never guaranteed business models.
- **Failure Behavior:** Returns fewer high-quality, evidence-backed opportunities (minimum 2–3) rather than fabricating low-conviction ideas.

---

## 7. Opportunity Validation Agent

- **Purpose:** Objectively evaluates and scores generated startup opportunities against critical venture viability dimensions.
- **Inputs:** Generated opportunity hypotheses, competitive analysis, and market evidence.
- **Responsibilities:**
  - Evaluates each hypothesis across 5 core dimensions:
    1. *Market Demand:* Urgency of the customer pain point and willingness to pay.
    2. *Competitive Pressure:* Presence of dominant incumbents vs. open white space.
    3. *Execution Feasibility:* Complexity of MVP build within practical constraints.
    4. *Market Timing:* Strength of "Why Now" catalysts.
    5. *AI / Technical Advantage:* Degree to which modern technology creates an unfair advantage.
  - Provides concise, evidence-informed scoring rationales.
  - Maintains humility: scores are analytical estimates, not absolute guarantees.
- **Outputs:** Structured validation scorecards attached to each opportunity hypothesis.
- **Evidence Requirements:** Scoring rationales must cite evidence or absence of evidence from previous pipeline stages.
- **Failure Behavior:** If evidence is insufficient to score a dimension reliably, assigns a neutral score and flags data uncertainty.

---

## 8. Research Summary Agent

- **Purpose:** Synthesizes the final structured research summary, unifying findings into an executive-ready brief.
- **Inputs:** Complete outputs from Market, Competitive, Customer, Opportunity, and Validation agents.
- **Responsibilities:**
  - Formulates an executive overview summarizing industry status.
  - Harmonizes findings, ensuring consistency between market signals and opportunity cards.
  - Rigorously separates verified facts from analytical interpretations and venture hypotheses.
  - Formats citations and ensures all claims map to valid external sources.
- **Outputs:** Final structured summary object integrated into the `AnalyzeResponse`.
- **Evidence Requirements:** Summary must accurately reflect the underlying evidence without exaggerating certainty or statistics.
- **Failure Behavior:** Falls back to rendering raw stage outputs if executive synthesis generation encounters an issue.

---

## Summary of Agent States in Current vs. Planned Architecture

| Logical Agent Role | Current Implementation (MVP) | Planned Multi-Agent Expansion |
|---|---|---|
| **1. Research Coordinator** | Integrated in FastAPI handler (`backend/main.py`) | Dedicated coordinator class managing lifecycle hooks |
| **2. Web Research Agent** | Implemented via `TavilyService` (`backend/services/tavily_service.py`) | Modular agent with query expansion and filter tuning |
| **3. Market Intelligence Agent** | Merged in `ResearchAgent` Gemini call (`backend/agents/research_agent.py`) | Dedicated reasoning role with signal classification |
| **4. Competitive Intelligence Agent** | Merged in `ResearchAgent` Gemini call | Dedicated competitive mapping and positioning matrix |
| **5. Customer Insights Agent** | Merged in `ResearchAgent` Gemini call | Dedicated customer persona and workflow decomposition |
| **6. Startup Opportunity Agent** | Implemented in `OpportunityAgent` (`backend/agents/opportunity_agent.py`) | Enhanced opportunity synthesis with MVP specifications |
| **7. Opportunity Validation Agent** | Qualitative risks in `OpportunityAgent` | Explicit multi-dimensional evidence scoring engine |
| **8. Research Summary Agent** | Structured JSON synthesis in API response | Dedicated executive briefing and cross-evidence auditor |
