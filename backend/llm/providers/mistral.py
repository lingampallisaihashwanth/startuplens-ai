"""
StartupLens AI — Mistral provider adapter.

Uses the official mistralai Python SDK.
Model is configured via MISTRAL_MODEL env var (never hard-coded to a
specific version string that may become deprecated).
"""

import json
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


class MistralProvider(LLMProvider):
    """
    Mistral AI provider using the official mistralai SDK.
    Model is read from settings.MISTRAL_MODEL (env: MISTRAL_MODEL).
    Defaults to 'mistral-small-latest' if not set.
    """

    MAX_RETRIES = 2
    BACKOFF = [1.0, 2.0]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self._api_key = (
            api_key if api_key is not None else (settings.MISTRAL_API_KEY or "")
        ).strip()
        self._model = (
            model or settings.MISTRAL_MODEL or "mistral-small-latest"
        ).strip()
        self._client = None

        if self._api_key:
            try:
                try:
                    from mistralai import Mistral  # type: ignore
                except ImportError:
                    from mistralai.client import Mistral  # type: ignore
                self._client = Mistral(api_key=self._api_key)
            except Exception as exc:
                logger.error(f"MistralProvider: failed to initialise client: {exc}")

    @property
    def provider_name(self) -> str:
        return "Mistral"

    @property
    def model_name(self) -> str:
        return self._model

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def health_check(self) -> Dict[str, Any]:
        if not self.is_configured():
            return {"status": "not_configured", "configured": False}
        return {"status": "available", "configured": True}

    def generate_json(self, request: LLMRequest) -> LLMResponse:
        if not self.is_configured():
            raise LLMAuthError(
                "Mistral API key is not configured. Please set MISTRAL_API_KEY."
            )
        if self._client is None:
            raise LLMAuthError(
                "Mistral client failed to initialise. Verify your MISTRAL_API_KEY."
            )

        logger.info(
            f"MistralProvider: request [{request.request_id}] model={self._model}"
        )
        t0 = self._timer()

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = self._client.chat.complete(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": request.system_prompt},
                        {"role": "user", "content": request.prompt},
                    ],
                    temperature=request.temperature,
                    response_format={"type": "json_object"},
                )

                raw_text = response.choices[0].message.content or ""
                if not raw_text:
                    raise LLMError("Mistral returned an empty response.")

                content = self._parse_json(raw_text, request.request_id)
                return LLMResponse(
                    content=content,
                    provider=self.provider_name,
                    model=self._model,
                    latency_ms=self._elapsed_ms(t0),
                    request_id=request.request_id,
                )

            except (LLMError, LLMAuthError, LLMInvalidRequestError,
                    LLMQuotaExhaustedError, LLMRateLimitError,
                    LLMServiceUnavailableError):
                raise

            except Exception as exc:
                err = str(exc)
                err_l = err.lower()
                code = (
                    getattr(exc, "status_code", None)
                    or getattr(exc, "http_status", None)
                    or getattr(exc, "code", None)
                )
                try:
                    code = int(code)
                except (TypeError, ValueError):
                    pass

                is_rate = (
                    code == 429
                    or "429" in err
                    or "rate_limit" in err_l
                    or "rate limit" in err_l
                    or "too_many_requests" in err_l
                    or "ratelimit" in err_l
                )
                is_auth = (
                    code in (401, 403)
                    or "401" in err or "403" in err
                    or "unauthorized" in err_l
                    or "invalid api key" in err_l
                    or "authentication" in err_l
                )
                is_bad = (
                    code == 400
                    or "400" in err
                    or "invalid request" in err_l
                    or "bad request" in err_l
                    or "invalid model" in err_l
                )
                is_unavail = (
                    code in (500, 502, 503, 504)
                    or any(str(c) in err for c in (500, 502, 503, 504))
                    or "unavailable" in err_l
                    or "server error" in err_l
                    or "internal error" in err_l
                )

                if is_rate:
                    if "quota" in err_l or "exceeded" in err_l:
                        raise LLMQuotaExhaustedError(
                            "Mistral quota exhausted. Try again later."
                        )
                    if attempt < self.MAX_RETRIES:
                        wait = self.BACKOFF[min(attempt, len(self.BACKOFF) - 1)]
                        logger.warning(
                            f"MistralProvider: rate limit, retry {attempt+1} in {wait:.1f}s"
                        )
                        time.sleep(wait)
                        continue
                    raise LLMRateLimitError(
                        "Mistral rate limit reached. Please try again shortly."
                    )
                if is_auth:
                    raise LLMAuthError(
                        "Mistral authentication failed. Verify your MISTRAL_API_KEY."
                    )
                if is_bad:
                    raise LLMInvalidRequestError(
                        f"Mistral rejected the request (400): {err[:200]}"
                    )
                if is_unavail:
                    if attempt < self.MAX_RETRIES:
                        wait = self.BACKOFF[min(attempt, len(self.BACKOFF) - 1)]
                        logger.warning(
                            f"MistralProvider: 5xx, retry {attempt+1} in {wait:.1f}s"
                        )
                        time.sleep(wait)
                        continue
                    raise LLMServiceUnavailableError(
                        "Mistral service is temporarily unavailable."
                    )

                if "timeout" in err_l or "timed out" in err_l:
                    raise LLMServiceUnavailableError("Mistral request timed out.")
                if "connect" in err_l or "network" in err_l:
                    raise LLMServiceUnavailableError(
                        "Cannot connect to Mistral API. Check network."
                    )
                raise LLMError(
                    f"Mistral unexpected error [{type(exc).__name__}]: {err[:200]}"
                )

    @staticmethod
    def _parse_json(text: str, request_id: Optional[str] = None) -> Dict[str, Any]:
        clean = text.strip()
        clean = re.sub(r"^`{3}(?:json)?\s*", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\s*`{3}$", "", clean)
        try:
            return json.loads(clean)
        except json.JSONDecodeError as exc:
            logger.error(
                f"MistralProvider: JSON parse failed [{request_id}]: {exc}"
            )
            raise LLMError("Mistral returned malformed JSON.")


# Module-level singleton
mistral_provider = MistralProvider()
