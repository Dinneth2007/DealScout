"""Smoke test through F01: runs the full intake pipeline on a known URL.

Run: uv run python -m dealscout.smoke
Expected: a StartupBrief recognizably describing Stripe.
Side effect: a Langfuse trace showing Triage -> handoff -> URLIntake -> fetch_url.
"""
from __future__ import annotations

import asyncio

from dealscout.adapters.llm import configure_provider
from dealscout.observability.tracing import init_tracing
from dealscout.pipelines.intake import run_intake


async def main() -> None:
    configure_provider()
    init_tracing()
    brief = await run_intake("https://stripe.com")
    print(f"OK: name={brief.name!r}")
    print(f"    one_liner={brief.one_liner!r}")
    print(
        f"    headers ({len(brief.headers_or_sections)}): "
        f"{brief.headers_or_sections[:3]}"
    )
    print(f"    raw_text ({len(brief.raw_text)} chars): {brief.raw_text[:200]}...")


if __name__ == "__main__":
    asyncio.run(main())
