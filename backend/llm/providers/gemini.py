"""
StartupLens AI — Google Gemini provider adapter.

Wraps the existing GeminiService behind the common LLMProvider interface.
Translates Gemini-specific exceptions into the shared LLMError hierarchy
so the ModelRouter can apply provider-agnostic fallback logic.
"""

import logging
import re
import time
from typing import Any, Dict, Optional

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
from backend.config import settings

logger = logging.getLogger(__name__)


def _classify_rate_limit(e: Exception) -> str:
    """Classify a 429-class error as 'daily_quota' or 'short_term'."""
    err_str = str(e).lower()
    daily_indicators = [
        "generaterequestsperday", "generate_content_free_tier_requests",
        "quota_exceeded", "quota exceeded", "exceeded your current quota",
        "free_tier_requests", "per day", "perday", "daily", "plan and billing",
    ]
    for ind in daily_indicators:
        if ind in err_str:
            return "daily_quota"

    response_json = getattr(e, "response_json", None)
    if isinstance(response_json, dict):
        for d in response_json.get("error", {}).get("details", []):
            if isinstance(d, dict):
                for v in d.get("violations", []):
                    qid = str(v.get("quotaId", "")).lower()
                    if any(x in qid for x in ("perday", "daily", "day", "free_tier")):
                        return "daily_quota"
                retry_delay = d.get("retryDelay")
                if retry_delay:
                    try:
                        if float(str(retry_delay).rstrip("s")) > 120:
                            return "daily_quota"
                    except ValueError:
                        pass

    if re.search(r"retry in \d+\s*h", err_str) or re.search(r"retry in \d{3,}\s*s", err_str):
        return "daily_quota"

    return "short_term"


class GeminiProvider(LLMProvider):
    """
    Google Gemini provider using GeminiService.
    Translates Gemini exceptions to LLMError hierarchy.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        from backend.services.gemini_service import GeminiService

        self._api_key = (
            api_key if api_key is not None else (settings.GEMINI_API_KEY or "")
        ).strip()
        self._model = (model or settings.GEMINI_MODEL or "gemini-3.8-flash").strip()
        self._service = GeminiService(api_key=self._api_key, model=self._model)

    @property
    def provider_name(self) -> str:
        return "Google Gemini"

    @property
    def model_name(self) -> str:
        return self._model

    def is_configured(self) -> bool:
        return self._service.is_configured()

    def is_quota_exhausted(self) -> bool:
        return self._service.is_quota_exhausted()

    def health_check(self) -> Dict[str, Any]:
        if not self.is_configured():
            return {"status": "not_configured", "configured": False}
        if self.is_quota_exhausted():
            return {"status": "quota_exhausted", "configured": True}
        return {"status": "available", "configured": True}

    def generate_json(self, request: LLMRequest) -> LLMResponse:
        from backend.services.gemini_service import (
            GeminiServiceError,
            GeminiRateLimitError,
            GeminiQuotaExhaustedError,
            GeminiServiceUnavailableError,
            GeminiAuthError,
        )

        if not self.is_configured():
            raise LLMAuthError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY."
            )

        logger.info(
            f"GeminiProvider: request [{request.request_id}] model={self._model}"
        )
        t0 = self._timer()

        try:
            content = self._service.generate_json(
                prompt=request.prompt,
                system_prompt=request.system_prompt or (
                    "You are a helpful AI research assistant for StartupLens AI. "
                    "Always return valid JSON only, with no markdown fences."
                ),
                model=self._model,
                temperature=request.temperature,
            )
            return LLMResponse(
                content=content,
                provider=self.provider_name,
                model=self._model,
                latency_ms=self._elapsed_ms(t0),
                request_id=request.request_id,
            )
        except GeminiQuotaExhaustedError as exc:
            self._service.set_quota_exhausted(True, self._model)
            logger.warning(f"GeminiProvider: daily quota exhausted [{request.request_id}]")
            raise LLMQuotaExhaustedError(str(exc))
        except GeminiRateLimitError as exc:
            raise LLMRateLimitError(str(exc))
        except GeminiServiceUnavailableError as exc:
            raise LLMServiceUnavailableError(str(exc))
        except GeminiAuthError as exc:
            raise LLMAuthError(str(exc))
        except GeminiServiceError as exc:
            err_str = str(exc)
            if "invalid" in err_str.lower() or "400" in err_str:
                raise LLMInvalidRequestError(err_str)
            raise LLMServiceUnavailableError(err_str)
        except Exception as exc:
            raise LLMServiceUnavailableError(f"Gemini unexpected error: {exc}")


# Module-level singleton
gemini_provider = GeminiProvider()
