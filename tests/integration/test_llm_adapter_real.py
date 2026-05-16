"""Integration test: real Gemini call. Costs money (Gemini free tier ok).
Run explicitly: uv run pytest tests/integration -m integration
"""
from __future__ import annotations

import pytest

from agents import Agent

from dealscout.adapters.llm import build_model, configure_provider, get_llm_client
from dealscout.config import settings


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_gemini_responds() -> None:
    configure_provider()
    agent = Agent(
        name="TestAgent",
        instructions="Reply with the single word 'pong'.",
        model=build_model(settings.default_model),
    )
    result = await get_llm_client().run(agent, "ping")
    assert "pong" in result.final_output.lower()
