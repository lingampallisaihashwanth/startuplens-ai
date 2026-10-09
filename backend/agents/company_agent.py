import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.services.tavily_service import tavily_service, TavilyServiceError
from backend.llm import llm_router
from backend.llm.base import (
    LLMRequest,
    LLMError,
    LLMRateLimitError,
    LLMQuotaExhaustedError,
    LLMServiceUnavailableError,
    LLMAuthError,
    LLMInvalidRequestError,
)
from backend.schemas.research import ResearchOutput, ResearchSource
from backend.schemas.analysis import MarketAnalysisOutput
from backend.schemas.company_analysis import CompanyAnalysisOutput
from backend.database.db import db

logger = logging.getLogger(__name__)


class CompanyAnalysisAgent:
    """
    Dedicated agent for analyzing existing companies across 19 critical dimensions:
    - Founding story, business model, early growth, milestones
    - Funding, competition, turning points, warning signs
    - Strategic errors, financial issues, reasons for decline/failure or success
    - Current status and actionable lessons for founders
    - Rigorous categorization into FACT, INFERENCE, and HYPOTHESIS.
    """

    def __init__(self):
        self.last_execution: Dict[str, Any] = {}

    def run(
        self,
        company_name: str,
        topic: str,
        document_ids: Optional[List[str]] = None,
        model_id: Optional[str] = None,
    ) -> Tuple[ResearchOutput, MarketAnalysisOutput, CompanyAnalysisOutput]:
        logger.info(
            f"CompanyAnalysisAgent: beginning research on company '{company_name}' (query: '{topic}')"
        )
        now_iso = datetime.now(timezone.utc).isoformat()

        # Step 1: Tavily Web Search
        if not tavily_service.is_configured():
            raise TavilyServiceError(
                "Current web research could not be completed. Try again when web research is available."
            )

        # Formulate targeted search queries
        query = f"{company_name} founding story business model milestones growth decline status"
        try:
            web_sources = tavily_service.search(query=query, max_results=7)
            if not web_sources:
                # Try fallback simpler query
                web_sources = tavily_service.search(query=company_name, max_results=6)
        except TavilyServiceError as e:
            logger.error(f"Tavily web search failed for company '{company_name}': {e}")
            raise TavilyServiceError(
                "Current web research could not be completed. Try again when web research is available."
            )

        if not web_sources:
            raise TavilyServiceError(
                f"No web sources found for company '{company_name}'. Please verify the company name."
            )

        # Step 2: Format sources for LLM context
        formatted_sources_list = []
        for i, s in enumerate(web_sources):
            pub_date = s.get("published_at") or "Date unspecified"
            freshness = s.get("freshness_label") or "Current"
            src_type = s.get("source_type") or "web"
            formatted_sources_list.append(
                f"Web Source [{i+1}]:\n"
                f"Title: {s.get('title', '')}\n"
                f"URL: {s.get('url', '')}\n"
                f"Published: {pub_date} ({freshness}) | Type: {src_type}\n"
                f"Snippet: {s.get('snippet', '')[:450]}"
            )
        formatted_sources = "\n\n".join(formatted_sources_list)

        system_prompt = (
            "You are the Senior Company & Venture Intelligence Analyst for StartupLens AI. "
            "Perform an objective, evidence-grounded case study of the requested company. "
            "Never invent revenue numbers, valuation figures, dates, or causes of failure. "
            "If evidence is insufficient or missing for any item, state 'Insufficient recent evidence found.' "
            "Strictly categorize findings into FACT (verified claims), INFERENCE (logical deductions), "
            "and HYPOTHESIS (analytical perspectives). Return valid JSON only."
        )

        user_prompt = f"""Target Company: {company_name}
User Query: {topic}

RETRIEVED WEB SOURCES (Verified live evidence retrieved at {now_iso}):
{formatted_sources}

CRITICAL RESEARCH INSTRUCTIONS:
1. Research all 19 dimensions below strictly based on the retrieved web sources and verifiable market history.
2. Do NOT fabricate numbers, funding rounds, valuations, dates, or causes of failure.
3. Explicitly separate:
   - facts: Directly verified claims grounded in sources (funding, dates, reported revenue, filings).
   - inferences: Logical deductions drawn from reported operational and market evidence.
   - hypotheses: Analytical interpretations or strategic hypotheses regarding decisions and outcomes.

Return valid JSON conforming EXACTLY to this schema:
{{
  "company_analysis": {{
    "company_name": "{company_name}",
    "overview": "1. Company overview and mission",
    "founding_story": "2. Founding story, founders, and origin",
    "original_problem": "3. Original problem the company set out to solve",
    "business_model": "4. Business model, pricing, and monetization mechanisms",
    "target_customers": "5. Primary target customer profiles and segments",
    "early_growth": "6. Early growth trajectory and initial traction",
    "growth_strategy": "7. Core growth strategy and acquisition channels",
    "funding_and_expansion": "8. Funding history, capital raised, and expansion moves",
    "major_milestones": ["Milestone 1", "Milestone 2"],
    "growth_drivers": ["Growth driver 1", "Growth driver 2"],
    "turning_points": ["Turning point 1", "Turning point 2"],
    "warning_signs": ["Warning sign 1", "Warning sign 2"],
    "competition": "13. Competitive dynamics, competitors, and rivalries",
    "market_changes": "14. Broader macroeconomic, industry, or regulatory shifts",
    "strategic_mistakes": ["Strategic mistake 1", "Strategic mistake 2"],
    "financial_problems": ["Financial problem or burn rate issue 1", "Unit economics issue 2"],
    "reasons_for_decline_or_failure": ["Reason 1", "Reason 2"],
    "current_status": "18. Current status and latest situation based on evidence",
    "lessons_for_founders": ["Lesson 1", "Lesson 2"],
    "facts": ["[FACT] Verified claim with source citation", "[FACT] Another verified fact"],
    "inferences": ["[INFERENCE] Deductive insight based on reported metrics"],
    "hypotheses": ["[HYPOTHESIS] Strategic interpretation of strategic pivot or mistake"]
  }},
  "research": {{
    "topic": "{topic}",
    "trends": ["Industry trend 1", "Industry trend 2"],
    "startups": ["{company_name}", "Related competitor 1"],
    "problems": ["Customer friction point 1"],
    "market_signals": ["Signal 1 with source reference"],
    "sources": []
  }},
  "analysis": {{
    "market_signals": ["Market signal 1"],
    "customer_segments": ["Target segment 1"],
    "competitors": ["Competitor 1", "Competitor 2"],
    "market_gaps": ["Market gap observed"],
    "why_now": ["Catalyst / timing driver"],
    "trends": ["Trend 1"],
    "problems": ["Problem 1"]
  }}
}}
"""

        llm_request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
        )

        try:
            llm_response = llm_router.generate_json(
                request=llm_request,
                model_id=model_id,
                task_type="analysis",
            )
            self.last_execution = {
                "provider": llm_response.provider,
                "model": llm_response.model,
                "fallback_used": llm_response.fallback_used,
                "fallback_reason": llm_response.fallback_reason,
                "latency_ms": llm_response.latency_ms,
            }
            content = llm_response.content

            raw_company = content.get("company_analysis", {})
            raw_research = content.get("research", {})
            raw_analysis = content.get("analysis", {})

            # Ensure company_name is set
            if not raw_company.get("company_name"):
                raw_company["company_name"] = company_name

            raw_research["sources"] = list(web_sources)
            raw_research["topic"] = topic
            raw_research["retrieved_at"] = now_iso

            company_output = CompanyAnalysisOutput(**raw_company)
            research_output = ResearchOutput(**raw_research)
            analysis_output = MarketAnalysisOutput(**raw_analysis)

            logger.info(
                f"CompanyAnalysisAgent complete for '{company_name}': "
                f"provider={llm_response.provider}, model={llm_response.model}"
            )
            return research_output, analysis_output, company_output

        except (
            LLMQuotaExhaustedError,
            LLMRateLimitError,
            LLMServiceUnavailableError,
            LLMAuthError,
            LLMInvalidRequestError,
        ):
            raise
        except LLMError:
            raise
        except Exception as e:
            logger.error(
                f"CompanyAnalysisAgent unexpected failure: {type(e).__name__}: {e}",
                exc_info=True,
            )
            raise LLMError(f"Company analysis reasoning failed: {type(e).__name__}: {e}")


company_agent = CompanyAnalysisAgent()
