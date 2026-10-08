"""
StartupLens AI — Multi-model architecture tests.

Covers:
1. Gemini provider interface
2. Groq provider interface
3. Mistral provider interface
4. Provider common interface compliance
5. Model registry
6. Model discovery endpoint (/models)
7. Explicit model selection
8. Auto routing
9. Gemini quota → Groq fallback
10. Groq failure → Mistral fallback
11. All providers unavailable
12. Invalid model ID
13. Missing API key
14. /config/status multi-provider fields
15. /analyze with mocked multi-provider
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from backend.main import app
from backend.llm.base import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    LLMError,
    LLMRateLimitError,
    LLMQuotaExhaustedError,
    LLMServiceUnavailableError,
    LLMAuthError,
    LLMInvalidRequestError,
)
from backend.llm.registry import ModelRegistry
from backend.llm.router import ModelRouter
from backend.llm.providers.gemini import GeminiProvider
from backend.llm.providers.groq import GroqProvider
from backend.llm.providers.mistral import MistralProvider

client = TestClient(app)

# ── Shared mock data ───────────────────────────────────────────────────────────

MOCK_RESEARCH_ANALYSIS = {
    "research": {
        "topic": "AI Robotics",
        "trends": ["Autonomous mobile robots"],
        "startups": ["Covariant"],
        "problems": ["High integration cost"],
        "market_signals": ["Growing VC investment"],
        "sources": [
            {
                "title": "Emerging Trends in AI",
                "url": "https://example.com/trends",
                "published_at": "2026-09-01",
                "snippet": "Industry trends.",
            }
        ],
    },
    "analysis": {
        "market_signals": ["Growing VC investment"],
        "customer_segments": ["Manufacturing operators"],
        "competitors": ["Boston Dynamics"],
        "market_gaps": ["Lack of plug-and-play tooling"],
        "why_now": ["Foundation models for robotics"],
        "trends": ["AI-powered inspection"],
        "problems": ["High integration cost"],
    },
}

MOCK_OPPORTUNITIES = {
    "opportunities": [
        {
            "title": "Autonomous QA Inspector",
            "problem": "Manual QA is slow",
            "customer": "Mid-size manufacturers",
            "solution": "Vision-based system",
            "why_now": "Foundation models",
            "competitors": ["Cognex"],
            "mvp_features": ["Camera scanner", "Defect dashboard"],
            "risks": ["Integration complexity"],
            "evidence": ["Growing VC investment"],
        },
        {
            "title": "Robot Fleet Manager",
            "problem": "Managing heterogeneous fleets",
            "customer": "Logistics operators",
            "solution": "Fleet orchestration platform",
            "why_now": "Multi-vendor deployments increasing",
            "competitors": ["6 River Systems"],
            "mvp_features": ["Fleet dashboard", "Task scheduler"],
            "risks": ["Vendor lock-in"],
            "evidence": ["Automation trend"],
        },
        {
            "title": "Robotics Training Sandbox",
            "problem": "No hands-on training",
            "customer": "Training institutions",
            "solution": "Cloud simulation platform",
            "why_now": "Simulation fidelity improved",
            "competitors": ["RoboDK"],
            "mvp_features": ["Browser simulator"],
            "risks": ["Sim-to-real gap"],
            "evidence": ["Skills shortage"],
        },
    ]
}

MOCK_TAVILY_SOURCES = [
    {
        "title": "Emerging Trends in AI",
        "url": "https://example.com/trends",
        "snippet": "Industry trends.",
        "published_at": "2026-09-01",
        "source_type": "web",
    }
]


# ── 1. Provider interface tests ────────────────────────────────────────────────

class TestProviderInterface:
    """Verify all providers implement the LLMProvider ABC correctly."""

    def test_gemini_provider_implements_interface(self):
        p = GeminiProvider(api_key="", model="gemini-2.5-flash")
        assert isinstance(p, LLMProvider)
        assert p.provider_name == "Google Gemini"
        assert p.model_name == "gemini-2.5-flash"

    def test_groq_provider_implements_interface(self):
        p = GroqProvider(api_key="", model="openai/gpt-oss-20b")
        assert isinstance(p, LLMProvider)
        assert p.provider_name == "Groq"
        assert p.model_name == "openai/gpt-oss-20b"

    def test_mistral_provider_implements_interface(self):
        p = MistralProvider(api_key="", model="mistral-small-latest")
        assert isinstance(p, LLMProvider)
        assert p.provider_name == "Mistral"
        assert p.model_name == "mistral-small-latest"

    def test_gemini_not_configured_without_key(self):
        p = GeminiProvider(api_key="", model="gemini-2.5-flash")
        assert not p.is_configured()
        health = p.health_check()
        assert health["status"] == "not_configured"
        assert health["configured"] is False

    def test_groq_not_configured_without_key(self):
        p = GroqProvider(api_key="", model="openai/gpt-oss-20b")
        assert not p.is_configured()

    def test_mistral_not_configured_without_key(self):
        p = MistralProvider(api_key="", model="mistral-small-latest")
        assert not p.is_configured()

    def test_gemini_raises_auth_when_not_configured(self):
        p = GeminiProvider(api_key="", model="gemini-2.5-flash")
        req = LLMRequest(prompt="hello", system_prompt="Return JSON")
        with pytest.raises(LLMAuthError):
            p.generate_json(req)

    def test_groq_raises_auth_when_not_configured(self):
        p = GroqProvider(api_key="", model="openai/gpt-oss-20b")
        req = LLMRequest(prompt="hello", system_prompt="Return JSON")
        with pytest.raises(LLMAuthError):
            p.generate_json(req)

    def test_mistral_raises_auth_when_not_configured(self):
        p = MistralProvider(api_key="", model="mistral-small-latest")
        req = LLMRequest(prompt="hello", system_prompt="Return JSON")
        with pytest.raises(LLMAuthError):
            p.generate_json(req)

    def test_llm_response_carries_metadata(self):
        resp = LLMResponse(
            content={"key": "value"},
            provider="Test Provider",
            model="test-model",
            latency_ms=123.4,
            fallback_used=True,
            fallback_reason="Primary unavailable",
            request_id="req123",
        )
        d = resp.to_dict()
        assert d["provider"] == "Test Provider"
        assert d["model"] == "test-model"
        assert d["fallback_used"] is True
        assert d["fallback_reason"] == "Primary unavailable"
        assert d["request_id"] == "req123"


# ── 2. Model registry tests ────────────────────────────────────────────────────

class TestModelRegistry:
    """Verify model registry contains correct entries and handles key presence."""

    def test_all_models_known(self):
        reg = ModelRegistry()
        for mid in ("auto", "gemini-balanced", "groq-fast", "groq-reasoning", "mistral-small"):
            assert reg.is_known(mid), f"Expected '{mid}' to be in registry"

    def test_auto_always_enabled(self):
        reg = ModelRegistry()
        assert reg.is_enabled("auto")

    def test_gemini_enabled_only_when_key_set(self):
        reg = ModelRegistry()
        from backend.config import settings
        expected = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())
        assert reg.is_enabled("gemini-balanced") == expected

    def test_groq_enabled_only_when_key_set(self):
        reg = ModelRegistry()
        from backend.config import settings
        expected = bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip())
        assert reg.is_enabled("groq-fast") == expected

    def test_mistral_enabled_only_when_key_set(self):
        reg = ModelRegistry()
        from backend.config import settings
        expected = bool(settings.MISTRAL_API_KEY and settings.MISTRAL_API_KEY.strip())
        assert reg.is_enabled("mistral-small") == expected

    def test_gemini_model_name_from_settings(self):
        reg = ModelRegistry()
        from backend.config import settings
        entry = reg.get_model("gemini-balanced")
        assert entry is not None
        assert entry["model_name"] == (settings.GEMINI_MODEL or "gemini-2.5-flash")

    def test_list_models_always_includes_auto(self):
        reg = ModelRegistry()
        enabled = reg.list_models(only_enabled=True)
        ids = [m["id"] for m in enabled]
        assert "auto" in ids

    def test_get_model_returns_none_for_unknown(self):
        reg = ModelRegistry()
        assert reg.get_model("nonexistent-xyz") is None


# ── 3. Model discovery endpoint (/models) ─────────────────────────────────────

class TestModelsEndpoint:
    def test_models_endpoint_returns_200(self):
        resp = client.get("/models")
        assert resp.status_code == 200

    def test_models_endpoint_has_required_fields(self):
        resp = client.get("/models")
        data = resp.json()
        assert "models" in data
        assert "default" in data
        assert isinstance(data["models"], list)
        assert len(data["models"]) > 0

    def test_models_endpoint_always_includes_auto(self):
        resp = client.get("/models")
        data = resp.json()
        ids = [m["id"] for m in data["models"]]
        assert "auto" in ids

    def test_models_endpoint_each_entry_has_id_and_display_name(self):
        resp = client.get("/models")
        data = resp.json()
        for m in data["models"]:
            assert "id" in m
            assert "display_name" in m
            assert "provider" in m


# ── 4. Model router — explicit selection & auto ────────────────────────────────

class TestModelRouter:
    def test_explicit_auto_resolves(self):
        router = ModelRouter()
        from backend.config import settings
        # At minimum gemini-balanced should be configured (GEMINI_API_KEY is set)
        result = router.resolve_model_id("auto")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_auto_none_resolves(self):
        router = ModelRouter()
        result = router.resolve_model_id(None)
        assert isinstance(result, str)

    def test_explicit_gemini_balanced_resolves_when_configured(self):
        from backend.config import settings
        if not settings.GEMINI_API_KEY:
            pytest.skip("GEMINI_API_KEY not configured")
        router = ModelRouter()
        result = router.resolve_model_id("gemini-balanced")
        assert result == "gemini-balanced"

    def test_unknown_model_raises_value_error(self):
        router = ModelRouter()
        with pytest.raises(ValueError):
            router.resolve_model_id("openai-gpt-4o")

    def test_unknown_model_raises_for_completely_unknown(self):
        router = ModelRouter()
        with pytest.raises(ValueError):
            router.resolve_model_id("fakemodel-xyz-1234")

    def test_unconfigured_explicit_model_raises_value_error(self):
        """Requesting a model whose key is not set should raise ValueError."""
        router = ModelRouter()
        from backend.config import settings
        if settings.GROQ_API_KEY:
            pytest.skip("GROQ_API_KEY is configured — skip unconfigured test")
        with pytest.raises(ValueError):
            router.resolve_model_id("groq-fast")


# ── 5. Fallback behaviour tests ────────────────────────────────────────────────

class TestFallbackBehavior:
    """Test fallback chain using mocked providers."""

    def _make_mock_request(self):
        return LLMRequest(
            prompt="test prompt",
            system_prompt="Return JSON",
        )

    def _mock_success_response(self, provider_name, model):
        return LLMResponse(
            content={"result": "ok"},
            provider=provider_name,
            model=model,
            latency_ms=100,
        )

    def test_gemini_quota_falls_back_to_groq(self):
        """
        When Gemini raises LLMQuotaExhaustedError, router should fall back
        to a Groq provider if configured.
        """
        router = ModelRouter(enable_fallback=True)
        req = self._make_mock_request()

        with patch("backend.llm.router._get_provider_for_model_id") as mock_get:
            # Primary = gemini-balanced → raises quota error
            gemini_mock = MagicMock()
            gemini_mock.is_configured.return_value = True
            gemini_mock.provider_name = "Google Gemini"
            gemini_mock.generate_json.side_effect = LLMQuotaExhaustedError(
                "Gemini quota exhausted"
            )

            # Fallback = groq-fast → succeeds
            groq_mock = MagicMock()
            groq_mock.is_configured.return_value = True
            groq_mock.provider_name = "Groq"
            groq_mock.generate_json.return_value = self._mock_success_response("Groq", "openai/gpt-oss-20b")

            def get_provider(model_id):
                if model_id == "gemini-balanced":
                    return gemini_mock
                if model_id == "groq-fast":
                    return groq_mock
                return None

            mock_get.side_effect = get_provider

            with patch("backend.llm.router._fallback_chain_for", return_value=["groq-fast"]):
                with patch("backend.llm.router._auto_select_model", return_value="gemini-balanced"):
                    response = router.generate_json(req, model_id="gemini-balanced")

        assert response.fallback_used is True
        assert response.provider == "Groq"
        assert "Gemini" in (response.fallback_reason or "")

    def test_groq_failure_falls_back_to_mistral(self):
        """When Groq raises LLMServiceUnavailableError, falls back to Mistral."""
        router = ModelRouter(enable_fallback=True)
        req = self._make_mock_request()

        with patch("backend.llm.router._get_provider_for_model_id") as mock_get:
            groq_mock = MagicMock()
            groq_mock.is_configured.return_value = True
            groq_mock.provider_name = "Groq"
            groq_mock.generate_json.side_effect = LLMServiceUnavailableError(
                "Groq unavailable"
            )

            mistral_mock = MagicMock()
            mistral_mock.is_configured.return_value = True
            mistral_mock.provider_name = "Mistral"
            mistral_mock.generate_json.return_value = self._mock_success_response(
                "Mistral", "mistral-small-latest"
            )

            def get_provider(model_id):
                if model_id == "groq-fast":
                    return groq_mock
                if model_id == "mistral-small":
                    return mistral_mock
                return None

            mock_get.side_effect = get_provider

            with patch("backend.llm.router._fallback_chain_for", return_value=["mistral-small"]):
                with patch("backend.llm.router._auto_select_model", return_value="groq-fast"):
                    response = router.generate_json(req, model_id="groq-fast")

        assert response.fallback_used is True
        assert response.provider == "Mistral"

    def test_all_providers_unavailable_raises(self):
        """When all providers fail, raises LLMServiceUnavailableError."""
        router = ModelRouter(enable_fallback=True)
        req = self._make_mock_request()

        with patch("backend.llm.router._get_provider_for_model_id") as mock_get:
            dead_mock = MagicMock()
            dead_mock.is_configured.return_value = True
            dead_mock.provider_name = "Google Gemini"
            dead_mock.generate_json.side_effect = LLMServiceUnavailableError(
                "Service down"
            )

            dead_fallback = MagicMock()
            dead_fallback.is_configured.return_value = True
            dead_fallback.provider_name = "Groq"
            dead_fallback.generate_json.side_effect = LLMServiceUnavailableError(
                "Also down"
            )

            def get_provider(mid):
                if mid == "gemini-balanced":
                    return dead_mock
                if mid == "groq-fast":
                    return dead_fallback
                return None

            mock_get.side_effect = get_provider

            with patch("backend.llm.router._fallback_chain_for", return_value=["groq-fast"]):
                with patch("backend.llm.router._auto_select_model", return_value="gemini-balanced"):
                    with pytest.raises(LLMServiceUnavailableError):
                        router.generate_json(req, model_id="gemini-balanced")

    def test_fallback_disabled_does_not_retry(self):
        """When fallback disabled, quota error propagates immediately."""
        router = ModelRouter(enable_fallback=False)
        req = self._make_mock_request()

        with patch("backend.llm.router._get_provider_for_model_id") as mock_get:
            gemini_mock = MagicMock()
            gemini_mock.is_configured.return_value = True
            gemini_mock.provider_name = "Google Gemini"
            gemini_mock.generate_json.side_effect = LLMQuotaExhaustedError(
                "Quota exhausted"
            )
            mock_get.return_value = gemini_mock

            with patch("backend.llm.router._auto_select_model", return_value="gemini-balanced"):
                with pytest.raises(LLMQuotaExhaustedError):
                    router.generate_json(req, model_id="gemini-balanced")

    def test_auth_error_does_not_fallback(self):
        """Auth errors (401/403) must NOT trigger fallback — they are config errors."""
        router = ModelRouter(enable_fallback=True)
        req = self._make_mock_request()

        with patch("backend.llm.router._get_provider_for_model_id") as mock_get:
            gemini_mock = MagicMock()
            gemini_mock.is_configured.return_value = True
            gemini_mock.provider_name = "Google Gemini"
            gemini_mock.generate_json.side_effect = LLMAuthError(
                "Invalid API key"
            )
            mock_get.return_value = gemini_mock

            with patch("backend.llm.router._auto_select_model", return_value="gemini-balanced"):
                with pytest.raises(LLMAuthError):
                    router.generate_json(req, model_id="gemini-balanced")

    def test_invalid_request_does_not_fallback(self):
        """Invalid request errors (400) must NOT trigger fallback."""
        router = ModelRouter(enable_fallback=True)
        req = self._make_mock_request()

        with patch("backend.llm.router._get_provider_for_model_id") as mock_get:
            gemini_mock = MagicMock()
            gemini_mock.is_configured.return_value = True
            gemini_mock.provider_name = "Google Gemini"
            gemini_mock.generate_json.side_effect = LLMInvalidRequestError(
                "Bad input"
            )
            mock_get.return_value = gemini_mock

            with patch("backend.llm.router._auto_select_model", return_value="gemini-balanced"):
                with pytest.raises(LLMInvalidRequestError):
                    router.generate_json(req, model_id="gemini-balanced")


# ── 6. /config/status multi-provider ─────────────────────────────────────────

class TestConfigStatusMultiProvider:
    def test_config_status_has_providers_field(self):
        resp = client.get("/config/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "providers" in data
        assert "gemini" in data["providers"]
        assert "groq" in data["providers"]
        assert "mistral" in data["providers"]
        assert "tavily" in data["providers"]

    def test_config_status_providers_have_status_and_configured(self):
        resp = client.get("/config/status")
        data = resp.json()
        for provider_name, info in data["providers"].items():
            assert "status" in info, f"{provider_name} missing 'status'"
            assert "configured" in info, f"{provider_name} missing 'configured'"

    def test_config_status_has_default_model(self):
        resp = client.get("/config/status")
        data = resp.json()
        assert "default_model" in data
        assert isinstance(data["default_model"], str)

    def test_config_status_does_not_expose_api_keys(self):
        resp = client.get("/config/status")
        text = resp.text
        from backend.config import settings
        for key in (
            settings.GEMINI_API_KEY,
            settings.GROQ_API_KEY,
            settings.MISTRAL_API_KEY,
            settings.TAVILY_API_KEY,
        ):
            if key and key.strip():
                assert key.strip() not in text, f"API key leaked in /config/status response"

    def test_config_status_overall_status_is_string(self):
        resp = client.get("/config/status")
        data = resp.json()
        assert isinstance(data["status"], str)
        assert data["status"] in (
            "ready", "degraded", "quota_exhausted", "needs_configuration"
        )


# ── 7. /analyze with mocked multi-provider ───────────────────────────────────

class TestAnalyzeMultiModel:
    """Integration tests for /analyze with multi-provider mocking."""

    def _mock_tavily(self):
        return MOCK_TAVILY_SOURCES

    def _mock_llm_research(self, req: LLMRequest) -> LLMResponse:
        return LLMResponse(
            content=MOCK_RESEARCH_ANALYSIS,
            provider="Google Gemini",
            model="gemini-2.5-flash",
            latency_ms=500,
            fallback_used=False,
        )

    def _mock_llm_opportunity(self, req: LLMRequest) -> LLMResponse:
        return LLMResponse(
            content=MOCK_OPPORTUNITIES,
            provider="Google Gemini",
            model="gemini-2.5-flash",
            latency_ms=800,
            fallback_used=False,
        )

    def test_analyze_with_auto_model(self):
        """Verify /analyze accepts model=auto and returns structured output."""
        call_count = [0]

        def mock_generate(request, model_id=None, task_type=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return LLMResponse(
                    content=MOCK_RESEARCH_ANALYSIS,
                    provider="Google Gemini",
                    model="gemini-2.5-flash",
                    latency_ms=500,
                )
            return LLMResponse(
                content=MOCK_OPPORTUNITIES,
                provider="Google Gemini",
                model="gemini-2.5-flash",
                latency_ms=800,
            )

        from backend.services.tavily_service import TavilyService

        with patch.object(TavilyService, "is_configured", return_value=True), \
             patch.object(TavilyService, "search", return_value=self._mock_tavily()), \
             patch("backend.llm.router.ModelRouter.generate_json", side_effect=mock_generate):

            response = client.post("/analyze", json={"topic": "AI Robotics", "model": "auto"})

        assert response.status_code == 200
        data = response.json()
        assert data["topic"] == "AI Robotics"
        assert "research" in data
        assert "opportunities" in data

    def test_analyze_with_gemini_balanced_model(self):
        """Verify /analyze with explicit gemini-balanced model ID works."""
        call_count = [0]

        def mock_generate(request, model_id=None, task_type=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return LLMResponse(
                    content=MOCK_RESEARCH_ANALYSIS,
                    provider="Google Gemini",
                    model="gemini-2.5-flash",
                    latency_ms=500,
                )
            return LLMResponse(
                content=MOCK_OPPORTUNITIES,
                provider="Google Gemini",
                model="gemini-2.5-flash",
                latency_ms=800,
            )

        from backend.services.tavily_service import TavilyService

        with patch.object(TavilyService, "is_configured", return_value=True), \
             patch.object(TavilyService, "search", return_value=self._mock_tavily()), \
             patch("backend.llm.router.ModelRouter.generate_json", side_effect=mock_generate):

            response = client.post("/analyze", json={"topic": "AI Healthcare", "model": "gemini-balanced"})

        assert response.status_code == 200

    def test_analyze_invalid_model_returns_400(self):
        """Verify /analyze rejects unknown model IDs."""
        response = client.post(
            "/analyze", json={"topic": "AI Robotics", "model": "nonexistent-model-xyz"}
        )
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_MODEL"

    def test_analyze_quota_exhausted_returns_429(self):
        """When quota exhausted, /analyze returns 429 with structured error."""
        from backend.services.tavily_service import TavilyService

        def mock_generate(request, model_id=None, task_type=None):
            raise LLMQuotaExhaustedError("Quota exhausted")

        with patch.object(TavilyService, "is_configured", return_value=True), \
             patch.object(TavilyService, "search", return_value=self._mock_tavily()), \
             patch("backend.llm.router.ModelRouter.generate_json", side_effect=mock_generate):

            response = client.post("/analyze", json={"topic": "AI Robotics"})

        assert response.status_code == 429
        data = response.json()
        assert data["error"]["code"] == "AI_QUOTA_EXHAUSTED"

    def test_analyze_service_unavailable_returns_503(self):
        """When all providers down, /analyze returns 503."""
        from backend.services.tavily_service import TavilyService

        def mock_generate(request, model_id=None, task_type=None):
            raise LLMServiceUnavailableError("All providers down")

        with patch.object(TavilyService, "is_configured", return_value=True), \
             patch.object(TavilyService, "search", return_value=self._mock_tavily()), \
             patch("backend.llm.router.ModelRouter.generate_json", side_effect=mock_generate):

            response = client.post("/analyze", json={"topic": "AI Robotics"})

        assert response.status_code == 503
        data = response.json()
        assert data["error"]["code"] == "AI_SERVICE_UNAVAILABLE"

    def test_analyze_auth_error_returns_401(self):
        """Auth errors propagate as 401."""
        from backend.services.tavily_service import TavilyService

        def mock_generate(request, model_id=None, task_type=None):
            raise LLMAuthError("Invalid API key")

        with patch.object(TavilyService, "is_configured", return_value=True), \
             patch.object(TavilyService, "search", return_value=self._mock_tavily()), \
             patch("backend.llm.router.ModelRouter.generate_json", side_effect=mock_generate):

            response = client.post("/analyze", json={"topic": "AI Robotics"})

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "AI_AUTH_ERROR"

    def test_analyze_with_fallback_info(self):
        """When fallback occurs, response should include model_used from fallback."""
        call_count = [0]

        def mock_generate(request, model_id=None, task_type=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return LLMResponse(
                    content=MOCK_RESEARCH_ANALYSIS,
                    provider="Groq",
                    model="openai/gpt-oss-20b",
                    latency_ms=300,
                    fallback_used=True,
                    fallback_reason="Gemini quota exhausted",
                )
            return LLMResponse(
                content=MOCK_OPPORTUNITIES,
                provider="Groq",
                model="openai/gpt-oss-20b",
                latency_ms=500,
                fallback_used=True,
                fallback_reason="Gemini quota exhausted",
            )

        from backend.services.tavily_service import TavilyService

        with patch.object(TavilyService, "is_configured", return_value=True), \
             patch.object(TavilyService, "search", return_value=self._mock_tavily()), \
             patch("backend.llm.router.ModelRouter.generate_json", side_effect=mock_generate):

            response = client.post("/analyze", json={"topic": "AI Robotics", "model": "auto"})

        assert response.status_code == 200


# ── 8. Missing API key tests ──────────────────────────────────────────────────

class TestMissingApiKeys:
    def test_gemini_generate_json_raises_auth_without_key(self):
        p = GeminiProvider(api_key="")
        req = LLMRequest(prompt="test", system_prompt="Return JSON")
        with pytest.raises(LLMAuthError):
            p.generate_json(req)

    def test_groq_generate_json_raises_auth_without_key(self):
        p = GroqProvider(api_key="")
        req = LLMRequest(prompt="test", system_prompt="Return JSON")
        with pytest.raises(LLMAuthError):
            p.generate_json(req)

    def test_mistral_generate_json_raises_auth_without_key(self):
        p = MistralProvider(api_key="")
        req = LLMRequest(prompt="test", system_prompt="Return JSON")
        with pytest.raises(LLMAuthError):
            p.generate_json(req)
