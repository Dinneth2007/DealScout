"""Integration test: real LLM + Tavily. Costs quota.
Run: uv run pytest tests/integration -m integration
"""
from __future__ import annotations

import pytest

from dealscout.adapters.llm import configure_provider
from dealscout.pipelines.intake import run_intake
from dealscout.pipelines.research import run_founder_research


@pytest.mark.integration
@pytest.mark.asyncio
async def test_founder_researcher_names_founders() -> None:
    configure_provider()
    brief = await run_intake("https://stripe.com")
    notes = await run_founder_research(brief)
    assert "Collison" in notes  # known-good case
    assert "## References" in notes
