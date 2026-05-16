from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Reads .env at import; unknown keys ignored so .env can hold extras.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM provider: Gemini via OpenAI-compatible endpoint ---
    # required + non-empty: missing OR blank key fails loud at import,
    # never silently mid-call (doc: "no silent fallbacks for required values")
    gemini_api_key: str = Field(min_length=1)
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    # Model tier mapping. VERIFY names against Google docs; they rename often.
    # 2.0-flash free-tier quota is now 0 (Google moved free tier to 2.5) —
    # verified 2026-05 against the live /models endpoint. Use 2.5-flash.
    default_model: str = "gemini-2.5-flash"
    orchestrator_model: str = "gemini-2.5-pro"   # heavier reasoning
    researcher_model: str = "gemini-2.5-flash"   # tool-heavy, fast
    intake_model: str = "gemini-2.5-flash"

    # --- Search provider: Tavily (F02). Auth is Bearer header, not body. ---
    tavily_api_key: str = Field(min_length=1)

    # --- Observability ---
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3000"

    # --- Limits (golden rule #5: nothing unbounded) ---
    default_max_turns: int = 10
    default_tool_timeout_seconds: float = 30.0


# Singleton: validated once at import. Importing this anywhere is safe and
# turns a missing/invalid key into an immediate, legible boot failure.
settings = Settings()
