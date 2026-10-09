import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.intent_service import intent_service, IntentType
from backend.schemas.company_analysis import CompanyAnalysisOutput
from backend.schemas.research import ResearchOutput, ResearchSource
from backend.schemas.analysis import MarketAnalysisOutput

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Unit Tests for Intent Classification
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "query",
    [
        "hi",
        "hey",
        "heyy",
        "hello",
        "good morning",
        "what's up",
        "thanks",
        "thank you",
        "okay",
        "bye",
        "Hello!",
        "Heyy there",
        "Thanks so much",
    ],
)
def test_casual_chat_intent_detection(query: str):
    result = intent_service.detect_intent(query)
    assert result.intent == IntentType.CASUAL_CHAT


@pytest.mark.parametrize(
    "query, expected_company",
    [
        ("Why did Byju's fail?", "Byju's"),
        ("How did Airbnb grow?", "Airbnb"),
        ("Why did WeWork decline?", "WeWork"),
        ("How did Zerodha become successful?", "Zerodha"),
        ("Analyze Nokia's rise and decline.", "Nokia"),
        ("Byju's", "Byju's"),
        ("Airbnb", "Airbnb"),
    ],
)
def test_company_analysis_intent_detection(query: str, expected_company: str):
    result = intent_service.detect_intent(query)
    assert result.intent == IntentType.COMPANY_ANALYSIS
    assert result.company_name is not None
    assert (
        expected_company.lower() in result.company_name.lower()
        or result.company_name.lower() in expected_company.lower()
    )


@pytest.mark.parametrize(
    "query",
    [
        ("AI robotics market trends"),
        ("Analyze the healthcare AI market"),
        ("Find competitors of Tesla"),
        ("What are the latest trends in AI agents?"),
        ("autonomous drones market"),
    ],
)
def test_market_research_intent_detection(query: str):
    result = intent_service.detect_intent(query)
    assert result.intent == IntentType.MARKET_RESEARCH


@pytest.mark.parametrize(
    "query",
    [
        ("Find startup opportunities"),
        ("Give me startup ideas"),
        ("What business can I build in AI healthcare?"),
        ("Give me startup ideas in AI healthcare"),
        ("startup opportunities in clean energy"),
    ],
)
def test_startup_opportunity_intent_detection(query: str):
    result = intent_service.detect_intent(query)
    assert result.intent == IntentType.STARTUP_OPPORTUNITY_RESEARCH


# ---------------------------------------------------------------------------
# 2. Integration Tests: POST /chat with Casual Messages
# ---------------------------------------------------------------------------

@patch("backend.services.tavily_service.TavilyService.search")
def test_chat_casual_zero_tavily_called(mock_tavily_search):
    """Verify casual messages do NOT call Tavily, do NOT call /analyze, and return instant natural reply."""
    casual_queries = ["hi", "heyy", "hello", "thanks", "good morning", "bye"]

    for query in casual_queries:
        mock_tavily_search.reset_mock()
        resp = client.post("/chat", json={"message": query})
        assert resp.status_code == 200, f"Failed on query: {query}"
        data = resp.json()

        assert data["intent"] == "CASUAL_CHAT"
        assert len(data["reply"]) > 0
        assert "research" in data["reply"].lower() or "ask" in data["reply"].lower()
        assert data["session_id"] is None
        assert data["data"] is None

        # Critical: Tavily must NEVER be called
        mock_tavily_search.assert_not_called()


# ---------------------------------------------------------------------------
# 3. Integration Tests: POST /chat with Company Analysis
# ---------------------------------------------------------------------------

def test_chat_company_analysis_flow():
    """Verify company queries trigger Company Analysis mode with all 19 dimensions and evidence breakdown."""
    from backend.services.tavily_service import TavilyService
    from backend.llm.base import LLMResponse

    mock_tavily_results = [
        {
            "title": "Byjus Fall Explained",
            "url": "https://example.com/byjus-fall",
            "snippet": "Byju's faced aggressive acquisitions and severe debt issues.",
            "source_type": "article",
            "published_at": "2024-01-15T00:00:00Z",
            "freshness_label": "Recent",
            "is_historical": False,
        }
    ]

    company_payload = {
        "company_analysis": {
            "company_name": "Byju's",
            "overview": "EdTech giant providing personalized K-12 learning.",
            "founding_story": "Founded in 2011 by Byju Raveendran and Divya Gokulnath.",
            "original_problem": "Lack of engaging visual learning materials for students.",
            "business_model": "Freemium subscription app bundled with hardware tablets.",
            "target_customers": ["K-12 students", "Parents in tier 1 and tier 2 Indian cities"],
            "early_growth": "Rapid adoption fueled by offline coaching seminars.",
            "growth_strategy": "Aggressive debt-financed global M&A spree.",
            "funding_and_expansion": "Raised over $5 billion from major sovereign and venture funds.",
            "major_milestones": ["Launched tablet app in 2015", "Became decacorn in 2020"],
            "growth_drivers": ["COVID-19 remote learning surge", "Aggressive field sales force"],
            "turning_points": ["Reopening of physical schools in 2022", "Default on $1.2B term loan"],
            "warning_signs": ["Auditor resignations (Deloitte)", "Delayed financial statements"],
            "competition": ["PhysicsWallah", "Khan Academy", "Unacademy"],
            "market_changes": ["Post-pandemic return to offline classrooms", "Edtech capital freeze"],
            "strategic_mistakes": ["Overpriced acquisitions like WhiteHat Jr", "Aggressive mis-selling"],
            "financial_problems": ["Severe liquidity crunch", "Debt covenants breached"],
            "reasons_for_decline_or_failure": [
                "Over-leveraged capital structure",
                "Governance and financial reporting breakdown",
                "Unsustainable sales practices",
            ],
            "current_status": "Under insolvency proceedings and restructuring.",
            "lessons_for_founders": [
                "Focus on unit economics and cash flow over vanity valuation.",
                "Maintain rigorous corporate governance and independent audits.",
            ],
            "facts": [
                "Raised over $5B in funding between 2016 and 2022.",
                "Auditor Deloitte resigned in June 2023 over delayed financial statements.",
            ],
            "inferences": [
                "Debt-funded expansion proved fatal once organic cash flows reversed post-COVID.",
            ],
            "hypotheses": [
                "Had Byju's focused strictly on domestic organic growth, it would have remained solvent.",
            ],
        },
        "research": {
            "topic": "Why did Byju's fail?",
            "trends": ["Shift to hybrid education"],
            "startups": ["Byju's", "PhysicsWallah"],
            "problems": ["High student acquisition cost"],
            "market_signals": ["Insolvency filings in NCLT"],
            "sources": [],
        },
        "analysis": {
            "market_signals": ["Insolvency filings"],
            "customer_segments": ["K-12 students"],
            "competitors": ["PhysicsWallah", "Unacademy"],
            "market_gaps": ["Affordable test prep"],
            "why_now": ["Post-COVID normalization"],
            "trends": ["Shift to hybrid education"],
            "problems": ["High student acquisition cost"],
        },
    }

    mock_llm_response = LLMResponse(
        content=company_payload,
        provider="Google Gemini",
        model="gemini-2.5-flash",
        latency_ms=1200,
    )

    with patch.object(TavilyService, "is_configured", return_value=True), \
         patch.object(TavilyService, "search", return_value=mock_tavily_results), \
         patch("backend.llm.router.ModelRouter.generate_json", return_value=mock_llm_response):

        resp = client.post("/chat", json={"message": "Why did Byju's fail?"})

    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] == "COMPANY_ANALYSIS"
    assert data["data"] is not None
    assert data["session_id"] is not None

    company_analysis = data["data"]["company_analysis"]
    assert company_analysis is not None
    assert company_analysis["company_name"] == "Byju's"
    assert "Deloitte" in str(company_analysis["facts"])
    assert len(company_analysis["lessons_for_founders"]) >= 2
    assert len(company_analysis["facts"]) >= 1
    assert len(company_analysis["inferences"]) >= 1
    assert len(company_analysis["hypotheses"]) >= 1

    # Opportunities should NOT be generated for pure company analysis
    assert len(data["data"]["opportunities"]) == 0


# ---------------------------------------------------------------------------
# 4. Backward Compatibility: POST /analyze
# ---------------------------------------------------------------------------

def test_analyze_backward_compatible_market_research():
    """Verify that legacy /analyze endpoint still functions smoothly for market research."""
    from backend.services.tavily_service import TavilyService
    from backend.llm.base import LLMResponse

    mock_tavily = [
        {
            "title": "Robotics Market Growth",
            "url": "https://example.com/robotics",
            "snippet": "AI robotics market growing at 32% CAGR.",
            "source_type": "report",
            "published_at": "2024-01-15T00:00:00Z",
            "freshness_label": "Recent",
            "is_historical": False,
        }
    ]

    research_payload = {
        "trends": ["Humanoid robots in warehousing"],
        "startups": ["Figure AI", "Boston Dynamics"],
        "problems": ["High hardware costs"],
        "market_signals": ["$675M Series B funding announced"],
        "customer_segments": ["Warehouse operators"],
        "competitors": ["Legacy automation providers"],
        "market_gaps": ["Affordable perception software"],
        "why_now": ["Foundation vision-language-action models"],
    }

    opp_payload = {
        "opportunities": [
            {
                "title": "RoboOps AI",
                "problem": "Robots fail in unstructured environments",
                "customer": "Warehouse automation directors",
                "solution": "Fine-tuned VLA perception API",
                "why_now": "Open-source robotics models released in 2024",
                "competitors": ["Covariant"],
                "mvp_features": ["Edge model container", "Teleoperation fallback"],
                "risks": ["Sensor latency"],
                "evidence": ["Warehouse operators report 40% downtime"],
                "score": {
                    "market_demand": 8,
                    "competitive_pressure": 7,
                    "execution_feasibility": 8,
                    "market_timing": 9,
                    "ai_advantage": 9,
                    "overall_score": 41,
                    "confidence_label": "High Conviction",
                    "rationale": "Strong timing with modern VLA models.",
                },
            }
        ]
    }

    call_count = [0]

    def mock_generate_json(request, model_id=None, task_type=None):
        call_count[0] += 1
        content = research_payload if call_count[0] == 1 else opp_payload
        return LLMResponse(
            content=content,
            provider="Google Gemini",
            model="gemini-2.5-flash",
            latency_ms=900,
        )

    with patch.object(TavilyService, "is_configured", return_value=True), \
         patch.object(TavilyService, "search", return_value=mock_tavily), \
         patch("backend.llm.router.ModelRouter.generate_json", side_effect=mock_generate_json):

        resp = client.post("/analyze", json={"topic": "AI robotics market trends"})

    assert resp.status_code == 200
    data = resp.json()

    assert data["topic"] == "AI robotics market trends"
    assert len(data["opportunities"]) == 1
    assert data["opportunities"][0]["title"] == "RoboOps AI"
    assert data["company_analysis"] is None

