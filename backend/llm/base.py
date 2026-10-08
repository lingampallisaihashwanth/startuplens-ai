"""
StartupLens AI — Common LLM provider interface.

All provider adapters must implement LLMProvider and return LLMResponse objects.
"""

import abc
import time
import uuid
from typing import Any, Dict, Optional


class LLMError(Exception):
    """Base error for all LLM provider failures."""
    pass


class LLMRateLimitError(LLMError):
    """Short-term 429 / rate limit — safe to retry or fallback."""
    pass


class LLMQuotaExhaustedError(LLMRateLimitError):
    """Daily/monthly quota exhausted — do not retry, safe to fallback."""
    pass


class LLMServiceUnavailableError(LLMError):
    """Temporary 5xx / service down — safe to fallback."""
    pass


class LLMAuthError(LLMError):
    """401/403 authentication error — do NOT fallback (config problem)."""
    pass


class LLMInvalidRequestError(LLMError):
    """400 / bad request — do NOT fallback (caller error)."""
    pass


class LLMRequest:
    """Typed request object passed to all providers."""

    def __init__(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful AI assistant. Return valid JSON only.",
        temperature: float = 0.2,
        request_id: Optional[str] = None,
    ):
        self.prompt = prompt
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.request_id = request_id or uuid.uuid4().hex[:12]


class LLMResponse:
    """Typed response returned by all providers."""

    def __init__(
        self,
        content: Dict[str, Any],
        provider: str,
        model: str,
        latency_ms: float = 0.0,
        fallback_used: bool = False,
        fallback_reason: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        self.content = content
        self.provider = provider
        self.model = model
        self.latency_ms = latency_ms
        self.fallback_used = fallback_used
        self.fallback_reason = fallback_reason
        self.request_id = request_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "latency_ms": round(self.latency_ms, 1),
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "request_id": self.request_id,
        }


class LLMProvider(abc.ABC):
    """Abstract base class every provider adapter must implement."""

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name, e.g. 'Google Gemini'."""
        ...

    @property
    @abc.abstractmethod
    def model_name(self) -> str:
        """Active model identifier string."""
        ...

    @abc.abstractmethod
    def is_configured(self) -> bool:
        """Return True if API key and client are ready."""
        ...

    @abc.abstractmethod
    def generate_json(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a structured JSON response.
        Must return an LLMResponse whose .content is a parsed dict.
        Must raise appropriate LLMError subclasses on failure.
        Must NOT fall back silently — failures must propagate as typed errors.
        """
        ...

    def health_check(self) -> Dict[str, Any]:
        """
        Return provider health status.
        Override for a real check; default returns configured/unconfigured state.
        """
        if not self.is_configured():
            return {"status": "not_configured", "configured": False}
        return {"status": "available", "configured": True}

    @staticmethod
    def _timer() -> float:
        return time.monotonic()

    @staticmethod
    def _elapsed_ms(start: float) -> float:
        return (time.monotonic() - start) * 1000
