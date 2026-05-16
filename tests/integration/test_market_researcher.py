"""Integration test: real LLM + Tavily. Costs quota.
Run: uv run pytest tests/integration -m integration
"""
from __future__ import annotations

import pytest

from dealscout.adapters.llm import configure_provider
from dealscout.pipelines.intake import run_intake
from dealscout.pipelines.research import run_market_research


@pytest.mark.integration
@pytest.mark.asyncio
async def test_market_researcher_includes_competitors() -> None:
    configure_provider()
    brief = await run_intake("https://stripe.com")
    notes = await run_market_research(brief)
    assert "## References" in notes
    assert notes.count("[") >= 3
    assert "Open questions" in notes
