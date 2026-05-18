# F10 — FastAPI Service + Gradio UI

**Phase:** 7 — Productionization
**Depends on:** F06 (full pipeline runs end-to-end)
**Blocks:** F11 (deployment needs a deployable service)
**Estimated time:** 1 long session (3–4 hours)
**LLM cost:** $0 for development; ~$0.60 budgeted for demo runs after

---

## Why this feature exists

You have a working pipeline. You don't have a *product*. The difference is that a product can be *used by someone who isn't you* — paste a URL, get a PDF, no terminal required.

F10 wraps the pipeline in two layers:

1. **A FastAPI service** that exposes `POST /analyze` (start a job) and `GET /jobs/{id}` (check status, download memo).
2. **A Gradio UI** that calls the service so a non-technical user can submit URLs and download PDFs through a browser.

There's a real architectural decision driving this shape: **memos take ~4 minutes to generate**, which means you cannot make the user wait synchronously on an HTTP request. F10's central problem is *managing long-running jobs gracefully*.

---

## Mental model

### Why two services, not one

A naive design would be: Gradio app calls the pipeline directly, shows a spinner, returns the PDF. This works locally but breaks in production for three reasons:

- **Gradio is a UI framework, not a job runner.** Long-running operations inside Gradio handlers block the UI for everyone.
- **You can't share state between users.** If two people submit URLs simultaneously, Gradio's per-request model gets confused.
- **No API for non-UI clients.** You'd want to demo by curl-ing the service from the terminal, or have a recruiter test it from Postman. That requires a real API.

The two-service split makes both pieces simple:

```
  Browser
     │
     ▼  HTTP  (port 7860)
  ┌────────────┐
  │   Gradio   │   Job submission, progress polling, PDF display
  │  (front)   │
  └─────┬──────┘
        │  HTTP  (port 8000)
        ▼
  ┌────────────┐
  │  FastAPI   │   /analyze (POST), /jobs/{id} (GET), /memos/{id} (GET)
  │  (back)    │   In-memory job queue, async worker
  └─────┬──────┘
        │
        ▼
   DealScout pipeline (intake → research → memo → render)
```

Gradio is dumb about pipelines. FastAPI is dumb about UI. Neither knows about the other beyond the HTTP contract. That separation is what makes both easy to test, easy to swap, easy to deploy.

### Why in-memory job queue (not Celery/RQ/Redis)

For F10's scope we use a simple Python dict + asyncio task pattern:

```python
JOBS: dict[str, JobState] = {}  # job_id → JobState
```

This is fine because:
- DealScout v1 has one user at a time (you, or a demo viewer).
- Memos are rare events (~one per minute peak), not high-throughput.
- The server is a single process — no need for shared state across workers.

The cost: if the server restarts mid-job, the job is lost. Acceptable for a demo. If DealScout ever needed real concurrency, you'd swap the in-memory queue for Redis + a worker pool. The interface (`enqueue_job`, `get_job_state`) stays the same. **That swap is a future feature; for F10 the simple thing is correct.**

### The job lifecycle

Every job moves through these states:

```
PENDING → RUNNING → COMPLETE
                 ↘
                   FAILED
```

- `PENDING`: queued, hasn't started
- `RUNNING`: pipeline is executing (may include progress: "researching company", "writing memo")
- `COMPLETE`: memo PDF + Markdown available for download
- `FAILED`: pipeline raised; error message stored

Gradio polls `GET /jobs/{id}` every 5 seconds to update the UI. When state is `COMPLETE`, Gradio shows the download button. When state is `FAILED`, it shows the error.

---

## Key design decisions

### Decision 1 — Async-first throughout

**What:** FastAPI handlers are `async def`. Pipeline calls use `asyncio.create_task` to run in the background.

**Why:** Memo generation is I/O-bound (LLM calls, web searches). Sync code would block one request per process. Async lets one Python process handle the Gradio polling traffic while the pipeline runs.

**How it would burn you:** Sync FastAPI handlers + a sync pipeline = one Gunicorn worker handles exactly one user at a time. Even with two demo viewers, the second one's polling requests time out. Async fixes this for free.

**Transferable principle:** *I/O-bound LLM systems are async-first by default.* The async overhead pays for itself the moment you have one concurrent user.

### Decision 2 — Jobs return immediately; polling fetches state

**What:** `POST /analyze` returns `{job_id, status}` in <100ms. The pipeline runs in a background task. The client polls `GET /jobs/{id}`.

**Why:** A 4-minute synchronous HTTP request will time out somewhere in the chain — at the browser, at the reverse proxy (Render/Fly have ~30s defaults), or at FastAPI itself. Async + polling is the only shape that works in production.

**How it would burn you:** Try to return the memo directly from `/analyze` and your service will work locally but fail the moment it's deployed behind any production proxy.

**Transferable principle:** *Long-running operations need explicit job semantics, not synchronous HTTP.* This applies to any operation that takes >10s — file processing, batch operations, training jobs, anything LLM-multi-agent.

### Decision 3 — Progress updates via job state, not WebSockets/SSE

**What:** The pipeline writes progress strings to `JOBS[job_id].progress_message` ("Researching company...", "Writing memo..."). Gradio polls every 5s and re-renders.

**Why:** WebSockets or Server-Sent Events would give real-time updates but add complexity (connection management, reconnection logic, proxy compatibility). Polling at 5s gives effectively-real-time UX for a 4-minute operation, with zero complexity overhead.

**How it would burn you:** WebSocket setup time + debugging time will exceed the entire F10 budget. The user-visible improvement from polling-at-5s to WebSocket-real-time on a 4-minute job is approximately zero.

**Transferable principle:** *Match update granularity to operation duration.* Real-time updates matter for sub-second operations. For minute-scale operations, polling at single-digit seconds is indistinguishable from real-time.

### Decision 4 — Gradio for v1, not Next.js or Streamlit

**What:** Gradio. Not React, not Streamlit, not a custom HTML page.

**Why:** Gradio gives you a usable UI in ~50 lines of Python. No build step, no separate frontend repo, no React state management. For a portfolio project where the UI is *evidence the system works*, not the differentiator, that's the right trade-off.

**How it would burn you:** Going with Next.js would add a week of work for a UI that doesn't make the project more impressive. The story you want to tell is "I built a multi-agent system" — not "I built a multi-agent system *and* a frontend."

**Transferable principle:** *Match UI investment to UI's contribution to the story.* When the UI is the demonstration, not the product, simple wins.

### Decision 5 — File-system storage for memos, not a database

**What:** Generated PDFs and Markdown files live in `./output/<job_id>/memo.pdf`. The job record stores the path.

**Why:** Adding Postgres for v1 is over-engineering. The filesystem is durable for the demo's purposes, and the deployment platform (Render/Fly) preserves the disk across requests. If we needed multi-server replication, we'd move to S3 + a metadata DB — but we don't.

**How it would burn you:** Premature database = setup time, schema migrations, ORM bugs. For DealScout's read pattern (write once per memo, read once per download), the filesystem is faster and simpler.

**Transferable principle:** *Add stateful infrastructure when the cost of not having it exceeds the cost of having it.* Right now, that calculus favors files.

### Decision 6 — One job at a time globally (concurrency guard)

**What:** A module-level `asyncio.Semaphore(1)` ensures only one pipeline run executes at a time, even if multiple jobs are submitted.

**Why:** Two concurrent pipeline runs would (a) double the Tavily/LLM cost burst, possibly hitting rate limits, and (b) make traces harder to read in Langfuse. For v1, serial is fine. The job queue still works — jobs wait in PENDING until the semaphore frees.

**How it would burn you:** No semaphore + a demo viewer who clicks "analyze" three times rapidly = three parallel pipelines, three burst rate-limit hits, three angry-looking failures. The semaphore is one line of code that prevents this.

**Transferable principle:** *Bound your concurrency explicitly. Default to 1 when you can.* Increase only when you have evidence the system handles parallelism cleanly.

---

## Build order

### Step 1 — Add dependencies

```bash
uv add fastapi uvicorn[standard] gradio
```

Verify they install cleanly and don't conflict with existing pins.

### Step 2 — Job state module

```python
# src/dealscout/service/jobs.py
from __future__ import annotations
import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


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
    error_message: Optional[str] = None
    pdf_path: Optional[str] = None
    markdown_path: Optional[str] = None
    company_name: Optional[str] = None
    recommendation: Optional[str] = None
    cost_usd_estimate: Optional[float] = None
    latency_seconds: Optional[float] = None


# In-memory store. Single process; not multi-worker safe.
JOBS: dict[str, JobState] = {}

# Concurrency guard — see Decision 6.
PIPELINE_LOCK = asyncio.Semaphore(1)


def new_job_id() -> str:
    return uuid.uuid4().hex[:12]


def create_job(input_str: str) -> JobState:
    job = JobState(
        job_id=new_job_id(),
        status=JobStatus.PENDING,
        submitted_at=datetime.utcnow(),
        input_str=input_str,
    )
    JOBS[job.job_id] = job
    return job


def get_job(job_id: str) -> Optional[JobState]:
    return JOBS.get(job_id)
```

**Acceptance:** importable, `create_job("https://stripe.com")` returns a `JobState`, `get_job(id)` retrieves it.

### Step 3 — Background worker

The worker is the function that takes a job from PENDING through to COMPLETE/FAILED. It writes progress along the way.

```python
# src/dealscout/service/worker.py
from __future__ import annotations
import time
import logging
from datetime import datetime
from dealscout.adapters.llm import configure_provider
from dealscout.observability.tracing import init_tracing
from dealscout.pipelines.analyze import run_full_analysis
from dealscout.service.jobs import JobState, JobStatus, PIPELINE_LOCK

log = logging.getLogger(__name__)


async def execute_job(job: JobState, output_dir: str = "./output") -> None:
    """Run the pipeline for a job. Updates job state as it goes.
    Never raises — failures become FAILED status with error_message."""

    async with PIPELINE_LOCK:   # serialize pipeline runs
        start = time.time()
        try:
            job.status = JobStatus.RUNNING
            job.progress_message = "Initializing..."

            # The pipeline emits progress through these messages.
            # In a richer implementation we'd pass callbacks into run_full_analysis
            # to update progress at each stage. For v1, three coarse updates is enough.
            job.progress_message = "Reading source..."
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
        except Exception as e:
            log.exception("Job %s failed", job.job_id)
            job.status = JobStatus.FAILED
            job.error_message = f"{type(e).__name__}: {e}"
            job.latency_seconds = time.time() - start


async def _run_with_progress(job: JobState, output_dir: str):
    """Wrap run_full_analysis with stage progress updates.

    The cleanest design here would be to refactor run_full_analysis to accept
    a progress callback. For v1, we use a simpler trick: we manually run the
    three stages and update progress between them.
    """
    from dealscout.pipelines.intake import run_intake
    from dealscout.pipelines.analyze import run_analysis
    from dealscout.pipelines.memo import run_memo_writer
    from dealscout.rendering.pdf import render_pdf
    from dealscout.rendering.markdown import render_markdown
    from pathlib import Path
    from collections import namedtuple

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    job_dir = Path(output_dir) / job.job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    job.progress_message = "Reading source (intake)..."
    brief = await run_intake(job.input_str)

    job.progress_message = "Researching (this is the slow part)..."
    analysis = await run_analysis(brief)

    job.progress_message = "Writing memo..."
    memo = await run_memo_writer(analysis.dossier_markdown)

    job.progress_message = "Rendering PDF..."
    pdf_path = str(job_dir / "memo.pdf")
    md_path = str(job_dir / "memo.md")
    render_pdf(memo, pdf_path)
    Path(md_path).write_text(render_markdown(memo))

    Result = namedtuple("Result", "brief dossier memo pdf_path markdown_path")
    return Result(brief, analysis.dossier_markdown, memo, pdf_path, md_path)
```

**Acceptance:** `await execute_job(create_job("https://stripe.com"))` runs the pipeline, updates job state through stages, and produces files at `./output/<job_id>/memo.{pdf,md}`. On a known-bad URL, status becomes FAILED with a sensible error.

### Step 4 — FastAPI service

```python
# src/dealscout/service/api.py
from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dealscout.adapters.llm import configure_provider
from dealscout.observability.tracing import init_tracing
from dealscout.service.jobs import JOBS, JobStatus, create_job, get_job
from dealscout.service.worker import execute_job


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: wire up the LLM provider once for the process.
    configure_provider()
    init_tracing()
    yield
    # Shutdown: nothing to do for in-memory queue.


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


@app.post("/analyze", response_model=JobResponse)
async def analyze(req: AnalyzeRequest) -> JobResponse:
    """Enqueue an analysis. Returns immediately with the job ID.
    Client polls /jobs/{id} to check status."""
    job = create_job(req.input)
    # Fire-and-forget background task. The Semaphore in execute_job
    # serializes actual pipeline runs.
    asyncio.create_task(execute_job(job))
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
    return FileResponse(job.pdf_path, media_type="application/pdf",
                        filename=f"dealscout_{job.company_name or 'memo'}.pdf")


@app.get("/memos/{job_id}/markdown")
async def get_memo_markdown(job_id: str):
    job = get_job(job_id)
    if job is None or job.status != JobStatus.COMPLETE or job.markdown_path is None:
        raise HTTPException(status_code=404, detail="Memo not ready")
    return FileResponse(job.markdown_path, media_type="text/markdown",
                        filename=f"dealscout_{job.company_name or 'memo'}.md")


@app.get("/health")
async def health():
    return {"status": "ok", "jobs_in_progress": sum(
        1 for j in JOBS.values() if j.status == JobStatus.RUNNING)}


def _to_response(job) -> JobResponse:
    pdf_url = f"/memos/{job.job_id}/pdf" if job.status == JobStatus.COMPLETE else None
    md_url = f"/memos/{job.job_id}/markdown" if job.status == JobStatus.COMPLETE else None
    return JobResponse(
        job_id=job.job_id, status=job.status, progress_message=job.progress_message,
        company_name=job.company_name, recommendation=job.recommendation,
        cost_usd_estimate=job.cost_usd_estimate, latency_seconds=job.latency_seconds,
        error_message=job.error_message, pdf_url=pdf_url, markdown_url=md_url,
    )
```

**Acceptance:** `uv run uvicorn dealscout.service.api:app --port 8000` starts cleanly. `curl -X POST http://localhost:8000/analyze -H "Content-Type: application/json" -d '{"input": "https://stripe.com"}'` returns a `job_id` immediately. Polling `curl http://localhost:8000/jobs/<id>` shows status transitions. After ~4 minutes, downloading `/memos/<id>/pdf` returns the file.

### Step 5 — Gradio UI

```python
# src/dealscout/service/ui.py
from __future__ import annotations
import time
import httpx
import gradio as gr

API_BASE = "http://localhost:8000"
POLL_INTERVAL_SECONDS = 5


def submit_and_wait(input_str: str, progress=gr.Progress()):
    """Submit an analysis, poll until complete, return PDF + memo summary."""
    if not input_str or not input_str.strip():
        return None, None, "Please enter a URL or PDF path.", ""

    # Submit
    progress(0, desc="Submitting...")
    try:
        r = httpx.post(f"{API_BASE}/analyze", json={"input": input_str}, timeout=10)
        r.raise_for_status()
        job_id = r.json()["job_id"]
    except httpx.HTTPError as e:
        return None, None, f"Failed to submit job: {e}", ""

    # Poll
    started = time.time()
    while True:
        try:
            r = httpx.get(f"{API_BASE}/jobs/{job_id}", timeout=10)
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPError as e:
            return None, None, f"Polling error: {e}", ""

        elapsed = time.time() - started
        progress((elapsed / 240) % 1.0, desc=data.get("progress_message", "Working..."))

        if data["status"] == "complete":
            # Download the PDF locally so Gradio can serve it
            pdf_resp = httpx.get(f"{API_BASE}{data['pdf_url']}", timeout=30)
            local_path = f"/tmp/{job_id}.pdf"
            with open(local_path, "wb") as f:
                f.write(pdf_resp.content)

            md_resp = httpx.get(f"{API_BASE}{data['markdown_url']}", timeout=30)
            md_text = md_resp.text

            summary = (
                f"**{data.get('company_name', 'Unknown')}** — "
                f"Recommendation: **{data.get('recommendation', '?')}**\n\n"
                f"Generated in {data.get('latency_seconds', 0):.0f}s · "
                f"estimated cost ${data.get('cost_usd_estimate', 0):.2f}"
            )
            return local_path, md_text, summary, "✅ Complete"

        if data["status"] == "failed":
            return None, None, f"❌ Failed: {data.get('error_message', 'Unknown error')}", ""

        time.sleep(POLL_INTERVAL_SECONDS)


with gr.Blocks(title="DealScout", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
        # DealScout
        ### Multi-agent AI system for VC-grade investment memos
        Paste a startup URL below. The system researches the company, market, and founders,
        then produces a structured investment memo with a Pass / Track / Meet recommendation.
        Typical runtime: 3–5 minutes.
    """)
    with gr.Row():
        input_box = gr.Textbox(
            label="Startup URL",
            placeholder="https://stripe.com",
            scale=4,
        )
        submit_btn = gr.Button("Generate Memo", variant="primary", scale=1)

    status_box = gr.Markdown("")
    with gr.Row():
        with gr.Column():
            pdf_output = gr.File(label="Investment Memo (PDF)", interactive=False)
            summary_box = gr.Markdown("")
        with gr.Column():
            markdown_output = gr.Textbox(
                label="Memo (Markdown)", lines=24, max_lines=24,
                show_copy_button=True,
            )

    submit_btn.click(
        fn=submit_and_wait,
        inputs=[input_box],
        outputs=[pdf_output, markdown_output, summary_box, status_box],
    )

    gr.Examples(
        examples=["https://stripe.com", "https://modal.com", "https://anthropic.com"],
        inputs=input_box,
    )

    gr.Markdown("""
        ---
        *Built on Python + OpenAI Agents SDK + DeepSeek.
        [Source on GitHub](https://github.com/yourname/dealscout) ·
        DealScout is a research aid, not investment advice.*
    """)


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
```

**Acceptance:**
1. With FastAPI already running on 8000, `uv run python -m dealscout.service.ui` starts Gradio on 7860.
2. Open http://localhost:7860, paste a URL, click submit.
3. Status updates progress text every ~5s.
4. After ~4 minutes, PDF appears as a download, Markdown renders in the textbox, summary line shows company + recommendation + cost + latency.
5. Submitting a bad URL produces a visible error message, not a hang.

### Step 6 — Process orchestration

You need both services running. For local dev, two terminals. For deployment (F11), a `Procfile` or `docker-compose.yml`.

For local dev, create a `Makefile` or `justfile`:

```makefile
# Makefile
.PHONY: api ui dev

api:
	uv run uvicorn dealscout.service.api:app --host 0.0.0.0 --port 8000 --reload

ui:
	uv run python -m dealscout.service.ui

dev:
	# Run both — needs `make -j 2 api ui` to parallelize
	@echo "Run 'make api' and 'make ui' in two terminals."
```

### Step 7 — Smoke test the full stack

Manual checklist on the running services:

1. `curl http://localhost:8000/health` → `{"status": "ok", ...}`
2. `curl -X POST http://localhost:8000/analyze -H "Content-Type: application/json" -d '{"input": "https://modal.com"}'` → returns `job_id`
3. `curl http://localhost:8000/jobs/<id>` → status transitions from `pending` → `running` → `complete` over ~4 min
4. `curl http://localhost:8000/memos/<id>/pdf -o test.pdf && open test.pdf` → opens the memo
5. Open http://localhost:7860 → Gradio loads, paste a URL, full flow works, PDF downloads
6. Submit a deliberately broken URL (`https://nonexistent-domain-test.com`) → fails cleanly with error in UI, not a hang
7. Submit two jobs in quick succession → second waits for first (semaphore working)

### Step 8 — One integration test

```python
# tests/integration/test_service.py
import pytest
import time
from fastapi.testclient import TestClient
from dealscout.service.api import app


@pytest.mark.integration
def test_full_service_flow():
    """End-to-end: POST /analyze → poll → download.
    Costs ~$0.20. Skip if budget is tight."""
    client = TestClient(app)

    # Submit
    r = client.post("/analyze", json={"input": "https://stripe.com"})
    assert r.status_code == 200
    job_id = r.json()["job_id"]
    assert r.json()["status"] == "pending"

    # Poll up to 6 minutes
    deadline = time.time() + 360
    while time.time() < deadline:
        r = client.get(f"/jobs/{job_id}")
        status = r.json()["status"]
        if status == "complete":
            break
        if status == "failed":
            pytest.fail(f"Job failed: {r.json().get('error_message')}")
        time.sleep(5)
    else:
        pytest.fail("Job did not complete in 6 minutes")

    # Download PDF
    r = client.get(f"/memos/{job_id}/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert len(r.content) > 5000   # non-trivial PDF
```

This test runs the real pipeline and costs ~$0.20. Don't run it in CI. Mark with `@pytest.mark.integration` and run on demand only.

---

## Quality gates

- [ ] FastAPI service runs without errors
- [ ] Gradio UI runs and connects to FastAPI
- [ ] `/analyze` returns a job ID in <500ms
- [ ] Job state transitions visibly (`pending` → `running` → `complete`)
- [ ] PDF downloads correctly from the UI
- [ ] Bad input produces a clean error, not a hang
- [ ] Two simultaneous jobs serialize (semaphore working)
- [ ] No memo data persists in process memory after restart (acceptable for v1; document it)
- [ ] At least one screenshot saved of the Gradio UI showing a completed memo

---

## DeepSeek / pipeline gotchas

- **Pipeline currently emits 3 coarse progress messages** ("Reading source", "Researching", "Writing memo"). The researching phase is ~3 minutes of one message. Acceptable for v1. A future improvement: thread progress callbacks through the agents so you can see "researching company done, researching market 30% complete." Not for now.

- **F01 intake fragility is still real.** If your F01.5 fix isn't in place when you demo, prefer URLs that have produced good intakes in your testing (Stripe, Modal). Don't roll the dice with an untested URL during a live demo.

- **Tavily and DeepSeek rate limits apply.** If a recruiter clicks your live demo URL and submits a job while you're already running one, the semaphore queues theirs. They'll see "pending" for a bit. Document this in the UI ("one analysis at a time during demo period").

- **Cost on the live demo.** Set DeepSeek's daily spend cap to $2 before going live. A semaphore prevents accidental burst, but bad actors clicking submit-submit-submit on the public URL could still drain budget over a day.

---

## What we explicitly defer

- ❌ **WebSockets / SSE for real-time progress.** Polling is fine.
- ❌ **Auth / API keys.** Public demo. F11 will add basic IP rate limiting if needed.
- ❌ **Multi-user concurrency.** Semaphore=1. One job at a time globally.
- ❌ **Persistent job history.** Lost on restart. Acceptable.
- ❌ **Frontend prettier than Gradio.** No Next.js, no custom CSS beyond Gradio's theme.
- ❌ **Streaming the memo into the UI as it's written.** F06's Memo Writer doesn't stream.

---

## Definition of done

- [ ] `service/jobs.py`, `service/worker.py`, `service/api.py`, `service/ui.py` exist
- [ ] `make api` and `make ui` (or equivalent) start both services
- [ ] Full Gradio flow works end-to-end on Stripe
- [ ] PDF and Markdown both downloadable
- [ ] Error states surface in the UI without crashing
- [ ] One integration test passes (`tests/integration/test_service.py`)
- [ ] Screenshot of UI saved to `docs/screenshots/gradio_demo.png` for the LinkedIn post
- [ ] Committed on branch `feature/10-service`

---

## Session plan

Roughly 3–4 hours.

1. **15 min** — Step 1. Dependencies. Verify clean install.
2. **30 min** — Steps 2–3. Job state + worker. Test by calling `execute_job` directly from a Python REPL on a fixture URL — don't bring HTTP in yet.
3. **45 min** — Step 4. FastAPI service. Test with `curl` only. Confirm the async background task fires.
4. **60 min** — Step 5. Gradio UI. Most time goes into testing the polling loop and making sure the PDF download works through Gradio's File component.
5. **15 min** — Step 6. Makefile or equivalent.
6. **30 min** — Step 7. Smoke test the full stack. Pay attention to the error cases — those are what break in production.
7. **30 min** — Step 8. Integration test + screenshot for LinkedIn.
8. **15 min** — Commit.

If Gradio's polling loop fights you, stop and ping me. There's a specific pattern around `gr.Progress` and long-running operations that's easy to get wrong.

---

## What to add to `my_work/learnings.md`

1. *What's the difference between an async background task and a worker queue (Celery)? When does v1 stop being enough?*
2. *Why does the pipeline run inside a Semaphore? What would break without it?*
3. *Why does the user poll instead of getting a WebSocket update? What's the tradeoff?*
4. *Look at your screenshots. What would you have to change about the UI before showing it to a non-technical investor?* (You don't have to fix it. Just observe.)

---

## After F10

You have a deployable service. Next is F11 (deploy to Render or Fly), then F07 (evals), then the LinkedIn post.

If you only had time for **one screenshot for LinkedIn**, take it now: open the Gradio UI on Stripe's memo, mid-recommendation visible. That screenshot is what makes the post tangible. PDFs are attachments people may not download; a UI screenshot is what they see while scrolling.
