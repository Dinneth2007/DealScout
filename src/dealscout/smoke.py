"""Smoke test: prove the LLM adapter works end-to-end with Gemini.

Run:  uv run python -m dealscout.smoke
Expected: 'OK: response received from <model>' + the model's reply.
Side effect: a Langfuse trace if keys are configured.
"""
from __future__ import annotations

import asyncio

from agents import Agent

from dealscout.adapters.llm import build_model, configure_provider, get_llm_client
from dealscout.config import settings
from dealscout.observability.tracing import init_tracing


async def main() -> None:
    configure_provider()  # wire SDK -> Gemini (must run before Agent use)
    init_tracing()        # wire Langfuse (no-op if keys missing)

    agent = Agent(
        name="SmokeTestAgent",
        instructions="You are a helpful assistant. Reply in one short sentence.",
        model=build_model(settings.default_model),
    )
    result = await get_llm_client().run(agent, "Say 'hello' and the word 'OK'.")
    print(f"OK: response received from {settings.default_model}")
    print(f"Output: {result.final_output}")


if __name__ == "__main__":
    asyncio.run(main())
