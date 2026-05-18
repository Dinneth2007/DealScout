"""Smoke test for F06: feed a saved F05 dossier through Memo Writer + renderer.

Decoupled from the live pipeline so F06 is testable without intake/F05.
Run: uv run python -m dealscout.smoke_memo
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from dealscout.adapters.llm import configure_provider
from dealscout.observability.tracing import init_tracing
from dealscout.pipelines.memo import run_memo_writer
from dealscout.rendering.markdown import render_markdown
from dealscout.rendering.pdf import render_pdf


async def main() -> None:
    configure_provider()
    init_tracing()

    dossier = Path("tests/fixtures/stripe_dossier.md").read_text()

    print("Running Memo Writer...")
    memo = await run_memo_writer(dossier)
    print(f"OK — memo for {memo.company_name}")
    print(f"   Recommendation: {memo.recommendation}")
    print(f"   Strengths: {len(memo.strengths)}, Concerns: {len(memo.concerns)}")
    print(f"   Founders: {len(memo.founders_detail)}, "
          f"References: {len(memo.references)}")

    pdf_path = "/tmp/smoke_memo.pdf"
    md_path = "/tmp/smoke_memo.md"
    render_pdf(memo, pdf_path)
    Path(md_path).write_text(render_markdown(memo))
    print(f"\nPDF: {pdf_path} ({Path(pdf_path).stat().st_size} bytes)")
    print(f"MD:  {md_path}")


if __name__ == "__main__":
    asyncio.run(main())
