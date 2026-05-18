"""The only module that imports the provider SDK. Everything else depends
on the LLMClient protocol so tracing, provider switching and test fakes
attach in one place.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from agents import (
    Agent,
    OpenAIChatCompletionsModel,
    RunResult,
    Runner,
    set_default_openai_api,
    set_default_openai_client,
    set_tracing_disabled,
)
from openai import AsyncOpenAI

from dealscout.config import settings


def _provider_creds() -> tuple[str, str]:
    if settings.llm_provider == "deepseek":
        if not settings.deepseek_api_key:
            raise RuntimeError("LLM_PROVIDER=deepseek but DEEPSEEK_API_KEY is empty.")
        return settings.deepseek_api_key, settings.deepseek_base_url
    if not settings.gemini_api_key:
        raise RuntimeError("LLM_PROVIDER=gemini but GEMINI_API_KEY is empty.")
    return settings.gemini_api_key, settings.gemini_base_url


def _client() -> AsyncOpenAI:
    api_key, base_url = _provider_creds()
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


def configure_provider() -> None:
    """Point the Agents SDK at the configured provider. Call once at startup."""
    set_default_openai_client(_client())
    set_default_openai_api("chat_completions")
    set_tracing_disabled(True)  # SDK exporter targets OpenAI's backend


def build_model(model_name: str) -> OpenAIChatCompletionsModel:
    return OpenAIChatCompletionsModel(model=model_name, openai_client=_client())


@runtime_checkable
class LLMClient(Protocol):
    async def run(
        self, agent: Agent, input: str, max_turns: int | None = None
    ) -> RunResult: ...


class RealLLMClient:
    async def run(
        self, agent: Agent, input: str, max_turns: int | None = None
    ) -> RunResult:
        return await Runner.run(
            agent, input, max_turns=max_turns or settings.default_max_turns
        )


class _FakeResult:
    def __init__(self, final_output: str) -> None:
        self.final_output = final_output


class FakeLLMClient:
    """Scripted responses for unit tests, keyed by agent name."""

    def __init__(self) -> None:
        self._responses: dict[str, str] = {}

    def register(self, agent_name: str, response: str) -> None:
        self._responses[agent_name] = response

    async def run(
        self, agent: Agent, input: str, max_turns: int | None = None
    ) -> Any:
        return _FakeResult(self._responses.get(agent.name, ""))


def get_llm_client() -> LLMClient:
    return RealLLMClient()
