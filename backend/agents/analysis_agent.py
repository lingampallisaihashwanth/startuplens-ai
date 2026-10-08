"""
Market Analysis Agent — MERGED into ResearchAgent (research_agent.py).

The research_agent.run() method now returns (ResearchOutput, MarketAnalysisOutput)
in a single LLM call, reducing API usage from 3 calls to 2 per /analyze request.

This module is retained for import compatibility and future standalone use.
"""
import logging
from backend.schemas.research import ResearchOutput
from backend.schemas.analysis import MarketAnalysisOutput

logger = logging.getLogger(__name__)


class AnalysisAgent:
    """
    Stub — logic merged into ResearchAgent to reduce LLM API calls.
    Kept for import compatibility with existing tests.
    """
    pass


analysis_agent = AnalysisAgent()
