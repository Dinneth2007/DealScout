"""Background worker: drives a job PENDING -> RUNNING -> COMPLETE/FAILED.

Runs the pipeline stage-by-stage so progress messages can be surfaced
(the pipeline doesn't yet take a progress callback — coarse stages are
enough for v1). The PIPELINE_LOCK serializes runs globally (Decision 6).
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import NamedTuple

from dealscout.domain.brief import StartupBrief
from dealscout.domain.memo import InvestmentMemo
from dealscout.pipelines.analyze import run_analysis
from dealscout.pipelines.intake import run_intake
from dealscout.pipelines.memo import run_memo_writer
from dealscout.rendering.markdown import render_markdown
from dealscout.rendering.pdf import render_pdf
from dealscout.service.jobs import PIPELINE_LOCK, JobState, JobStatus

log = logging.getLogger(__name__)


class _Result(NamedTuple):
    brief: StartupBrief
    memo: InvestmentMemo
    pdf_path: str
    markdown_path: str


async def _run_with_progress(job: JobState, output_dir: str) -> _Result:
    job_dir = Path(output_dir) / job.job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    job.progress_message = "Reading source (intake)..."
    brief = await run_intake(job.input_str)

    job.progress_message = "Researching company, market & founders (slow)..."
    analysis = await run_analysis(brief)

    job.progress_message = "Writing memo..."
    memo = await run_memo_writer(analysis.dossier_markdown)

    job.progress_message = "Rendering PDF..."
    pdf_path = str(job_dir / "memo.pdf")
    md_path = str(job_dir / "memo.md")
    render_pdf(memo, pdf_path)
    Path(md_path).write_text(render_markdown(memo))
    return _Result(brief, memo, pdf_path, md_path)


async def execute_job(job: JobState, output_dir: str = "./output") -> None:
    """Run the pipeline for a job. Never raises — failures become FAILED."""
    async with PIPELINE_LOCK:  # serialize pipeline runs (Decision 6)
        start = time.time()
        try:
            job.status = JobStatus.RUNNING
            job.progress_message = "Initializing..."
            result = await _run_with_progress(job, output_dir)

            job.pdf_path = result.pdf_path
            job.markdown_path = result.markdown_path
            job.company_name = result.memo.company_name
            job.recommendation = result.memo.recommendation
            job.cost_usd_estimate = result.memo.cost_usd_estimate
            job.latency_seconds = time.time() - start
            job.status = JobStatus.COMPLETE
            job.progress_message = "Complete"
            log.info("Job %s complete in %.1fs", job.job_id, job.latency_seconds)
        except Exception as e:  # noqa: BLE001 — worker must never propagate
            log.exception("Job %s failed", job.job_id)
            job.status = JobStatus.FAILED
            job.error_message = f"{type(e).__name__}: {e}"
            job.latency_seconds = time.time() - start
