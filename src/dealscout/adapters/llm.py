"""THE LLM adapter — the only module that imports the provider SDK (golden rule #2).

Everything else depends on the `LLMClient` Protocol, never on `agents`/`openai`
directly. This is the single seam where tracing, retries, timeouts, provider
swapping, and test fakes attach.
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

# --- Provider wiring -------------------------------------------------------
# Called once at process startup, before any Agent is constructed. Rewires the
# SDK's default client to the selected provider's OpenAI-compatible endpoint.
# Both providers are chat-completions only; provider differs by key+base_url.


def _provider_creds() -> tuple[str, str]:
    """(api_key, base_url) for the configured provider. Fails loud if the
    selected provider's key is missing — never silently mid-call."""
    if settings.llm_provider == "deepseek":
        if not settings.deepseek_api_key:
            raise RuntimeError(
                "llm_provider=deepseek but DEEPSEEK_API_KEY is empty."
            )
        return settings.deepseek_api_key, settings.deepseek_base_url
    return settings.gemini_api_key, settings.gemini_base_url


def _client() -> AsyncOpenAI:
    api_key, base_url = _provider_creds()
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


def configure_provider() -> None:
    """Wire the Agents SDK to the selected provider. Call once at startup."""
    set_default_openai_client(_client())
    # Both Gemini and DeepSeek expose chat-completions only (no Responses API).
    set_default_openai_api("chat_completions")
    # The SDK's built-in trace exporter ships to OpenAI's backend, which 401s
    # on a non-OpenAI key. We trace via Langfuse instead, so disable it here.
    set_tracing_disabled(True)


def build_model(model_name: str) -> OpenAIChatCompletionsModel:
    """Belt-and-suspenders: an explicit provider-bound model object for an
    Agent, independent of global init order. Prefer this over a bare string.
    """
    return OpenAIChatCompletionsModel(
        model=model_name,
        openai_client=_client(),
    )


# --- Adapter protocol + impls ----------------------------------------------


@runtime_checkable
class LLMClient(Protocol):
    """Anything that can run an agent. Real or fake. Tests depend on this,
    not on Runner / AsyncOpenAI internals.
    """

    async def run(
        self, agent: Agent, input: str, max_turns: int | None = None
    ) -> RunResult: ...


class RealLLMClient:
    """Wraps Runner.run with our default turn limit (golden rule #5)."""

    async def run(
        self, agent: Agent, input: str, max_turns: int | None = None
    ) -> RunResult:
        return await Runner.run(
            agent,
            input,
            max_turns=max_turns or settings.default_max_turns,
        )


class _FakeResult:
    """Minimal RunResult stand-in. Constructing the SDK's real RunResult is
    version-coupled (the conscious residual coupling we flagged); the fake only
    needs `.final_output` for unit tests.
    """

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
    """The one place anyone instantiates a client. Factory (not a module-level
    instance) so tests can monkeypatch it cleanly.
    """
    return RealLLMClient()
