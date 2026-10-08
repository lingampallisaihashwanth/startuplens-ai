from typing import Dict, List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Google Gemini ──────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"

    # ── Groq ──────────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = ""
    GROQ_MODEL_FAST: str = "openai/gpt-oss-20b"
    GROQ_MODEL_REASONING: str = "openai/gpt-oss-120b"

    # ── Mistral ───────────────────────────────────────────────────────────────
    MISTRAL_API_KEY: str = ""
    MISTRAL_MODEL: str = "mistral-small-latest"

    # ── Router ────────────────────────────────────────────────────────────────
    DEFAULT_MODEL: str = "auto"
    ENABLE_LLM_FALLBACK: bool = True

    # ── Tavily ────────────────────────────────────────────────────────────────
    TAVILY_API_KEY: str = ""

    # ── Infrastructure ────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./startuplens.db"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    FRONTEND_URL: Optional[str] = None
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8003",
        "http://127.0.0.1:8003",
    ]

    def get_cors_origins(self) -> List[str]:
        """Return combined list of allowed CORS origins including FRONTEND_URL."""
        origins = [o.rstrip("/") for o in self.CORS_ORIGINS]
        if self.FRONTEND_URL:
            for item in self.FRONTEND_URL.split(","):
                cleaned = item.strip().rstrip("/")
                if cleaned and cleaned not in origins:
                    origins.append(cleaned)
        return origins

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def validate_keys(self) -> Dict[str, bool]:
        """Return configured status of all external API keys (no secrets exposed)."""
        return {
            "gemini_configured": bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip()),
            "groq_configured": bool(self.GROQ_API_KEY and self.GROQ_API_KEY.strip()),
            "mistral_configured": bool(self.MISTRAL_API_KEY and self.MISTRAL_API_KEY.strip()),
            "tavily_configured": bool(self.TAVILY_API_KEY and self.TAVILY_API_KEY.strip()),
        }

    def any_llm_configured(self) -> bool:
        keys = self.validate_keys()
        return any(keys[k] for k in ("gemini_configured", "groq_configured", "mistral_configured"))


settings = Settings()
