"""Smoke test through F02: full intake + company research."""
from __future__ import annotations

import asyncio

from dealscout.adapters.llm import configure_provider
from dealscout.observability.tracing import init_tracing
from dealscout.pipelines.intake import run_intake
from dealscout.pipelines.research import run_company_research


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


if __name__ == "__main__":
    asyncio.run(main())
