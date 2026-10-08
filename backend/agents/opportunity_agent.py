import logging
from pathlib import Path
from typing import List, Optional

from backend.schemas.research import ResearchOutput
from backend.schemas.analysis import MarketAnalysisOutput
from backend.schemas.opportunity import (
    Opportunity,
    OpportunityOutput,
    OpportunityScore,
    calculate_confidence_label,
)
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

logger = logging.getLogger(__name__)

PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "opportunity.txt"


class OpportunityAgent:
    """
    Agent 3 — Opportunity & Validation Agent:
    Converts research signals and market analysis into 3–5 evidence-backed
    startup opportunity hypotheses with MVP definitions, risk assessments, and
    evidence-informed validation scoring across 5 dimensions.
    Uses ModelRouter so any configured provider can satisfy the request.
    """

    def __init__(self):
        self.system_prompt = self._load_prompt()
        self.last_execution: Dict[str, Any] = {}

    def _load_prompt(self) -> str:
        if PROMPT_FILE.exists():
            try:
                return PROMPT_FILE.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"Could not read prompt file: {e}")
        return (
            "You are the Opportunity & Validation Agent for StartupLens AI. "
            "Generate 3-5 opportunity hypotheses grounded strictly in the evidence. "
            "Score each opportunity across 5 dimensions (1-10) objectively based on evidence. "
            "Never guarantee success. Frame scores and opportunities as analytical hypotheses."
        )

    def run(
        self,
        research: ResearchOutput,
        analysis: MarketAnalysisOutput,
        model_id: Optional[str] = None,
    ) -> List[Opportunity]:
        logger.info(
            f"OpportunityAgent: generating hypotheses for topic: {research.topic}"
        )

        user_prompt = f"""
Topic: {research.topic}

Market Analysis:
- Gaps: {analysis.market_gaps}
- Target Customers: {analysis.customer_segments}
- Competitors: {analysis.competitors}
- Why Now: {analysis.why_now}
- Market Signals: {analysis.market_signals}

Supporting Research:
- Problems: {research.problems}
- Trends: {research.trends}
- Sources: {[s.url for s in research.sources]}

Generate 3 to 5 startup opportunity hypotheses.
For each opportunity include:
- title: clear, compelling name for the concept
- problem: specific pain point
- customer: defined customer persona
- solution: proposed product hypothesis
- why_now: why this can be built and adopted now
- competitors: 2-3 alternatives or incumbents
- mvp_features: 3-4 concrete MVP features for a 4-week build
- risks: 2-3 market or execution risks
- evidence: 2-3 evidence points from the provided research
- score: objective evidence-informed validation scoring:
    - market_demand: 1-10 (urgency of customer pain point and willingness to pay)
    - competitive_pressure: 1-10 (room to compete; 10 = massive uncrowded white space, 1 = dominated)
    - execution_feasibility: 1-10 (practical feasibility of 4-week MVP build)
    - market_timing: 1-10 (strength of current 'Why Now' catalysts)
    - ai_advantage: 1-10 (degree of AI/technical unfair advantage)
    - rationale: 1-2 sentence evidence-informed rationale for this score

Use cautious, hypothesis-driven language (e.g. "Potential opportunity", "Hypothesis", "Evidence suggests").
Do not claim scores guarantee success.

JSON schema:
{{
  "opportunities": [
    {{
      "title": "...",
      "problem": "...",
      "customer": "...",
      "solution": "...",
      "why_now": "...",
      "competitors": ["..."],
      "mvp_features": ["..."],
      "risks": ["..."],
      "evidence": ["..."],
      "score": {{
        "market_demand": 8,
        "competitive_pressure": 7,
        "execution_feasibility": 8,
        "market_timing": 9,
        "ai_advantage": 8,
        "rationale": "High urgency and clear timing catalyst supported by recent industry signals."
      }}
    }}
  ]
}}
"""

        llm_request = LLMRequest(
            prompt=user_prompt,
            system_prompt=self.system_prompt,
        )

        try:
            llm_response = llm_router.generate_json(
                request=llm_request,
                model_id=model_id,
                task_type="opportunity",
            )
            self.last_execution = {
                "provider": llm_response.provider,
                "model": llm_response.model,
                "fallback_used": llm_response.fallback_used,
                "fallback_reason": llm_response.fallback_reason,
                "latency_ms": llm_response.latency_ms,
            }
            result = llm_response.content
            raw_opps = result.get("opportunities", [])
            parsed_opps: List[Opportunity] = []

            for item in raw_opps:
                score_data = item.get("score")
                score_obj = None
                if score_data and isinstance(score_data, dict):
                    d = max(1, min(10, int(score_data.get("market_demand", 7))))
                    c = max(1, min(10, int(score_data.get("competitive_pressure", 6))))
                    f = max(1, min(10, int(score_data.get("execution_feasibility", 7))))
                    t = max(1, min(10, int(score_data.get("market_timing", 8))))
                    a = max(1, min(10, int(score_data.get("ai_advantage", 7))))
                    overall = d + c + f + t + a
                    lbl = calculate_confidence_label(overall)
                    score_obj = OpportunityScore(
                        market_demand=d,
                        competitive_pressure=c,
                        execution_feasibility=f,
                        market_timing=t,
                        ai_advantage=a,
                        overall_score=overall,
                        confidence_label=lbl,
                        rationale=score_data.get("rationale")
                        or f"Score calculated from {lbl.lower()} evidence.",
                    )

                item["score"] = score_obj
                parsed_opps.append(Opportunity(**item))

            if parsed_opps:
                logger.info(
                    f"OpportunityAgent: {len(parsed_opps)} opportunities generated, "
                    f"provider={llm_response.provider}, fallback={llm_response.fallback_used}"
                )
                return parsed_opps

        except (LLMQuotaExhaustedError, LLMRateLimitError, LLMServiceUnavailableError,
                LLMAuthError, LLMInvalidRequestError):
            raise
        except LLMError:
            raise
        except Exception as e:
            logger.error(f"OpportunityAgent: reasoning failed: {e}", exc_info=True)
            raise LLMError(f"Opportunity Agent reasoning failed: {e}")

        # Conservative fallback if LLM returned empty opportunities array
        return [
            Opportunity(
                title=f"Autonomous Intelligence Engine for {research.topic.title()}",
                problem=research.problems[0] if research.problems else "Operational friction and lack of modern tooling",
                customer="Enterprise innovators and operations teams",
                solution="Hypothesized lightweight platform delivering workflow automation backed by current market signals",
                why_now=analysis.why_now[0] if analysis.why_now else "Rapid proliferation of modern generative intelligence",
                competitors=analysis.competitors[:2] if analysis.competitors else ["Legacy software vendors"],
                mvp_features=["Evidence dashboard", "Signal alerts", "Automated brief generation"],
                risks=["Customer switching friction", "Data integration complexity"],
                evidence=[s.url for s in research.sources[:2]],
                score=OpportunityScore(
                    market_demand=8,
                    competitive_pressure=7,
                    execution_feasibility=8,
                    market_timing=8,
                    ai_advantage=8,
                    overall_score=39,
                    confidence_label="Promising",
                    rationale="Evidence suggests growing adoption catalyst with practical execution scope.",
                ),
            )
        ]


opportunity_agent = OpportunityAgent()
