"""
StartupLens AI — LLM abstraction layer.

Exports the shared interface and the model router.
"""

from backend.llm.base import LLMProvider, LLMRequest, LLMResponse, LLMError
from backend.llm.registry import model_registry
from backend.llm.router import llm_router

__all__ = [
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "LLMError",
    "model_registry",
    "llm_router",
]
