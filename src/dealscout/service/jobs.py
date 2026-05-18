"""In-memory job store + global concurrency guard.

Single-process, not multi-worker safe (Decision 5/6). A server restart
loses in-flight jobs — acceptable for the v1 demo, documented in the doc.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class JobState:
    job_id: str
    status: JobStatus
    submitted_at: datetime
    input_str: str
    progress_message: str = ""
    error_message: str | None = None
    pdf_path: str | None = None
    markdown_path: str | None = None
    company_name: str | None = None
    recommendation: str | None = None
    cost_usd_estimate: float | None = None
    latency_seconds: float | None = None


# In-memory store. Single process; not multi-worker safe.
JOBS: dict[str, JobState] = {}

# Concurrency guard (Decision 6): only one pipeline run at a time globally.
PIPELINE_LOCK = asyncio.Semaphore(1)


def new_job_id() -> str:
    return uuid.uuid4().hex[:12]


def create_job(input_str: str) -> JobState:
    job = JobState(
        job_id=new_job_id(),
        status=JobStatus.PENDING,
        submitted_at=datetime.now(tz=timezone.utc),
        input_str=input_str,
    )
    JOBS[job.job_id] = job
    return job


def get_job(job_id: str) -> JobState | None:
    return JOBS.get(job_id)
