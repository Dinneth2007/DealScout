"""Smoke test through F03: full intake + company + market research."""
from __future__ import annotations

import asyncio

from dealscout.adapters.llm import configure_provider
from dealscout.observability.tracing import init_tracing
from dealscout.pipelines.intake import run_intake
from dealscout.pipelines.research import (
    run_company_research,
    run_founder_research,
    run_market_research,
)


async def main() -> None:
    configure_provider()
    init_tracing()

    brief = await run_intake("https://stripe.com")
    print("\n=== INTAKE ===")
    print(f"Name: {brief.name}")
    print(f"One-liner: {brief.one_liner}\n")

    notes = await run_company_research(brief)
    print("=== COMPANY RESEARCH ===\n")
    print(notes)

    notes_market = await run_market_research(brief)
    print("\n=== MARKET RESEARCH ===\n")
    print(notes_market)

    notes_founders = await run_founder_research(brief)
    print("\n=== FOUNDER RESEARCH ===\n")
    print(notes_founders)


if __name__ == "__main__":
    asyncio.run(main())
