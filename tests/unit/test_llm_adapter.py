"""Unit tests: no network, no spend. Depend on our Protocol, not the SDK."""
from __future__ import annotations

import pytest

from dealscout.adapters.llm import FakeLLMClient, LLMClient


def test_fake_llm_client_satisfies_protocol() -> None:
    assert isinstance(FakeLLMClient(), LLMClient)


@pytest.mark.asyncio
async def test_fake_returns_registered_response() -> None:
    fake = FakeLLMClient()
    fake.register("Researcher", "scripted answer")

    class _A:
        name = "Researcher"

    result = await fake.run(_A(), "anything")
    assert result.final_output == "scripted answer"


@pytest.mark.asyncio
async def test_fake_unknown_agent_returns_empty() -> None:
    class _A:
        name = "Unknown"

    result = await FakeLLMClient().run(_A(), "anything")
    assert result.final_output == ""
