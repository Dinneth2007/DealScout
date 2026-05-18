from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: Literal["gemini", "deepseek"] = "gemini"

    # Provider keys are optional here; the active provider's key is
    # required at startup (see adapters.llm).
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"

    default_model: str = "gemini-2.5-flash"
    orchestrator_model: str = "gemini-2.5-pro"
    researcher_model: str = "gemini-2.5-flash"
    intake_model: str = "gemini-2.5-flash"

    tavily_api_key: str = Field(min_length=1)

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3000"

    default_max_turns: int = 10
    default_tool_timeout_seconds: float = 30.0


settings = Settings()
