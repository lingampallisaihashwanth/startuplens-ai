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
from backend.database.db import db

logger = logging.getLogger(__name__)

PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "research.txt"


class ResearchAgent:
    """
    Research + Market Analysis Agent:
    - Queries Tavily for fresh web research (mandatory).
    - Sends verified sources & documents to the LLM router in ONE structured
      call producing both research extraction and market analysis.
    - Uses ModelRouter so any configured provider can satisfy the request.
    - Fails immediately if web research cannot be completed.
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
            "You are the Research and Market Analysis Agent for StartupLens AI. "
            "Extract structured evidence strictly from the provided real search results and attached documents. "
            "Never invent sources, statistics, funding numbers, company names, or page numbers. "
            "If evidence is insufficient, state 'Insufficient recent evidence found.' "
            "Clearly distinguish between verified facts and analytical interpretations. Return valid JSON only."
        )

    def run(
        self,
        topic: str,
        document_ids: Optional[List[str]] = None,
        model_id: Optional[str] = None,
    ) -> Tuple[ResearchOutput, MarketAnalysisOutput]:
        """
        Executes web research via Tavily followed by a single LLM extraction call.
        Includes attached documents if document_ids are provided.
        Fails immediately if web research cannot be completed.
        """
        logger.info(f"ResearchAgent: starting web-first research for topic: '{topic}'")
        now_iso = datetime.now(timezone.utc).isoformat()

        # Step 1: Tavily web search (MANDATORY)
        if not tavily_service.is_configured():
            raise TavilyServiceError(
                "Current web research could not be completed. Try again when web research is available."
            )

        try:
            web_sources = tavily_service.search(query=topic, max_results=6)
            logger.info(f"Tavily returned {len(web_sources)} sources for: '{topic}'")
        except TavilyServiceError as e:
            logger.error(f"Tavily web research failed: {e}")
            raise TavilyServiceError(
                "Current web research could not be completed. Try again when web research is available."
            )

        if not web_sources:
            logger.warning(f"Tavily returned 0 sources for topic: '{topic}'")
            raise TavilyServiceError(
                "Current web research could not be completed. Try again when web research is available."
            )

        # Step 2: Ingest attached documents from SQLite if requested
        doc_sources: List[Dict[str, Any]] = []
        doc_context_parts: List[str] = []

        if document_ids:
            try:
                uploaded_docs = db.get_documents(doc_ids=document_ids)
                logger.info(f"Loaded {len(uploaded_docs)} attached documents")
                for doc in uploaded_docs:
                    sections = doc.get("sections", [])
                    for sec in sections[:8]:
                        page_ref = sec.get("page_or_section", "Document Section")
                        text_snip = sec.get("text", "")[:500]
                        doc_context_parts.append(
                            f"Document: {doc['filename']} | Reference: {page_ref}\nExcerpt: {text_snip}"
                        )
                    doc_sources.append({
                        "title": doc["filename"],
                        "url": f"document://{doc['id']}/{doc['filename']}",
                        "published_at": doc.get("created_at"),
                        "snippet": f"Attached research document ({doc.get('file_type', '').upper()}): {doc['filename']}",
                        "source_type": "document",
                        "freshness_label": "Document",
                        "page_or_section": f"{len(sections)} sections",
                        "authority": "Internal Document",
                    })
            except Exception as e:
                logger.warning(f"Could not load attached documents: {e}", exc_info=True)

        # Step 3: Format sources for LLM context
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
                f"Snippet: {s.get('snippet', '')[:400]}"
            )
        formatted_sources = "\n\n".join(formatted_sources_list)
        formatted_docs = "\n\n".join(doc_context_parts) if doc_context_parts else "None attached."

        # Step 4: Single LLM call via router
        user_prompt = f"""Topic: {topic}

RETRIEVED FRESH WEB SOURCES (Real, verified live web evidence acquired at {now_iso}):
{formatted_sources}

ATTACHED RESEARCH DOCUMENTS (Internal user-uploaded context):
{formatted_docs}

CRITICAL RESEARCH & EVIDENCE RULES:
1. Ground ALL factual claims strictly in the sources above.
2. PRIORITY: For current or latest market trends, funding, and recent metrics, FRESH WEB EVIDENCE takes absolute priority over attached documents.
3. If citing an attached document, specify the exact filename and page/section reference.
4. Never fabricate citations, page numbers, or statistics.
5. If evidence is insufficient for any trend, problem, or signal, state "Insufficient recent evidence found."
6. Maintain source citations: reference specific Source numbers (e.g. "[Web Source 1]") in market signals and problems.

PART A — FACTUAL RESEARCH EXTRACTION:
- trends: Emerging market/technology trends supported by the sources
- startups: Active startups and companies specifically named in the sources
- problems: Specific customer pain points documented in the sources
- market_signals: Concrete signals (funding, metrics, demand indicators) from the sources

PART B — MARKET ANALYSIS (Analytical Interpretation of the Evidence):
- customer_segments: Identified buyer or user personas experiencing these problems
- competitors: Active incumbents or alternative approaches documented
- market_gaps: Genuine unmet needs or underserved niches
- why_now: Structural, technological, or regulatory catalysts driving adoption today

Return valid JSON with this exact schema:
{{
  "research": {{
    "topic": "{topic}",
    "trends": ["trend 1", "trend 2"],
    "startups": ["startup 1", "startup 2"],
    "problems": ["problem 1", "problem 2"],
    "market_signals": ["signal 1 with source reference", "signal 2"],
    "sources": []
  }},
  "analysis": {{
    "market_signals": ["signal 1", "signal 2"],
    "customer_segments": ["segment 1", "segment 2"],
    "competitors": ["competitor 1", "competitor 2"],
    "market_gaps": ["gap 1", "gap 2"],
    "why_now": ["catalyst 1", "catalyst 2"],
    "trends": ["trend 1"],
    "problems": ["problem 1"]
  }}
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
                task_type="research",
            )
            self.last_execution = {
                "provider": llm_response.provider,
                "model": llm_response.model,
                "fallback_used": llm_response.fallback_used,
                "fallback_reason": llm_response.fallback_reason,
                "latency_ms": llm_response.latency_ms,
            }
            result = llm_response.content

            raw_research = result.get("research", {})
            raw_analysis = result.get("analysis", {})

            combined_sources: List[Dict[str, Any]] = list(web_sources) + doc_sources
            raw_research["sources"] = combined_sources
            raw_research["topic"] = topic
            raw_research["retrieved_at"] = now_iso

            research_output = ResearchOutput(**raw_research)
            analysis_output = MarketAnalysisOutput(**raw_analysis)

            logger.info(
                f"ResearchAgent complete: {len(research_output.trends)} trends, "
                f"{len(research_output.sources)} sources, "
                f"provider={llm_response.provider}, model={llm_response.model}, "
                f"fallback={llm_response.fallback_used}"
            )
            return research_output, analysis_output

        except (LLMQuotaExhaustedError, LLMRateLimitError, LLMServiceUnavailableError,
                LLMAuthError, LLMInvalidRequestError):
            raise
        except LLMError:
            raise
        except Exception as e:
            logger.error(f"ResearchAgent: unexpected failure: {type(e).__name__}: {e}")
            raise LLMError(
                f"Research Agent: reasoning failed — {type(e).__name__}: {e}"
            )


research_agent = ResearchAgent()
