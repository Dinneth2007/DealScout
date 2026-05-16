"""Integration test: real Gemini + Tavily. Costs money / quota.
Run: uv run pytest tests/integration -m integration
"""
from __future__ import annotations

import pytest

from dealscout.adapters.llm import configure_provider
from dealscout.pipelines.intake import run_intake
from dealscout.pipelines.research import run_company_research


@pytest.mark.integration
@pytest.mark.asyncio
async def test_company_researcher_produces_notes_with_citations() -> None:
    configure_provider()
    brief = await run_intake("https://stripe.com")
    notes = await run_company_research(brief)
    assert "## References" in notes
    assert notes.count("[") >= 3  # at least 3 citation markers
    assert "Open questions" in notes
