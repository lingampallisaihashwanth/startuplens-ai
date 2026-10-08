import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.tavily_service import (
    TavilyService,
    TavilyServiceError,
    canonicalize_url,
    classify_source_type,
    parse_publication_date,
    compute_freshness_label,
)
from backend.agents.research_agent import ResearchAgent
from backend.schemas.research import ResearchOutput, ResearchSource
from backend.schemas.analysis import MarketAnalysisOutput

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. URL Canonicalization & Duplicate Source Removal
# ---------------------------------------------------------------------------

def test_canonicalize_url_strips_tracking():
    """Verify tracking parameters and trailing slashes are removed."""
    url1 = "https://example.com/robotics/overview/?utm_source=twitter&utm_medium=social"
    url2 = "https://example.com/robotics/overview"
    url3 = "https://example.com/robotics/overview?ref=producthunt&fbclid=123"

    assert canonicalize_url(url1) == "https://example.com/robotics/overview"
    assert canonicalize_url(url2) == "https://example.com/robotics/overview"
    assert canonicalize_url(url3) == "https://example.com/robotics/overview"


def test_duplicate_source_removal_in_tavily_service():
    """Verify identical or tracking-variant URLs and duplicate domain titles are deduplicated."""
    svc = TavilyService(api_key="tvly-mock-test")
    svc._client = MagicMock()
    svc._client.search.return_value = {
        "results": [
            {
                "title": "Figure AI Raises $675M",
                "url": "https://techcrunch.com/2026/02/figure-ai-funding/?utm_source=newsletter",
                "content": "Figure AI secured substantial funding.",
                "published_date": "2026-02-28",
            },
            {
                "title": "Figure AI Raises $675M",
                "url": "https://techcrunch.com/2026/02/figure-ai-funding",  # duplicate canonical URL
                "content": "Figure AI funding details.",
                "published_date": "2026-02-28",
            },
            {
                "title": "Figure AI Raises $675M For Humanoids",  # duplicate domain + title key
                "url": "https://techcrunch.com/2026/02/figure-ai-funding-humanoids",
                "content": "Humanoid robotics overview.",
                "published_date": "2026-02-28",
            },
            {
                "title": "Sanctuary AI Phoenix Updates",
                "url": "https://venturebeat.com/ai/sanctuary-ai-phoenix-2026",
                "content": "New dexterity benchmarks.",
                "published_date": "2026-03-01",
            },
        ]
    }

    results = svc.search(query="Humanoid Robotics", max_results=5)
    assert len(results) == 2
    assert results[0]["title"] == "Figure AI Raises $675M"
    assert results[1]["title"] == "Sanctuary AI Phoenix Updates"


# ---------------------------------------------------------------------------
# 2. Publication Date Handling & Missing Date Safety
# ---------------------------------------------------------------------------

def test_parse_publication_date_iso_and_formatted():
    """Verify standard ISO and formatted date strings parse cleanly."""
    date_str, dt = parse_publication_date("2026-04-15T14:30:00Z")
    assert date_str == "2026-04-15"
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 4

    date_str2, dt2 = parse_publication_date("2025-11-20")
    assert date_str2 == "2025-11-20"
    assert dt2 is not None


def test_missing_published_date_never_fabricates():
    """Verify missing, empty, or unparseable dates return None without fabricating fake dates."""
    date_none, dt_none = parse_publication_date(None)
    assert date_none is None
    assert dt_none is None

    date_empty, dt_empty = parse_publication_date("   ")
    assert date_empty is None
    assert dt_empty is None

    date_invalid, dt_invalid = parse_publication_date("Unknown Date String")
    assert date_invalid is None
    assert dt_invalid is None


# ---------------------------------------------------------------------------
# 3. Freshness vs. Stale / Historical Source Labeling
# ---------------------------------------------------------------------------

def test_stale_source_labeled_as_historical():
    """Verify older sources (> 2.5 years) are marked is_historical=True with historical label."""
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)
    old_date = datetime(2022, 5, 10, tzinfo=timezone.utc)

    label, is_historical = compute_freshness_label(old_date, now_dt=now)
    assert is_historical is True
    assert "Historical context (2022)" in label


def test_recent_source_freshness_relative_labels():
    """Verify recent sources (< 30 days) receive clear relative freshness labels."""
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)

    # 2 days ago
    label_2d, hist_2d = compute_freshness_label(now - timedelta(days=2), now_dt=now)
    assert hist_2d is False
    assert label_2d == "2 days ago"

    # 2 weeks ago
    label_2w, hist_2w = compute_freshness_label(now - timedelta(days=14), now_dt=now)
    assert hist_2w is False
    assert label_2w == "2 weeks ago"

    # Today
    label_today, hist_today = compute_freshness_label(now, now_dt=now)
    assert hist_today is False
    assert label_today == "Today"


# ---------------------------------------------------------------------------
# 4. Source Authority Classification
# ---------------------------------------------------------------------------

def test_source_authority_classification():
    """Verify domain classification into government, research, news, or company."""
    assert classify_source_type("https://www.energy.gov/clean-energy", "Gov Report") == "government"
    assert classify_source_type("https://arxiv.org/abs/2601.12345", "Paper Title") == "research_institution"
    assert classify_source_type("https://techcrunch.com/article", "TechCrunch News") == "industry_publication"
    assert classify_source_type("https://figure.ai/blog/dexterity", "Figure AI Blog") == "official_company"
    assert classify_source_type("https://general-domain.com/overview", "General Page") == "web"


# ---------------------------------------------------------------------------
# 5. Time-Sensitive Query Prioritization
# ---------------------------------------------------------------------------

def test_time_sensitive_query_triggers_news_and_temporal_expansion():
    """Verify that temporal keywords like 'latest' or 'recent' trigger news topic mode in Tavily."""
    svc = TavilyService(api_key="tvly-mock-test")
    svc._client = MagicMock()
    svc._client.search.return_value = {"results": []}

    svc.search(query="latest AI robotics developments", max_results=5)
    call_kwargs = svc._client.search.call_args[1]
    assert call_kwargs["topic"] == "news"


# ---------------------------------------------------------------------------
# 6. Tavily Failure Behavior — Strict Prohibition on Model Memory Fallback
# ---------------------------------------------------------------------------

def test_tavily_failure_returns_503_and_does_not_hallucinate():
    """
    Requirement 15: If Tavily fails, do NOT generate a report using Gemini memory alone.
    Return HTTP 503 with exact specified message.
    """
    with patch("backend.services.tavily_service.tavily_service.is_configured", return_value=True), \
         patch("backend.services.tavily_service.tavily_service.search", side_effect=TavilyServiceError("Tavily unreachable")):

        response = client.post("/analyze", json={"topic": "Quantum Computing Startups"})
        assert response.status_code == 503
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "WEB_RESEARCH_FAILED"
        assert "Current web research could not be completed. Try again when web research is available." in data["error"]["message"]


def test_tavily_zero_sources_returns_503():
    """Verify that if Tavily returns 0 sources, system halts rather than fabricating data."""
    with patch("backend.services.tavily_service.tavily_service.is_configured", return_value=True), \
         patch("backend.services.tavily_service.tavily_service.search", return_value=[]):

        response = client.post("/analyze", json={"topic": "Obscure Rare Topic Zero Sources"})
        assert response.status_code == 503
        data = response.json()
        assert data["error"]["code"] == "WEB_RESEARCH_FAILED"


# ---------------------------------------------------------------------------
# 7. Research Timestamp & Freshness Disclaimer in API Responses
# ---------------------------------------------------------------------------

def test_analyze_response_contains_retrieved_at_and_disclaimer():
    """Verify that AnalyzeResponse includes retrieved_at and the required freshness disclaimer."""
    mock_sources = [
        {
            "title": "Robotics Today 2026",
            "url": "https://example.com/robotics",
            "snippet": "Advances in robotic manipulation.",
            "published_at": "2026-03-01",
            "source_type": "industry_publication",
            "retrieved_at": "2026-10-06T12:00:00Z",
            "freshness_label": "7 months ago",
            "is_historical": False,
        }
    ]

    mock_research_output = ResearchOutput(
        topic="Robotics",
        trends=["VLA foundation models"],
        startups=["Figure AI"],
        problems=["Calibration overhead"],
        market_signals=["$675M funding"],
        sources=[ResearchSource(**mock_sources[0])],
        retrieved_at="2026-10-06T12:00:00Z",
    )

    mock_analysis_output = MarketAnalysisOutput(
        market_signals=["Industrial pilot demand"],
        customer_segments=["Automotive logistics"],
        competitors=["Figure AI", "Boston Dynamics"],
        market_gaps=["Unified teleoperation portal"],
        why_now=["Commoditized actuators"],
    )

    with patch("backend.agents.research_agent.research_agent.run", return_value=(mock_research_output, mock_analysis_output)), \
         patch("backend.agents.opportunity_agent.opportunity_agent.run", return_value=[]):

        response = client.post("/analyze", json={"topic": "Robotics"})
        assert response.status_code == 200
        data = response.json()

        assert "retrieved_at" in data
        assert data["retrieved_at"] is not None
        assert "research_disclaimer" in data
        assert "Based on web sources retrieved on" in data["research_disclaimer"]
        assert len(data["sources"]) == 1
        assert data["sources"][0]["freshness_label"] == "7 months ago"
        assert data["sources"][0]["is_historical"] is False
