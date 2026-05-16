"""Integration tests for the F01 intake pipeline. Real Gemini — costs money.
Run: uv run pytest tests/integration -m integration
"""
from __future__ import annotations

import pathlib

import pytest

from dealscout.adapters.llm import configure_provider
from dealscout.pipelines.intake import run_intake


@pytest.mark.integration
@pytest.mark.asyncio
async def test_intake_url_produces_valid_brief() -> None:
    configure_provider()
    brief = await run_intake("https://stripe.com")
    assert brief.source_type == "url"
    assert len(brief.name) > 0
    assert len(brief.raw_text) > 200
    assert brief.one_liner != ""


@pytest.mark.integration
@pytest.mark.asyncio
async def test_intake_pdf_produces_valid_brief() -> None:
    fixture = pathlib.Path("tests/fixtures/sample_deck.pdf")
    if not fixture.exists():
        pytest.skip("sample_deck.pdf fixture not present")
    configure_provider()
    brief = await run_intake(str(fixture))
    assert brief.source_type == "pdf"
    assert len(brief.name) > 0
