"""Integration test: full F05 pipeline. Real LLM + Tavily, costs money.
Run: uv run pytest tests/integration -m integration

NOTE: this goes through run_intake first, which currently has a known
fragility (LLM echoing large raw_text into JSON → invalid escapes) that is
NOT an F05 defect. Until the F01 intake fix lands this test can fail at
intake; F05 itself is verified separately via a synthetic brief.
"""
from __future__ import annotations

import pytest

from dealscout.adapters.llm import configure_provider
from dealscout.pipelines.analyze import run_analysis
from dealscout.pipelines.intake import run_intake


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_produces_full_dossier() -> None:
    configure_provider()
    brief = await run_intake("https://stripe.com")
    result = await run_analysis(brief)
    d = result.dossier_markdown

    # Structural checks
    assert "at-a-glance" in d.lower()
    assert "strongest" in d.lower()
    assert "concerning" in d.lower() or "concerns" in d.lower()
    assert "confidence" in d.lower()
    assert "open questions" in d.lower()

    # Quality proxies
    assert d.count("[") >= 8  # citation markers aggregated from 3 researchers
    assert len(d) > 2000  # substantive synthesis, not a stub
