import logging
from typing import Any, Dict, List, Optional
from backend.config import settings

logger = logging.getLogger(__name__)

# Configurable Model Profiles
# Only Gemini models are supported as required.
# Reads current environment GEMINI_MODEL as primary default.
DEFAULT_ACTIVE_MODEL = settings.GEMINI_MODEL or "gemini-3.8-flash"

MODEL_PROFILES: Dict[str, Dict[str, str]] = {
    "FAST": {
        "id": "FAST",
        "name": "Gemini Flash (Fast)",
        "description": "High-speed responses with low latency for rapid iterations.",
        "model_name": "gemini-3.8-flash",
    },
    "BALANCED": {
        "id": "BALANCED",
        "name": f"Gemini Balanced ({DEFAULT_ACTIVE_MODEL})",
        "description": "Balanced intelligence and speed, optimized for research synthesis.",
        "model_name": DEFAULT_ACTIVE_MODEL,
    },
    "DEEP": {
        "id": "DEEP",
        "name": "Gemini 2.5 Pro (Deep Reasoning)",
        "description": "Comprehensive reasoning for complex multi-faceted domains.",
        "model_name": "gemini-2.5-pro",
    },
}


class ModelRouter:
    """Manages Gemini model profiles and resolution without exposing secrets or supporting non-Gemini providers."""

    def __init__(self):
        self.profiles = dict(MODEL_PROFILES)
        self.default_profile_id = "BALANCED"

    def list_models(self) -> List[Dict[str, Any]]:
        """Return user-facing model profiles with active indicator."""
        result = []
        for profile_id, data in self.profiles.items():
            result.append({
                "id": data["id"],
                "name": data["name"],
                "description": data["description"],
                "model_name": data["model_name"],
                "is_default": (profile_id == self.default_profile_id),
            })
        return result

    def resolve_model(self, model_request: Optional[str]) -> str:
        """
        Resolve requested model ID/name to a valid Gemini model name.
        If user explicitly requested a profile (e.g. FAST, BALANCED, DEEP), return its exact model_name.
        If user passed a direct Gemini model string (e.g. gemini-2.5-flash), validate that it's Gemini.
        If None or empty, return the default model profile.
        If explicit invalid model is requested, raise ValueError (do NOT silently switch models).
        """
        if not model_request or model_request.strip().upper() == "AUTO":
            return self.profiles[self.default_profile_id]["model_name"]

        key = model_request.strip().upper()
        if key in self.profiles:
            return self.profiles[key]["model_name"]

        req_clean = model_request.strip().lower()
        # Direct model name check
        if req_clean.startswith("gemini"):
            return req_clean

        # Check by model_name in profiles
        for data in self.profiles.values():
            if data["model_name"].lower() == req_clean:
                return data["model_name"]

        raise ValueError(
            f"Invalid Gemini model '{model_request}'. "
            f"Available profiles: {', '.join(self.profiles.keys())} or direct Gemini model names."
        )


model_router = ModelRouter()
