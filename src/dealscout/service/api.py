"""FastAPI service: submit a job, poll status, download the memo.

/analyze returns immediately (Decision 2); the pipeline runs in a
fire-and-forget task whose actual execution is serialized by the
semaphore inside execute_job.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from dealscout.adapters.llm import configure_provider
from dealscout.observability.tracing import init_tracing
from dealscout.service.jobs import JOBS, JobStatus, create_job, get_job
from dealscout.service.worker import execute_job


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_provider()  # wire LLM provider once for the process
    init_tracing()
    yield


app = FastAPI(title="DealScout", version="1.0", lifespan=lifespan)


class AnalyzeRequest(BaseModel):
    input: str  # URL or local PDF path


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress_message: str = ""
    company_name: str | None = None
    recommendation: str | None = None
    cost_usd_estimate: float | None = None
    latency_seconds: float | None = None
    error_message: str | None = None
    pdf_url: str | None = None
    markdown_url: str | None = None


def _to_response(job) -> JobResponse:
    done = job.status == JobStatus.COMPLETE
    return JobResponse(
        job_id=job.job_id,
        status=job.status,
        progress_message=job.progress_message,
        company_name=job.company_name,
        recommendation=job.recommendation,
        cost_usd_estimate=job.cost_usd_estimate,
        latency_seconds=job.latency_seconds,
        error_message=job.error_message,
        pdf_url=f"/memos/{job.job_id}/pdf" if done else None,
        markdown_url=f"/memos/{job.job_id}/markdown" if done else None,
    )


@app.post("/analyze", response_model=JobResponse)
async def analyze(req: AnalyzeRequest) -> JobResponse:
    job = create_job(req.input)
    asyncio.create_task(execute_job(job))  # fire-and-forget; returns now
    return _to_response(job)


@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_endpoint(job_id: str) -> JobResponse:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return _to_response(job)


@app.get("/memos/{job_id}/pdf")
async def get_memo_pdf(job_id: str):
    job = get_job(job_id)
    if job is None or job.status != JobStatus.COMPLETE or job.pdf_path is None:
        raise HTTPException(status_code=404, detail="Memo not ready")
    return FileResponse(
        job.pdf_path, media_type="application/pdf",
        filename=f"dealscout_{job.company_name or 'memo'}.pdf",
    )


@app.get("/memos/{job_id}/markdown")
async def get_memo_markdown(job_id: str):
    job = get_job(job_id)
    if job is None or job.status != JobStatus.COMPLETE or job.markdown_path is None:
        raise HTTPException(status_code=404, detail="Memo not ready")
    return FileResponse(
        job.markdown_path, media_type="text/markdown",
        filename=f"dealscout_{job.company_name or 'memo'}.md",
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "jobs_in_progress": sum(
            1 for j in JOBS.values() if j.status == JobStatus.RUNNING
        ),
    }
