"""Smoke test through F05: intake + full orchestrated research."""
from __future__ import annotations

import asyncio
import time

from dealscout.adapters.llm import configure_provider
from dealscout.observability.tracing import init_tracing
from dealscout.pipelines.analyze import run_analysis
from dealscout.pipelines.intake import run_intake


async def main() -> None:
    configure_provider()
    init_tracing()

    started = time.time()
    brief = await run_intake("https://stripe.com")
    print(f"\n=== INTAKE ({time.time() - started:.1f}s) ===")
    print(f"Name: {brief.name}")
    print(f"One-liner: {brief.one_liner}\n")

    started_analysis = time.time()
    result = await run_analysis(brief)
    analysis_elapsed = time.time() - started_analysis
    total = time.time() - started

    print(f"=== SYNTHESIZED DOSSIER ({analysis_elapsed:.1f}s) ===\n")
    print(result.dossier_markdown)
    print(f"\n=== TOTAL: {total:.1f}s ===")


if __name__ == "__main__":
    asyncio.run(main())
