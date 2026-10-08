"""
StartupLens AI — Model Router.

Responsibilities:
  1. Explicit model selection: routes to the configured provider for a model ID.
  2. Auto model selection: picks a model based on task_type hint.
  3. Provider availability checks at request time.
  4. Rate-limit / quota / 5xx fallback with configurable ordering.
  5. Clear structured errors surfaced to callers.

Fallback rules:
  - Only fallback on: LLMQuotaExhaustedError, LLMRateLimitError,
    LLMServiceUnavailableError.
  - Do NOT fallback on: LLMAuthError, LLMInvalidRequestError (caller errors).
  - Fallback behaviour is configurable via ENABLE_LLM_FALLBACK env var.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

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
from backend.llm.registry import model_registry
from backend.config import settings

logger = logging.getLogger(__name__)

# Errors that trigger fallback to the next provider
_FALLBACK_ERRORS = (LLMQuotaExhaustedError, LLMRateLimitError, LLMServiceUnavailableError)

# Errors that must NOT trigger fallback (propagate immediately)
_HARD_ERRORS = (LLMAuthError, LLMInvalidRequestError)


def _get_provider_for_model_id(model_id: str) -> Optional[LLMProvider]:
    """Lazy-instantiate the right provider for a model registry entry."""
    entry = model_registry.get_model(model_id)
    if entry is None:
        return None

    provider_key = entry.get("provider")
    model_name = entry.get("model_name")

    if provider_key == "gemini":
        from backend.llm.providers.gemini import GeminiProvider
        return GeminiProvider(model=model_name)

    if provider_key == "groq":
        from backend.llm.providers.groq import GroqProvider
        return GroqProvider(model=model_name)

    if provider_key == "mistral":
        from backend.llm.providers.mistral import MistralProvider
        return MistralProvider(model=model_name)

    return None


def _fallback_chain_for(primary_id: str) -> List[str]:
    """
    Build the ordered fallback list for a given primary model ID.
    Returns model IDs in fallback_priority order, excluding the primary.
    """
    all_models = model_registry.list_models(only_enabled=True)
    # Sort by fallback_priority ascending (lower = higher priority)
    ordered = sorted(
        [m for m in all_models if m["id"] not in ("auto",) and m["id"] != primary_id],
        key=lambda m: m.get("fallback_priority", 99),
    )
    return [m["id"] for m in ordered if m.get("provider") != "router"]


def _auto_select_model(task_type: Optional[str]) -> str:
    """
    Select a model ID based on task type hint.

    task_type="research"     → prefer fast model
    task_type="analysis"     → prefer reasoning model
    task_type="opportunity"  → prefer strong general model
    default                  → prefer gemini-balanced → groq-fast → mistral-small
    """
    enabled = {m["id"] for m in model_registry.list_models(only_enabled=True)}

    if task_type == "research":
        # Prefer speed
        for mid in ("groq-fast", "gemini-balanced", "mistral-small", "groq-reasoning"):
            if mid in enabled:
                return mid

    elif task_type == "analysis":
        # Prefer reasoning capability
        for mid in ("groq-reasoning", "gemini-balanced", "mistral-small", "groq-fast"):
            if mid in enabled:
                return mid

    elif task_type == "opportunity":
        # Prefer strong general purpose
        for mid in ("gemini-balanced", "groq-reasoning", "mistral-small", "groq-fast"):
            if mid in enabled:
                return mid

    # Default priority order
    for mid in ("gemini-balanced", "groq-fast", "groq-reasoning", "mistral-small"):
        if mid in enabled:
            return mid

    raise LLMError(
        "No LLM providers are configured. Please set at least one API key."
    )


class ModelRouter:
    """
    Central router for all LLM calls in StartupLens AI.
    Agents call router.generate_json() instead of a specific provider.
    """

    def __init__(self, enable_fallback: Optional[bool] = None):
        # Default to True unless explicitly disabled
        env_val = getattr(settings, "ENABLE_LLM_FALLBACK", None)
        if enable_fallback is not None:
            self._fallback_enabled = enable_fallback
        elif env_val is not None:
            self._fallback_enabled = bool(env_val)
        else:
            self._fallback_enabled = True

    # ── Public API ─────────────────────────────────────────────────────────────

    def generate_json(
        self,
        request: LLMRequest,
        model_id: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> LLMResponse:
        """
        Route a JSON generation request to the appropriate provider.

        Args:
            request:   LLMRequest with prompt and system_prompt.
            model_id:  Explicit model selection ('auto', 'gemini-balanced', etc.)
                       If None, falls back to DEFAULT_MODEL setting.
            task_type: Hint for auto-mode ('research', 'analysis', 'opportunity').

        Returns:
            LLMResponse with content, provider metadata, and fallback info.

        Raises:
            LLMError subclass on unrecoverable failures.
        """
        # Normalise model_id
        resolved_id = self._resolve_model_id(model_id, task_type)
        logger.info(
            f"ModelRouter: routing [{request.request_id}] → model_id={resolved_id}"
        )

        # Primary attempt
        primary_provider = _get_provider_for_model_id(resolved_id)
        if primary_provider is None:
            raise LLMError(
                f"No provider adapter found for model '{resolved_id}'."
            )
        if not primary_provider.is_configured():
            raise LLMAuthError(
                f"Provider for '{resolved_id}' is not configured. "
                f"Please set the required API key."
            )

        primary_error: Optional[Exception] = None
        try:
            response = primary_provider.generate_json(request)
            return response
        except _HARD_ERRORS:
            raise
        except _FALLBACK_ERRORS as exc:
            primary_error = exc
            logger.warning(
                f"ModelRouter: primary provider '{resolved_id}' failed with "
                f"{type(exc).__name__}: {exc}. "
                f"Fallback enabled: {self._fallback_enabled}"
            )

        # Fallback chain
        if not self._fallback_enabled or primary_error is None:
            raise primary_error  # type: ignore[misc]

        chain = _fallback_chain_for(resolved_id)
        logger.info(
            f"ModelRouter: fallback chain for '{resolved_id}': {chain}"
        )

        for fallback_id in chain:
            fallback_provider = _get_provider_for_model_id(fallback_id)
            if fallback_provider is None or not fallback_provider.is_configured():
                continue

            try:
                logger.info(
                    f"ModelRouter: trying fallback '{fallback_id}' "
                    f"[{request.request_id}]"
                )
                response = fallback_provider.generate_json(request)
                # Annotate response with fallback info
                response.fallback_used = True
                response.fallback_reason = (
                    f"{primary_provider.provider_name} unavailable "
                    f"({type(primary_error).__name__})"
                )
                logger.info(
                    f"ModelRouter: fallback to '{fallback_id}' succeeded "
                    f"[{request.request_id}]"
                )
                return response
            except _HARD_ERRORS:
                raise
            except Exception as fb_exc:
                logger.warning(
                    f"ModelRouter: fallback '{fallback_id}' also failed: {fb_exc}"
                )
                continue

        # All providers failed
        raise LLMServiceUnavailableError(
            "AI analysis is temporarily unavailable. "
            "All configured providers failed. Please try again later."
        )

    def resolve_model_id(
        self,
        model_id: Optional[str],
        task_type: Optional[str] = None,
    ) -> str:
        """Public wrapper used by main.py to validate model requests."""
        return self._resolve_model_id(model_id, task_type)

    def list_models_response(self) -> Dict[str, Any]:
        """Return the /models API payload."""
        default_id = model_registry.get_default_model_id()
        enabled = model_registry.list_models(only_enabled=True)

        models_out = []
        # Always include 'auto' first
        models_out.append({
            "id": "auto",
            "display_name": "Auto",
            "provider": "router",
            "model": None,
        })

        for entry in enabled:
            if entry["id"] == "auto":
                continue
            models_out.append({
                "id": entry["id"],
                "display_name": entry["display_name"],
                "provider": entry.get("provider_label", entry["provider"]),
                "model": entry.get("model_name"),
                "speed": entry.get("speed"),
                "reasoning_level": entry.get("reasoning_level"),
            })

        return {
            "default": default_id,
            "models": models_out,
        }

    def provider_statuses(self) -> Dict[str, Any]:
        """Return provider health status for /config/status."""
        statuses: Dict[str, Any] = {}

        # Gemini
        from backend.llm.providers.gemini import GeminiProvider
        gp = GeminiProvider()
        statuses["gemini"] = gp.health_check()

        # Groq
        from backend.llm.providers.groq import GroqProvider
        grp = GroqProvider()
        statuses["groq"] = grp.health_check()

        # Mistral
        from backend.llm.providers.mistral import MistralProvider
        mp = MistralProvider()
        statuses["mistral"] = mp.health_check()

        # Tavily
        from backend.services.tavily_service import tavily_service
        if tavily_service.is_configured():
            statuses["tavily"] = {"status": "available", "configured": True}
        else:
            statuses["tavily"] = {"status": "not_configured", "configured": False}

        return statuses

    def overall_status(self) -> str:
        """Compute top-level status string for /config/status."""
        ps = self.provider_statuses()
        llm_statuses = {k: v for k, v in ps.items() if k != "tavily"}
        tavily = ps.get("tavily", {})

        any_llm_ok = any(
            v.get("status") == "available" for v in llm_statuses.values()
        )
        all_llm_exhausted = all(
            v.get("status") in ("quota_exhausted", "not_configured")
            for v in llm_statuses.values()
        )
        tavily_ok = tavily.get("status") == "available"

        if any_llm_ok and tavily_ok:
            return "ready"
        if all_llm_exhausted:
            return "quota_exhausted"
        if not any_llm_ok:
            return "needs_configuration"
        return "degraded"

    # ── Private helpers ────────────────────────────────────────────────────────

    def _resolve_model_id(
        self,
        model_id: Optional[str],
        task_type: Optional[str] = None,
    ) -> str:
        """
        Resolve a user-supplied model_id string to a concrete registry ID.
        Raises ValueError for unknown / unconfigured explicit model IDs.
        """
        if not model_id or model_id.strip().lower() == "auto":
            return _auto_select_model(task_type)

        clean = model_id.strip().lower()

        # Direct registry match
        if model_registry.is_known(clean):
            if not model_registry.is_enabled(clean):
                raise ValueError(
                    f"Model '{clean}' is not configured. "
                    f"Please set the required API key."
                )
            if clean == "auto":
                return _auto_select_model(task_type)
            return clean

        # Legacy Gemini profile IDs (FAST, BALANCED, DEEP) for backward compat
        _legacy_map = {
            "fast": "gemini-balanced",   # map to what's available
            "balanced": "gemini-balanced",
            "deep": "gemini-balanced",
        }
        if clean in _legacy_map:
            mapped = _legacy_map[clean]
            if model_registry.is_enabled(mapped):
                return mapped

        raise ValueError(
            f"Unknown model '{model_id}'. "
            f"Valid options: {', '.join(m['id'] for m in model_registry.list_models())}."
        )


# Singleton
llm_router = ModelRouter()
