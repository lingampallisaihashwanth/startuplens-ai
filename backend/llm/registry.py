"""
StartupLens AI — Model registry.

Central source of truth for all supported models and their metadata.
The registry reads from environment variables at import time so that
only keys that are actually configured produce enabled entries.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from backend.config import settings

logger = logging.getLogger(__name__)

# ── Model definitions ──────────────────────────────────────────────────────────
# Each entry follows the spec in the architecture requirements.
# 'enabled' is computed dynamically from env vars (see _build_registry below).

_MODEL_SPECS: List[Dict[str, Any]] = [
    # ── Auto ──────────────────────────────────────────────────────────────────
    {
        "id": "auto",
        "display_name": "Auto",
        "provider": "router",
        "model_name": None,
        "speed": "auto",
        "reasoning_level": "auto",
        "fallback_priority": 0,
        "requires_key": None,   # Always "enabled" — router decides
    },
    # ── Google Gemini ──────────────────────────────────────────────────────────
    {
        "id": "gemini-balanced",
        "display_name": "Gemini Balanced",
        "provider": "gemini",
        "provider_label": "Google Gemini",
        "model_name": None,  # filled from settings.GEMINI_MODEL at load time
        "speed": "balanced",
        "reasoning_level": "standard",
        "fallback_priority": 1,
        "requires_key": "GEMINI_API_KEY",
    },
    # ── Groq ──────────────────────────────────────────────────────────────────
    {
        "id": "groq-fast",
        "display_name": "Groq Fast",
        "provider": "groq",
        "provider_label": "Groq",
        "model_name": None,  # filled from settings.GROQ_MODEL_FAST
        "speed": "fast",
        "reasoning_level": "standard",
        "fallback_priority": 2,
        "requires_key": "GROQ_API_KEY",
    },
    {
        "id": "groq-reasoning",
        "display_name": "Groq Reasoning",
        "provider": "groq",
        "provider_label": "Groq",
        "model_name": None,  # filled from settings.GROQ_MODEL_REASONING
        "speed": "balanced",
        "reasoning_level": "high",
        "fallback_priority": 3,
        "requires_key": "GROQ_API_KEY",
    },
    # ── Mistral ───────────────────────────────────────────────────────────────
    {
        "id": "mistral-small",
        "display_name": "Mistral Small",
        "provider": "mistral",
        "provider_label": "Mistral",
        "model_name": None,  # filled from settings.MISTRAL_MODEL
        "speed": "fast",
        "reasoning_level": "standard",
        "fallback_priority": 4,
        "requires_key": "MISTRAL_API_KEY",
    },
]


def _build_registry() -> Dict[str, Dict[str, Any]]:
    """
    Build the live model registry by resolving model names and
    computing enabled status from current environment settings.
    """
    registry: Dict[str, Dict[str, Any]] = {}

    for spec in _MODEL_SPECS:
        entry = dict(spec)
        model_id = entry["id"]

        # Resolve model_name from settings
        if model_id == "gemini-balanced":
            entry["model_name"] = settings.GEMINI_MODEL or "gemini-3.8-flash"
        elif model_id == "groq-fast":
            entry["model_name"] = settings.GROQ_MODEL_FAST or "openai/gpt-oss-20b"
        elif model_id == "groq-reasoning":
            entry["model_name"] = settings.GROQ_MODEL_REASONING or "openai/gpt-oss-120b"
        elif model_id == "mistral-small":
            entry["model_name"] = settings.MISTRAL_MODEL or "mistral-small-latest"

        # Compute enabled
        requires_key = entry.get("requires_key")
        if requires_key is None:
            # "auto" and router-level entries are always present
            entry["enabled"] = True
        else:
            key_value: str = getattr(settings, requires_key, "") or ""
            entry["enabled"] = bool(key_value.strip())

        registry[model_id] = entry

    return registry


class ModelRegistry:
    """
    Central model registry — read-only after construction.
    Rebuilt each time get_model() or list_models() is called if needed,
    but for simplicity we build once at import and expose a refresh() method.
    """

    def __init__(self) -> None:
        self._registry: Dict[str, Dict[str, Any]] = _build_registry()

    def refresh(self) -> None:
        """Re-read environment and rebuild the registry (useful in tests)."""
        self._registry = _build_registry()

    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Return a model entry or None if not found."""
        return self._registry.get(model_id)

    def list_models(self, only_enabled: bool = True) -> List[Dict[str, Any]]:
        """
        Return a list of model entries.
        By default only returns models whose API key is configured.
        'auto' is always included.
        """
        result = []
        for entry in self._registry.values():
            if only_enabled and not entry.get("enabled", False):
                continue
            result.append(entry)
        return result

    def is_known(self, model_id: str) -> bool:
        return model_id in self._registry

    def is_enabled(self, model_id: str) -> bool:
        entry = self._registry.get(model_id)
        if entry is None:
            return False
        return bool(entry.get("enabled", False))

    def get_default_model_id(self) -> str:
        """Return DEFAULT_MODEL from settings, fallback to 'auto'."""
        default = (settings.DEFAULT_MODEL or "auto").strip().lower()
        if self.is_known(default) and self.is_enabled(default):
            return default
        # Fall back to gemini-balanced if configured, then auto
        if self.is_enabled("gemini-balanced"):
            return "gemini-balanced"
        return "auto"

    def get_provider_for_model(self, model_id: str) -> Optional[str]:
        entry = self._registry.get(model_id)
        if entry is None:
            return None
        return entry.get("provider")

    def list_enabled_provider_ids(self) -> List[str]:
        """Return unique provider names that have at least one enabled model."""
        providers = set()
        for entry in self._registry.values():
            if entry.get("enabled") and entry.get("provider") not in (None, "router"):
                providers.add(entry["provider"])
        return list(providers)


# Singleton
model_registry = ModelRegistry()
