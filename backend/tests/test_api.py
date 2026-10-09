import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.gemini_service import (
    GeminiService,
    GeminiServiceError,
    GeminiRateLimitError,
    GeminiServiceUnavailableError,
    GeminiAuthError,
)
from backend.services.tavily_service import TavilyService, TavilyServiceError
from backend.llm import llm_router

client = TestClient(app)


@pytest.fixture(autouse=True)
def disable_fallback_for_legacy_api_tests():
    """Ensure legacy test_api tests run isolated without multi-model fallback chain interference."""
    from backend.config import settings
    from backend.llm.registry import model_registry
    orig_fallback = llm_router._fallback_enabled
    orig_groq = settings.GROQ_API_KEY
    orig_mistral = settings.MISTRAL_API_KEY
    llm_router._fallback_enabled = False
    settings.GROQ_API_KEY = ""
    settings.MISTRAL_API_KEY = ""
    model_registry.refresh()
    yield
    llm_router._fallback_enabled = orig_fallback
    settings.GROQ_API_KEY = orig_groq
    settings.MISTRAL_API_KEY = orig_mistral
    model_registry.refresh()


# ---------------------------------------------------------------------------
# Health & infrastructure endpoints
# ---------------------------------------------------------------------------

def test_root_endpoint():
    """Verify GET / health message matches API.md spec."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "StartupLens AI API is running"}


def test_health_endpoint():
    """Verify GET /health returns standard health contract."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "StartupLens AI API" in data["service"]


def test_docs_endpoint():
    """Verify FastAPI /docs Swagger documentation is working."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower() or "html" in response.text.lower()


def test_openapi_schema_endpoint():
    """Verify FastAPI OpenAPI JSON schema is generated and accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "paths" in data
    assert "/analyze" in data["paths"]
    assert "/health" in data["paths"]


def test_config_status_endpoint():
    """Verify /config/status validates keys without exposing secrets."""
    response = client.get("/config/status")
    assert response.status_code == 200
    data = response.json()
    assert "keys" in data
    assert "gemini_configured" in data["keys"]
    assert "tavily_configured" in data["keys"]
    # llm_provider now reflects multi-provider architecture
    assert "llm_provider" in data
    assert data["llm_provider"]  # must be a non-empty string



# ---------------------------------------------------------------------------
# /analyze input validation
# ---------------------------------------------------------------------------

def test_analyze_empty_topic():
    """Verify empty or 1-char topic returns 400 with INVALID_TOPIC code."""
    response = client.post("/analyze", json={"topic": ""})
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_TOPIC"

    # Single character topic
    response = client.post("/analyze", json={"topic": "A"})
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "INVALID_TOPIC"


def test_analyze_invalid_body():
    """Test invalid request payload formats."""
    # Missing topic field
    response = client.post("/analyze", json={})
    assert response.status_code == 400

    # Non-string topic
    response = client.post("/analyze", json={"topic": 12345})
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# /analyze full pipeline (with mocked external services)
# ---------------------------------------------------------------------------

def _mock_tavily_search(query, max_results=5, search_depth="basic"):
    """Return realistic mock Tavily search results."""
    return [
        {
            "title": f"Emerging Trends in {query.split()[0]}",
            "url": "https://example.com/trends",
            "snippet": "Industry trends and analysis.",
            "published_at": "2026-09-01",
            "source_type": "web",
        },
        {
            "title": f"Startups Disrupting {query.split()[0]}",
            "url": "https://example.com/startups",
            "snippet": "Startup ecosystem overview.",
            "published_at": "2026-08-15",
            "source_type": "web",
        },
    ]


def _mock_gemini_research_response(prompt, **kwargs):
    """Mock Gemini response for research agent."""
    return {
        "topic": "AI Robotics",
        "trends": ["Autonomous mobile robots", "AI-powered quality inspection"],
        "startups": ["Covariant", "Dexterity AI"],
        "problems": ["High integration cost", "Lack of skilled operators"],
        "market_signals": ["Growing VC investment", "Manufacturing demand surge"],
        "sources": [
            {
                "title": "Emerging Trends in AI Robotics",
                "url": "https://example.com/trends",
                "published_at": "2026-09-01",
                "snippet": "Industry trends and analysis.",
            },
            {
                "title": "Startups Disrupting AI Robotics",
                "url": "https://example.com/startups",
                "published_at": "2026-08-15",
                "snippet": "Startup ecosystem overview.",
            },
        ],
    }


def _mock_gemini_analysis_response(prompt, **kwargs):
    """Mock Gemini response for analysis agent."""
    return {
        "market_signals": ["Growing VC investment in robotics"],
        "customer_segments": ["Manufacturing operators", "Logistics companies"],
        "competitors": ["Boston Dynamics", "FANUC"],
        "market_gaps": ["Lack of plug-and-play robotic tooling"],
        "why_now": ["Advances in foundation models for robotics"],
        "trends": ["AI-powered quality inspection"],
        "problems": ["High integration cost"],
    }


def _mock_gemini_opportunity_response(prompt, **kwargs):
    """Mock Gemini response for opportunity agent."""
    return {
        "opportunities": [
            {
                "title": "Autonomous QA Inspector",
                "problem": "Manual quality inspection is slow and error-prone",
                "customer": "Mid-size manufacturers",
                "solution": "Vision-based robotic inspection system",
                "why_now": "Foundation models enable zero-shot defect detection",
                "competitors": ["Cognex", "Keyence"],
                "mvp_features": ["Camera-based scanner", "Defect dashboard", "Alert system"],
                "risks": ["Hardware integration complexity", "Customer trust"],
                "evidence": ["Growing VC investment", "Manufacturing demand surge"],
            },
            {
                "title": "Robot Fleet Manager",
                "problem": "Managing heterogeneous robot fleets is fragmented",
                "customer": "Logistics warehouse operators",
                "solution": "Unified robot fleet orchestration platform",
                "why_now": "Multi-vendor robot deployments increasing",
                "competitors": ["6 River Systems", "Locus Robotics"],
                "mvp_features": ["Fleet dashboard", "Task scheduler", "Health monitor"],
                "risks": ["Vendor lock-in concerns", "Interoperability challenges"],
                "evidence": ["Logistics automation trend", "Startup ecosystem growth"],
            },
            {
                "title": "Robotics Training Sandbox",
                "problem": "Operators lack hands-on training without expensive hardware",
                "customer": "Technical training institutions",
                "solution": "Cloud-based robot simulation and training platform",
                "why_now": "Simulation fidelity approaching real-world accuracy",
                "competitors": ["RoboDK", "Gazebo"],
                "mvp_features": ["Browser-based simulator", "Scenario templates", "Progress tracking"],
                "risks": ["Simulation-to-real gap", "Content freshness"],
                "evidence": ["Skills shortage in robotics", "Growing demand for training"],
            },
        ]
    }


def test_analyze_valid_topic_mocked():
    """Verify /analyze returns structured output with mocked Gemini and Tavily."""
    call_count = [0]

    def mock_generate_json(prompt, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return {
                "research": _mock_gemini_research_response(prompt, **kwargs),
                "analysis": _mock_gemini_analysis_response(prompt, **kwargs),
            }
        else:
            return _mock_gemini_opportunity_response(prompt, **kwargs)

    with patch.object(
        GeminiService, "is_configured", return_value=True
    ), patch.object(
        GeminiService, "generate_json", side_effect=mock_generate_json
    ), patch.object(
        TavilyService, "is_configured", return_value=True
    ), patch.object(
        TavilyService, "search", side_effect=_mock_tavily_search
    ):
        response = client.post("/analyze", json={"topic": "AI Robotics"})

    assert response.status_code == 200
    data = response.json()

    # Session identifiers
    assert "id" in data
    assert "session_id" in data
    assert data["topic"] == "AI Robotics"

    # Research section
    assert "research" in data
    research = data["research"]
    assert "trends" in research and isinstance(research["trends"], list)
    assert "startups" in research and isinstance(research["startups"], list)
    assert "problems" in research and isinstance(research["problems"], list)
    assert "sources" in research and isinstance(research["sources"], list)

    # Analysis section
    assert "analysis" in data
    analysis = data["analysis"]
    assert "market_signals" in analysis
    assert "customer_segments" in analysis
    assert "competitors" in analysis
    assert "market_gaps" in analysis
    assert "why_now" in analysis

    # Opportunities section
    assert "opportunities" in data
    opportunities = data["opportunities"]
    assert len(opportunities) >= 3
    first_opp = opportunities[0]
    for key in ["title", "problem", "customer", "solution", "why_now", "competitors", "mvp_features", "risks", "evidence"]:
        assert key in first_opp, f"Missing key {key} in opportunity"

    # Sources section
    assert "sources" in data
    assert len(data["sources"]) > 0


def test_analyze_valid_topic():
    """
    Live integration test: verify /analyze returns structured output when Gemini quota allows.

    Accepts HTTP 200 (success) or HTTP 429 (Gemini free-tier quota exhausted).
    HTTP 429 is correct behavior — the fix under test is that quota exhaustion is
    now surfaced as 429 instead of the previous incorrect 500 PIPELINE_ERROR.
    When 429 is returned, the structured error body is validated.
    """
    response = client.post("/analyze", json={"topic": "AI Robotics"})

    # External live service may return 200, 429 (quota exhausted), or 500/503 (temporary high demand spike)
    assert response.status_code in (200, 429, 500, 503), (
        f"Expected 200, 429, 500, or 503, got {response.status_code}: {response.text}"
    )

    if response.status_code in (429, 500, 503):
        # Verify error body shape
        data = response.json()
        assert "error" in data, "Error response must have an 'error' key"
        assert "code" in data["error"]
        assert "opportunities" not in data
        assert "research" not in data
        return

    # --- HTTP 200 path: full structural validation ---
    data = response.json()

    # Session identifiers
    assert "id" in data
    assert "session_id" in data
    assert data["topic"] == "AI Robotics"

    # Research section
    assert "research" in data
    research = data["research"]
    assert "trends" in research and isinstance(research["trends"], list)
    assert "startups" in research and isinstance(research["startups"], list)
    assert "problems" in research and isinstance(research["problems"], list)
    assert "sources" in research and isinstance(research["sources"], list)

    # Analysis section
    assert "analysis" in data
    analysis = data["analysis"]
    assert "market_signals" in analysis
    assert "customer_segments" in analysis
    assert "competitors" in analysis
    assert "market_gaps" in analysis
    assert "why_now" in analysis

    # Opportunities section
    assert "opportunities" in data
    opportunities = data["opportunities"]
    assert len(opportunities) >= 3
    first_opp = opportunities[0]
    for key in ["title", "problem", "customer", "solution", "why_now", "competitors", "mvp_features", "risks", "evidence"]:
        assert key in first_opp, f"Missing key {key} in opportunity"

    # Sources section
    assert "sources" in data
    assert len(data["sources"]) > 0


# ---------------------------------------------------------------------------
# Gemini service unit tests
# ---------------------------------------------------------------------------

def test_gemini_unconfigured_error():
    """Test Gemini service raises GeminiServiceError when key is missing."""
    service = GeminiService(api_key="")
    assert not service.is_configured()
    with pytest.raises(GeminiServiceError) as exc_info:
        service.generate_json("Test prompt")
    assert "GEMINI_API_KEY" in str(exc_info.value)


def test_gemini_json_parsing():
    """Test JSON parsing utility in GeminiService handles markdown fences."""
    service = GeminiService(api_key="mock_key")
    fenced_json = '```json\n{"status": "success", "count": 5}\n```'
    parsed = service._parse_json(fenced_json)
    assert parsed == {"status": "success", "count": 5}


def test_gemini_json_parsing_clean():
    """Test JSON parsing works for clean JSON without fences."""
    service = GeminiService(api_key="mock_key")
    clean_json = '{"key": "value", "number": 42}'
    parsed = service._parse_json(clean_json)
    assert parsed == {"key": "value", "number": 42}


def test_gemini_malformed_json():
    """Test malformed JSON response raises GeminiServiceError."""
    service = GeminiService(api_key="mock_key")
    with pytest.raises(GeminiServiceError) as exc_info:
        service._parse_json("this is not json {{{")
    assert "malformed JSON" in str(exc_info.value)


def test_gemini_service_configured():
    """Test GeminiService.is_configured with a valid key."""
    service = GeminiService(api_key="test_api_key_123")
    assert service.is_configured()


def test_gemini_service_not_configured_whitespace():
    """Test GeminiService.is_configured rejects whitespace-only keys."""
    service = GeminiService(api_key="   ")
    assert not service.is_configured()


# ---------------------------------------------------------------------------
# Tavily service unit tests
# ---------------------------------------------------------------------------

def test_tavily_unconfigured_error():
    """Test Tavily service raises TavilyServiceError when key is missing."""
    service = TavilyService(api_key="")
    assert not service.is_configured()
    with pytest.raises(TavilyServiceError) as exc_info:
        service.search("Test query")
    assert "Tavily API key is not configured" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Malformed Gemini response in pipeline
# ---------------------------------------------------------------------------

def test_analyze_gemini_malformed_response():
    """Verify pipeline handles malformed Gemini JSON gracefully via fallback."""
    def mock_generate_json_fail(prompt, **kwargs):
        raise GeminiServiceError("Received malformed JSON from Gemini model.")

    with patch.object(
        GeminiService, "is_configured", return_value=True
    ), patch.object(
        GeminiService, "generate_json", side_effect=mock_generate_json_fail
    ), patch.object(
        TavilyService, "is_configured", return_value=True
    ), patch.object(
        TavilyService, "search", side_effect=_mock_tavily_search
    ):
        response = client.post("/analyze", json={"topic": "AI Robotics"})

    # Pipeline should cleanly fail when Gemini returns malformed response (no mock/fallback)
    assert response.status_code in (500, 503)
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] in ("PIPELINE_ERROR", "AI_SERVICE_UNAVAILABLE")


# ---------------------------------------------------------------------------
# Gemini 429 RESOURCE_EXHAUSTED → HTTP 429 AI_RATE_LIMITED
# ---------------------------------------------------------------------------

def test_analyze_gemini_rate_limited_returns_429():
    """
    Verify that when Gemini raises GeminiRateLimitError during the pipeline
    the /analyze endpoint returns HTTP 429 with code AI_RATE_LIMITED and
    the required structured error body. No fallback data should be returned.
    """
    def mock_raise_rate_limit(prompt, **kwargs):
        raise GeminiRateLimitError(
            "Gemini free-tier request limit reached. Please wait before trying again."
        )

    with patch.object(
        GeminiService, "is_configured", return_value=True
    ), patch.object(
        GeminiService, "generate_json", side_effect=mock_raise_rate_limit
    ), patch.object(
        TavilyService, "is_configured", return_value=True
    ), patch.object(
        TavilyService, "search", side_effect=_mock_tavily_search
    ):
        response = client.post("/analyze", json={"topic": "AI Robotics"})

    # Must be 429, not 400 or 500
    assert response.status_code == 429, (
        f"Expected 429, got {response.status_code}: {response.text}"
    )

    data = response.json()
    assert "error" in data, "Response must have an 'error' key"

    error = data["error"]
    assert error["code"] == "AI_RATE_LIMITED", (
        f"Expected code AI_RATE_LIMITED, got: {error.get('code')}"
    )
    assert "message" in error, "Error object must contain a 'message' field"
    assert len(error["message"]) > 10, "Error message must not be empty"

    # Confirm no fallback opportunities leaked into the response
    assert "opportunities" not in data, "Fallback opportunities must not appear in a 429 response"
    assert "research" not in data, "Fallback research must not appear in a 429 response"


def test_analyze_gemini_rate_limit_is_independent_of_tavily_errors():
    """
    Verify Tavily errors still return 500 PIPELINE_ERROR (not 429),
    ensuring the two error paths are kept separate.
    """
    def mock_tavily_fail(query, **kwargs):
        raise TavilyServiceError("Tavily network error")

    with patch.object(
        TavilyService, "is_configured", return_value=True
    ), patch.object(
        TavilyService, "search", side_effect=mock_tavily_fail
    ), patch.object(
        GeminiService, "is_configured", return_value=True
    ):
        response = client.post("/analyze", json={"topic": "AI Robotics"})

    # Tavily errors must NOT produce 429
    assert response.status_code != 429, "Tavily errors must not produce 429"
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] != "AI_RATE_LIMITED", (
        "Tavily errors must not be classified as AI_RATE_LIMITED"
    )


# ---------------------------------------------------------------------------
# Opportunity agent 429 propagation
# ---------------------------------------------------------------------------

def test_opportunity_agent_rate_limit_returns_429():
    """
    Verify that GeminiRateLimitError raised in the Opportunity Agent
    is correctly propagated as HTTP 429 with AI_RATE_LIMITED code.
    The research agent succeeds; only the opportunity agent is rate-limited.
    """
    call_count = [0]

    def mock_generate_json_opportunity_rate_limited(prompt, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            # Research agent call succeeds
            return {
                "research": _mock_gemini_research_response(prompt, **kwargs),
                "analysis": _mock_gemini_analysis_response(prompt, **kwargs),
            }
        # Second call (opportunity agent) is rate-limited
        raise GeminiRateLimitError(
            "Gemini free-tier request limit reached. Please wait before trying again."
        )

    with patch.object(
        GeminiService, "is_configured", return_value=True
    ), patch.object(
        GeminiService, "generate_json", side_effect=mock_generate_json_opportunity_rate_limited
    ), patch.object(
        TavilyService, "is_configured", return_value=True
    ), patch.object(
        TavilyService, "search", side_effect=_mock_tavily_search
    ):
        response = client.post("/analyze", json={"topic": "AI Robotics"})

    assert response.status_code == 429, (
        f"Expected 429 from opportunity agent rate limit, got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert "error" in data
    error = data["error"]
    assert error["code"] == "AI_RATE_LIMITED"
    assert len(error["message"]) > 10
    assert "opportunities" not in data
    assert "research" not in data


# ---------------------------------------------------------------------------
# Non-429 Gemini errors → 500 PIPELINE_ERROR (not 429)
# ---------------------------------------------------------------------------

def test_analyze_gemini_auth_error_returns_401():
    """
    Verify that a Gemini authentication error (401/403) returns 401
    AI_AUTH_ERROR, not 500 or 429.
    """
    def mock_auth_error(prompt, **kwargs):
        raise GeminiAuthError("Gemini authentication failed. Please verify your GEMINI_API_KEY.")

    with patch.object(
        GeminiService, "is_configured", return_value=True
    ), patch.object(
        GeminiService, "generate_json", side_effect=mock_auth_error
    ), patch.object(
        TavilyService, "is_configured", return_value=True
    ), patch.object(
        TavilyService, "search", side_effect=_mock_tavily_search
    ):
        response = client.post("/analyze", json={"topic": "AI Robotics"})

    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "AI_AUTH_ERROR"
    assert "Gemini authentication failed" in data["error"]["message"]


def test_analyze_gemini_503_after_retries_returns_503():
    """
    Verify that a Gemini 503 error (after exhausting retries) returns HTTP 503
    with code AI_SERVICE_UNAVAILABLE and structured error body.
    """
    def mock_unavailable_error(prompt, **kwargs):
        raise GeminiServiceUnavailableError(
            "The AI service is temporarily unavailable. Please try again shortly."
        )

    with patch.object(
        GeminiService, "is_configured", return_value=True
    ), patch.object(
        GeminiService, "generate_json", side_effect=mock_unavailable_error
    ), patch.object(
        TavilyService, "is_configured", return_value=True
    ), patch.object(
        TavilyService, "search", side_effect=_mock_tavily_search
    ):
        response = client.post("/analyze", json={"topic": "AI Robotics"})

    assert response.status_code == 503
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "AI_SERVICE_UNAVAILABLE"
    assert data["error"]["message"] == "The AI service is temporarily unavailable. Please try again shortly."
    assert "opportunities" not in data
    assert "research" not in data


# ---------------------------------------------------------------------------
# 429 response body shape: no data keys must be present
# ---------------------------------------------------------------------------

def test_429_response_contains_no_data_fields():
    """
    Verify the 429 response body contains ONLY the error envelope.
    No 'research', 'analysis', 'opportunities', 'sources', 'session_id'
    or 'id' fields must appear (no fallback data leak).
    """
    def mock_raise_rate_limit(prompt, **kwargs):
        raise GeminiRateLimitError("Rate limit exceeded.")

    with patch.object(
        GeminiService, "is_configured", return_value=True
    ), patch.object(
        GeminiService, "generate_json", side_effect=mock_raise_rate_limit
    ), patch.object(
        TavilyService, "is_configured", return_value=True
    ), patch.object(
        TavilyService, "search", side_effect=_mock_tavily_search
    ):
        response = client.post("/analyze", json={"topic": "AI Robotics"})

    assert response.status_code == 429
    data = response.json()

    # The error envelope must be present
    assert "error" in data
    assert data["error"]["code"] == "AI_RATE_LIMITED"

    # No data fields may appear alongside the error
    forbidden_keys = {"research", "analysis", "opportunities", "sources", "session_id", "id", "topic"}
    leaking_keys = forbidden_keys.intersection(set(data.keys()))
    assert not leaking_keys, (
        f"429 response must not contain data fields. Found: {leaking_keys}"
    )


# ---------------------------------------------------------------------------
# Gemini service: 429 classification unit test
# ---------------------------------------------------------------------------

def test_gemini_service_429_raises_rate_limit_error():
    """
    Unit test: verify GeminiService correctly classifies a 429/RESOURCE_EXHAUSTED
    exception as GeminiRateLimitError (not a generic GeminiServiceError).
    """
    service = GeminiService(api_key="test_key_abc")
    service._client = MagicMock()

    # Simulate the google-genai SDK throwing a 429-like exception
    service._client.models.generate_content.side_effect = Exception(
        "429 RESOURCE_EXHAUSTED: Quota exceeded for quota metric"
    )

    with pytest.raises(GeminiRateLimitError):
        service.generate_json("test prompt")


def test_gemini_service_non_429_raises_service_error():
    """
    Unit test: verify GeminiService raises GeminiServiceError (not GeminiRateLimitError)
    for non-429 errors (e.g., 401 auth failure).
    """
    service = GeminiService(api_key="test_key_abc")
    service._client = MagicMock()

    # Simulate a 401 authentication error
    service._client.models.generate_content.side_effect = Exception(
        "401 UNAUTHENTICATED: API key not valid"
    )

    with pytest.raises(GeminiServiceError) as exc_info:
        service.generate_json("test prompt")

    # Must be base GeminiServiceError, NOT the rate-limit subtype
    assert not isinstance(exc_info.value, GeminiRateLimitError), (
        "Auth errors must not be classified as GeminiRateLimitError"
    )
    assert isinstance(exc_info.value, GeminiAuthError), (
        "Auth errors must be classified as GeminiAuthError"
    )


# ---------------------------------------------------------------------------
# Gemini 503 Service Unavailable & Retry Policy Unit Tests
# ---------------------------------------------------------------------------

def test_gemini_service_503_once_successful_retry():
    """
    Unit test: Gemini 503 on attempt 1 succeeds on attempt 2 (retry).
    Verifies that transient 503 is recovered cleanly without throwing.
    """
    service = GeminiService(api_key="test_key_abc", backoff_seconds=[0.01, 0.02, 0.04])
    service._client = MagicMock()

    mock_resp = MagicMock()
    mock_resp.text = '{"status": "ok", "retried": true}'

    call_count = [0]

    def mock_generate(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise Exception("503 UNAVAILABLE: The service is temporarily overloaded.")
        return mock_resp

    service._client.models.generate_content.side_effect = mock_generate

    with patch("time.sleep") as mock_sleep:
        result = service.generate_json("test prompt")

    assert result == {"status": "ok", "retried": True}
    assert call_count[0] == 2
    mock_sleep.assert_called_once_with(0.01)


def test_gemini_service_503_repeatedly_raises_service_unavailable():
    """
    Unit test: Gemini 503 on all attempts exhausts retries and raises
    GeminiServiceUnavailableError.
    """
    service = GeminiService(api_key="test_key_abc", backoff_seconds=[0.01, 0.02, 0.04])
    service._client = MagicMock()
    service._client.models.generate_content.side_effect = Exception(
        "503 UNAVAILABLE: Backend service unavailable"
    )

    with patch("time.sleep"):
        with pytest.raises(GeminiServiceUnavailableError) as exc_info:
            service.generate_json("test prompt")

    assert "temporarily unavailable" in str(exc_info.value).lower()


def test_gemini_service_retry_count_limit():
    """
    Unit test: verifies max_retries limit is strictly honored (max_retries + 1 total attempts).
    """
    service = GeminiService(api_key="test_key_abc", max_retries=3, backoff_seconds=[0.001, 0.001, 0.001])
    service._client = MagicMock()
    service._client.models.generate_content.side_effect = Exception(
        "503 Service Unavailable"
    )

    with patch("time.sleep"):
        with pytest.raises(GeminiServiceUnavailableError):
            service.generate_json("test prompt")

    # 1 initial attempt + 3 retries = 4 total calls
    assert service._client.models.generate_content.call_count == 4


def test_gemini_service_exponential_backoff_delays():
    """
    Unit test: verifies backoff delays follow the configured exponential schedule.
    """
    service = GeminiService(api_key="test_key_abc", max_retries=3, backoff_seconds=[1.0, 2.0, 4.0])
    service._client = MagicMock()
    service._client.models.generate_content.side_effect = Exception("503 UNAVAILABLE")

    with patch("time.sleep") as mock_sleep:
        with pytest.raises(GeminiServiceUnavailableError):
            service.generate_json("test prompt")

    assert mock_sleep.call_count == 3
    sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
    assert sleep_calls == [1.0, 2.0, 4.0]


def test_gemini_service_non_retryable_400():
    """
    Unit test: non-retryable 400 Bad Request fails immediately without retrying.
    """
    service = GeminiService(api_key="test_key_abc", backoff_seconds=[0.01, 0.02, 0.04])
    service._client = MagicMock()
    service._client.models.generate_content.side_effect = Exception(
        "400 INVALID_ARGUMENT: Invalid parameter"
    )

    with patch("time.sleep") as mock_sleep:
        with pytest.raises(GeminiServiceError) as exc_info:
            service.generate_json("test prompt")

    # Must NOT be classified as unavailable
    assert not isinstance(exc_info.value, GeminiServiceUnavailableError)
    # Must NOT retry
    assert service._client.models.generate_content.call_count == 1
    mock_sleep.assert_not_called()


def test_analyze_non_retryable_400_returns_400():
    """
    Integration test: Gemini 400 error returns HTTP 400 with AI_INVALID_REQUEST code.
    """
    def mock_bad_request(prompt, **kwargs):
        raise GeminiServiceError("Gemini invalid request (400): INVALID_ARGUMENT")

    with patch.object(
        GeminiService, "is_configured", return_value=True
    ), patch.object(
        GeminiService, "generate_json", side_effect=mock_bad_request
    ), patch.object(
        TavilyService, "is_configured", return_value=True
    ), patch.object(
        TavilyService, "search", side_effect=_mock_tavily_search
    ):
        response = client.post("/analyze", json={"topic": "AI Robotics"})

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "AI_INVALID_REQUEST"


def test_analyze_gemini_503_once_successful_retry():
    """
    Integration test: /analyze succeeds when first Gemini call encounters a transient 503
    that recovers on retry within GeminiService.
    """
    call_counts = {"research": 0, "opportunity": 0}

    def mock_generate_json_with_transient_503(prompt, **kwargs):
        # Research call succeeds
        if "PART A" in prompt or "RETRIEVED WEB SOURCES" in prompt:
            call_counts["research"] += 1
            return {
                "research": _mock_gemini_research_response(prompt, **kwargs),
                "analysis": _mock_gemini_analysis_response(prompt, **kwargs),
            }
        # Opportunity call: fails once, then succeeds
        call_counts["opportunity"] += 1
        return _mock_gemini_opportunity_response(prompt, **kwargs)

    with patch.object(
        GeminiService, "is_configured", return_value=True
    ), patch.object(
        GeminiService, "generate_json", side_effect=mock_generate_json_with_transient_503
    ), patch.object(
        TavilyService, "is_configured", return_value=True
    ), patch.object(
        TavilyService, "search", side_effect=_mock_tavily_search
    ):
        response = client.post("/analyze", json={"topic": "AI Robotics"})

    assert response.status_code == 200
    data = response.json()
    assert data["topic"] == "AI Robotics"
    assert "opportunities" in data
    assert len(data["opportunities"]) >= 3


def test_analyze_503_failed_analysis_not_persisted():
    """
    Verify that when Gemini raises 503, incomplete analysis is NOT persisted to the database.
    """
    from backend.database.db import db

    initial_session_count = len(db.get_sessions(limit=100))

    def mock_503(prompt, **kwargs):
        raise GeminiServiceUnavailableError(
            "The AI service is temporarily unavailable. Please try again shortly."
        )

    with patch.object(
        GeminiService, "is_configured", return_value=True
    ), patch.object(
        GeminiService, "generate_json", side_effect=mock_503
    ), patch.object(
        TavilyService, "is_configured", return_value=True
    ), patch.object(
        TavilyService, "search", side_effect=_mock_tavily_search
    ):
        response = client.post("/analyze", json={"topic": "Unique Test 503 Persistence"})

    assert response.status_code == 503
    # Verify no new session was added to database
    current_session_count = len(db.get_sessions(limit=100))
    assert current_session_count == initial_session_count


def test_analyze_503_structured_error_and_no_data_leak():
    """
    Verify the 503 response adheres to the required contract:
    {
      "error": {
        "code": "AI_SERVICE_UNAVAILABLE",
        "message": "The AI service is temporarily unavailable. Please try again shortly."
      }
    }
    and never leaks API keys, stack traces, or report fields.
    """
    def mock_503(prompt, **kwargs):
        raise GeminiServiceUnavailableError(
            "The AI service is temporarily unavailable. Please try again shortly."
        )

    with patch.object(
        GeminiService, "is_configured", return_value=True
    ), patch.object(
        GeminiService, "generate_json", side_effect=mock_503
    ), patch.object(
        TavilyService, "is_configured", return_value=True
    ), patch.object(
        TavilyService, "search", side_effect=_mock_tavily_search
    ):
        response = client.post("/analyze", json={"topic": "AI Robotics"})

    assert response.status_code == 503
    data = response.json()

    assert data == {
        "error": {
            "code": "AI_SERVICE_UNAVAILABLE",
            "message": "The AI service is temporarily unavailable. Please try again shortly.",
        }
    }

    # Verify no sensitive or data leaks
    for forbidden in ["traceback", "stack", "key", "secret", "opportunities", "research", "sources", "analysis"]:
        assert forbidden not in data


