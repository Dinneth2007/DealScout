"""Integration test: F06 against the saved Stripe dossier fixture.
Real LLM (DeepSeek), costs ~$0.03-0.09 (validation-feedback retry loop).
Run: uv run pytest tests/integration -m integration
"""
from __future__ import annotations

from pathlib import Path

import pytest

from dealscout.adapters.llm import configure_provider
from dealscout.pipelines.memo import run_memo_writer
from dealscout.rendering.markdown import render_markdown
from dealscout.rendering.pdf import render_pdf


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memo_writer_produces_valid_memo(tmp_path) -> None:
    configure_provider()
    dossier = Path("tests/fixtures/stripe_dossier.md").read_text()
    memo = await run_memo_writer(dossier)

    # Schema-level
    assert memo.recommendation in {"PASS", "TRACK", "MEET"}
    assert len(memo.strengths) == 3
    assert len(memo.concerns) == 3
    assert len(memo.references) >= 4

    # Content-level (loose)
    assert "stripe" in memo.company_name.lower()
    assert len(memo.executive_summary) >= 400

    # Renderers don't crash and produce non-trivial output
    pdf = tmp_path / "test.pdf"
    render_pdf(memo, str(pdf))
    assert pdf.exists() and pdf.stat().st_size > 5000
    md = render_markdown(memo)
    assert "## Recommendation" in md
