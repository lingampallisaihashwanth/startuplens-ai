import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from backend.config import settings

logger = logging.getLogger(__name__)


class GeminiServiceError(Exception):
    """Base exception for Google Gemini service operations."""
    pass


class GeminiRateLimitError(GeminiServiceError):
    """Raised when Gemini returns a short-term 429 RESOURCE_EXHAUSTED / rate limit error."""
    pass


class GeminiQuotaExhaustedError(GeminiRateLimitError):
    """Raised when Gemini daily/long-term quota has been exhausted (e.g. GenerateRequestsPerDayPerProjectPerModel-FreeTier)."""
    pass


class GeminiServiceUnavailableError(GeminiServiceError):
    """Raised when Gemini returns HTTP 503 UNAVAILABLE after bounded retries."""
    pass


class GeminiAuthError(GeminiServiceError):
    """Raised when Gemini returns HTTP 401/403 unauthenticated/permission denied."""
    pass


def classify_rate_limit_error(e: Exception) -> str:
    """
    Classify a 429/RESOURCE_EXHAUSTED error as either 'daily_quota' or 'short_term'.
    Returns: 'daily_quota' or 'short_term'.
    """
    err_str = str(e).lower()

    # Daily quota indicators in error string
    daily_quota_indicators = [
        "generaterequestsperday",
        "generate_content_free_tier_requests",
        "quota_exceeded",
        "quota exceeded",
        "exceeded your current quota",
        "free_tier_requests",
        "per day",
        "perday",
        "daily",
        "plan and billing",
        "check your plan",
    ]
    for indicator in daily_quota_indicators:
        if indicator in err_str:
            return "daily_quota"

    # Check response_json structure if present (e.g. google.genai.errors.ClientError)
    response_json = getattr(e, "response_json", None)
    if isinstance(response_json, dict):
        err_dict = response_json.get("error", {})
        details = err_dict.get("details", [])
        for d in details:
            if isinstance(d, dict):
                # QuotaFailure violations
                violations = d.get("violations", [])
                for v in violations:
                    qid = str(v.get("quotaId", "")).lower()
                    qmetric = str(v.get("quotaMetric", "")).lower()
                    if "perday" in qid or "daily" in qid or "day" in qid or "free_tier" in qmetric:
                        return "daily_quota"
                # RetryInfo retryDelay
                retry_delay = d.get("retryDelay")
                if retry_delay:
                    delay_str = str(retry_delay).rstrip("s")
                    try:
                        if float(delay_str) > 120:
                            return "daily_quota"
                    except ValueError:
                        pass

    # Regex for long retry delay in message, e.g. "retry in 13h" or "retry in 46839s"
    if re.search(r"retry in \d+\s*h", err_str) or re.search(r"retry in \d{3,}\s*s", err_str):
        return "daily_quota"

    return "short_term"


class GeminiService:
    """
    Service client for Google Gemini models using the official google-genai SDK.
    Supports structured JSON output via response_mime_type.
    Retries up to 3 times on transient short-term 429 and 503 UNAVAILABLE with exponential backoff.
    Never automatically retries daily quota exhaustion errors.
    """

    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BACKOFF_SECONDS = [1.0, 2.0, 4.0]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_seconds: Optional[List[float]] = None,
    ):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self.max_retries = max_retries
        self.backoff_seconds = (
            list(backoff_seconds) if backoff_seconds is not None else list(self.DEFAULT_BACKOFF_SECONDS)
        )
        self._client: Optional[genai.Client] = None
        self._quota_exhausted: bool = False
        self._quota_exhausted_model: Optional[str] = None

        if self.is_configured():
            try:
                self._client = genai.Client(api_key=self.api_key.strip())
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def is_quota_exhausted(self) -> bool:
        return self._quota_exhausted

    def set_quota_exhausted(self, exhausted: bool, model: Optional[str] = None):
        self._quota_exhausted = exhausted
        if exhausted and model:
            self._quota_exhausted_model = model

    def get_quota_exhausted_model(self) -> Optional[str]:
        return self._quota_exhausted_model

    def generate_json(
        self,
        prompt: str,
        system_prompt: str = (
            "You are a helpful AI research assistant for StartupLens AI. "
            "Always return valid JSON only, with no markdown fences."
        ),
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Request structured JSON from Google Gemini using the official SDK.
        Uses response_mime_type=application/json to enforce JSON output.
        Disables automatic function calling (AFC) since function calling is not used.
        Retries up to max_retries times on short-term 429 and 503 UNAVAILABLE with exponential backoff.
        Immediately raises GeminiQuotaExhaustedError on daily quota errors without retrying.
        """
        if not self.is_configured():
            raise GeminiAuthError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY in your .env file."
            )

        if self._client is None:
            raise GeminiAuthError(
                "Gemini client failed to initialize. Please verify your GEMINI_API_KEY."
            )

        target_model = model or self.model

        # Configure GenerateContentConfig with AFC disabled to avoid unnecessary SDK warnings
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            response_mime_type="application/json",
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        logger.info(f"Gemini request started for model: {target_model}")

        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=config,
                )

                if not response or not response.text:
                    raise GeminiServiceError("Gemini returned an empty response with no text content.")

                result = self._parse_json(response.text)
                # Successful response resets quota exhausted flag
                self.set_quota_exhausted(False)
                return result

            except GeminiServiceError:
                raise
            except Exception as e:
                error_msg = str(e)
                error_lower = error_msg.lower()
                status_code = getattr(e, "code", None) or getattr(e, "status_code", None)

                # Check non-retryable categories first
                is_rate_limit = (
                    status_code == 429
                    or "429" in error_msg
                    or "resource_exhausted" in error_lower
                    or "quota" in error_lower
                    or "rate_limit" in error_lower
                    or "rate limit" in error_lower
                    or "too_many_requests" in error_lower
                )
                is_auth_error = (
                    status_code in (401, 403)
                    or "401" in error_msg
                    or "403" in error_msg
                    or "unauthenticated" in error_lower
                    or "permission" in error_lower
                )
                is_bad_request = (
                    status_code == 400
                    or "400" in error_msg
                    or "invalid_argument" in error_lower
                    or "bad request" in error_lower
                    or "invalid request" in error_lower
                )
                is_not_found = (
                    status_code == 404
                    or "404" in error_msg
                    or "not_found" in error_lower
                    or "no longer available" in error_lower
                )

                if is_rate_limit:
                    rate_limit_type = classify_rate_limit_error(e)
                    if rate_limit_type == "daily_quota":
                        self.set_quota_exhausted(True, model=target_model)
                        logger.warning(
                            f"Gemini daily quota exhausted for model '{target_model}' [{type(e).__name__}]. "
                            f"No automatic retry will be performed."
                        )
                        raise GeminiQuotaExhaustedError(
                            "Gemini's current quota has been exhausted. Please try again after the quota resets."
                        )

                    # Short-term rate limit: retry with bounded exponential backoff
                    logger.warning(
                        f"Gemini short-term rate limit (429) on attempt {attempt + 1}/{self.max_retries + 1}"
                    )
                    if attempt < self.max_retries:
                        base_wait = (
                            self.backoff_seconds[attempt]
                            if attempt < len(self.backoff_seconds)
                            else self.backoff_seconds[-1]
                        )
                        wait = base_wait + 0.2  # Bounded backoff with slight jitter
                        logger.warning(f"Retrying short-term 429 in {wait:.2f}s...")
                        time.sleep(wait)
                        continue
                    else:
                        logger.error(
                            f"Gemini short-term rate limit retries exhausted ({self.max_retries}/{self.max_retries})."
                        )
                        raise GeminiRateLimitError(
                            "Gemini free-tier request limit reached. Please wait before trying again."
                        )

                if is_auth_error:
                    logger.error(f"Gemini authentication error [{type(e).__name__}]")
                    raise GeminiAuthError(
                        "Gemini authentication failed. Please verify your GEMINI_API_KEY."
                    )

                if is_bad_request:
                    logger.error(f"Gemini 400 Bad Request [{type(e).__name__}]: {error_msg[:120]}")
                    raise GeminiServiceError(f"Gemini invalid request (400): {error_msg[:200]}")

                if is_not_found:
                    logger.error(f"Gemini model not found [{type(e).__name__}]: {error_msg[:120]}")
                    raise GeminiServiceError(
                        f"Gemini model '{target_model}' not found or no longer available. "
                        "Update GEMINI_MODEL in .env."
                    )

                # Check 503 / Service Unavailable (Retryable)
                is_unavailable = (
                    status_code == 503
                    or "503" in error_msg
                    or "unavailable" in error_lower
                    or "service unavailable" in error_lower
                )

                if is_unavailable:
                    logger.warning(f"Gemini 503 received on attempt {attempt + 1}/{self.max_retries + 1}")
                    if attempt < self.max_retries:
                        wait = (
                            self.backoff_seconds[attempt]
                            if attempt < len(self.backoff_seconds)
                            else self.backoff_seconds[-1]
                        )
                        logger.warning(
                            f"Retry attempt {attempt + 1}/{self.max_retries} in {wait}s..."
                        )
                        time.sleep(wait)
                        continue
                    else:
                        logger.error(
                            f"Retries exhausted ({self.max_retries}/{self.max_retries})."
                        )
                        raise GeminiServiceUnavailableError(
                            "The AI service is temporarily unavailable. Please try again shortly."
                        )

                # Other failures: timeouts, network, generic
                if "timeout" in error_lower or "deadline" in error_lower:
                    logger.error(f"Gemini timeout [{type(e).__name__}]")
                    raise GeminiServiceError("Gemini request timed out. Please try again.")
                elif "connect" in error_lower or "network" in error_lower:
                    logger.error(f"Gemini network error [{type(e).__name__}]")
                    raise GeminiServiceError("Failed to connect to Gemini API. Check network connectivity.")
                else:
                    logger.error(f"Unexpected Gemini error [{type(e).__name__}]: {error_msg[:200]}")
                    raise GeminiServiceError(f"Gemini reasoning failed: {type(e).__name__}: {error_msg[:200]}")

    def _parse_json(self, content: str) -> Dict[str, Any]:
        """Strip markdown fences and load JSON safely."""
        clean_text = content.strip()
        clean_text = re.sub(r"^`{3}(?:json)?\s*", "", clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r"\s*`{3}$", "", clean_text)
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from Gemini response: {e}")
            raise GeminiServiceError("Received malformed JSON from Gemini model.")


gemini_service = GeminiService()
