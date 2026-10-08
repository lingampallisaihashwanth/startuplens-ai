"""
StartupLens AI — Groq provider adapter.

Uses the official groq Python SDK to call Groq's OpenAI-compatible API.
Translates Groq SDK exceptions into the shared LLMError hierarchy.
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


class GroqProvider(LLMProvider):
    """
    Groq provider using the official groq Python SDK.
    Supports two model tiers: fast (small) and reasoning (large).
    """

    MAX_RETRIES = 2
    BACKOFF = [1.0, 2.0]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self._api_key = (
            api_key if api_key is not None else (settings.GROQ_API_KEY or "")
        ).strip()
        self._model = (
            model or settings.GROQ_MODEL_FAST or "openai/gpt-oss-20b"
        ).strip()
        self._client = None

        if self._api_key:
            try:
                from groq import Groq  # type: ignore
                self._client = Groq(api_key=self._api_key)
            except Exception as exc:
                logger.error(f"GroqProvider: failed to initialise client: {exc}")

    @property
    def provider_name(self) -> str:
        return "Groq"

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
                "Groq API key is not configured. Please set GROQ_API_KEY."
            )
        if self._client is None:
            raise LLMAuthError(
                "Groq client failed to initialise. Verify your GROQ_API_KEY."
            )

        logger.info(
            f"GroqProvider: request [{request.request_id}] model={self._model}"
        )
        t0 = self._timer()

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                completion = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": request.system_prompt},
                        {"role": "user", "content": request.prompt},
                    ],
                    temperature=request.temperature,
                    response_format={"type": "json_object"},
                    max_tokens=8192,
                )

                raw_text = completion.choices[0].message.content or ""
                if not raw_text:
                    raise LLMError("Groq returned an empty response.")

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
                    or getattr(exc, "code", None)
                )
                # Try to extract code from groq error body
                if code is None:
                    body = getattr(exc, "body", None) or {}
                    if isinstance(body, dict):
                        code = body.get("error", {}).get("code") or body.get("status")
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
                    or "invalid api key" in err_l
                    or "authentication" in err_l
                    or "unauthorized" in err_l
                )
                is_bad = (
                    code == 400
                    or "400" in err
                    or "invalid request" in err_l
                    or "bad request" in err_l
                )
                is_unavail = (
                    code in (500, 502, 503, 504)
                    or any(str(c) in err for c in (500, 502, 503, 504))
                    or "unavailable" in err_l
                    or "server error" in err_l
                    or "internal error" in err_l
                )

                if is_rate:
                    # Check for quota-style exhaustion
                    if "quota" in err_l or "exceeded" in err_l or "limit reached" in err_l:
                        raise LLMQuotaExhaustedError(
                            "Groq quota exhausted. Try again later."
                        )
                    if attempt < self.MAX_RETRIES:
                        wait = self.BACKOFF[min(attempt, len(self.BACKOFF) - 1)]
                        logger.warning(
                            f"GroqProvider: rate limit, retry {attempt+1} in {wait:.1f}s"
                        )
                        time.sleep(wait)
                        continue
                    raise LLMRateLimitError(
                        "Groq rate limit reached. Please try again shortly."
                    )
                if is_auth:
                    raise LLMAuthError(
                        "Groq authentication failed. Verify your GROQ_API_KEY."
                    )
                if is_bad:
                    raise LLMInvalidRequestError(
                        f"Groq rejected the request (400): {err[:200]}"
                    )
                if is_unavail:
                    if attempt < self.MAX_RETRIES:
                        wait = self.BACKOFF[min(attempt, len(self.BACKOFF) - 1)]
                        logger.warning(
                            f"GroqProvider: 5xx, retry {attempt+1} in {wait:.1f}s"
                        )
                        time.sleep(wait)
                        continue
                    raise LLMServiceUnavailableError(
                        "Groq service is temporarily unavailable."
                    )

                if "timeout" in err_l or "timed out" in err_l:
                    raise LLMServiceUnavailableError("Groq request timed out.")
                if "connect" in err_l or "network" in err_l:
                    raise LLMServiceUnavailableError(
                        "Cannot connect to Groq API. Check network."
                    )
                raise LLMError(
                    f"Groq unexpected error [{type(exc).__name__}]: {err[:200]}"
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
                f"GroqProvider: JSON parse failed [{request_id}]: {exc}"
            )
            raise LLMError("Groq returned malformed JSON.")


# Fast model singleton (default)
groq_provider = GroqProvider()
