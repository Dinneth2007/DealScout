"""Gradio front-end. Submits to the FastAPI service and polls for the memo.

Gradio 6.x note: gr.Textbox dropped `show_copy_button` (was in v4) — removed
here so construction doesn't throw. Other v4 APIs used (gr.Progress, gr.File,
gr.Blocks, gr.Examples) are still present in v6.
"""
from __future__ import annotations

import logging
import os
import tempfile
import time
from pathlib import Path

import gradio as gr
import httpx

from dealscout.service.rate_limit import check_rate_limit

log = logging.getLogger(__name__)

# Render injects DEALSCOUT_API_BASE via fromService as a bare host
# ("dealscout-api.onrender.com"); locally it's a full URL. Normalize both.
_raw = os.getenv("DEALSCOUT_API_BASE", "http://localhost:8000")
API_BASE = _raw if _raw.startswith("http") else f"https://{_raw}"
POLL_INTERVAL_SECONDS = 5

# A cold Render free service can take 90-150s to boot with our stack
# (FastAPI + agents SDK + tracing init). The edge proxy answers with these
# statuses, or the socket refuses, until uvicorn binds the port. A
# scheduled GH Actions ping keeps the service hot in normal use; this
# budget is the backstop for the case where the ping has been delayed or
# the dyno was restarted by Render.
COLD_START_STATUSES = {502, 503, 504}
WAKE_BUDGET_SECONDS = 180
WAKE_RETRY_SECONDS = 5


def _prewarm_api() -> None:
    """Ping the API once at UI startup to wake it from Render sleep."""
    try:
        httpx.get(f"{API_BASE}/health", timeout=5.0)
        log.info("API pre-warm ping successful")
    except Exception as e:  # noqa: BLE001 — best-effort, never blocks startup
        log.warning("API pre-warm failed (OK on first deploy): %s", e)


def _client_ip(request: gr.Request | None) -> str:
    """Best-effort client IP. Render sets X-Forwarded-For."""
    if request is None:
        return ""
    headers = dict(request.headers) if hasattr(request, "headers") else {}
    ip = (headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if not ip and getattr(request, "client", None):
        ip = request.client.host
    return ip


def _submit_with_wake(input_str: str, progress) -> str:
    """POST /analyze, riding out a cold-API boot. Returns the job id.

    A request that lands while the free-tier API is asleep gets a fast
    502/503 from Render's proxy (or a refused connection) — not a slow
    success — so a single attempt can't wait the boot out. Retry only
    those, within a bounded window. A 4xx (bad input) or an app 500 is a
    real failure: let it raise so we don't mask it behind "waking…".
    """
    deadline = time.time() + WAKE_BUDGET_SECONDS
    attempt = 0
    while True:
        attempt += 1
        try:
            r = httpx.post(
                f"{API_BASE}/analyze", json={"input": input_str}, timeout=30
            )
            if r.status_code not in COLD_START_STATUSES:
                r.raise_for_status()  # real 4xx/5xx propagates out untouched
                return r.json()["job_id"]
            last_error: Exception = httpx.HTTPStatusError(
                f"{r.status_code} from edge proxy (API still booting)",
                request=r.request,
                response=r,
            )
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
            last_error = e  # socket not accepting yet — still booting

        if time.time() >= deadline:
            raise last_error
        progress(0, desc=f"Waking server, retrying… (attempt {attempt})")
        time.sleep(WAKE_RETRY_SECONDS)


def submit_and_wait(
    input_str: str, request: gr.Request, progress=gr.Progress()
):
    """Submit an analysis, poll until done, return (pdf, md, summary, status)."""
    if not input_str or not input_str.strip():
        return None, None, "Please enter a URL or PDF path.", ""

    rate_error = check_rate_limit(_client_ip(request))
    if rate_error:
        return None, None, f"⏱️ {rate_error}", ""

    progress(0, desc="Submitting...")
    try:
        job_id = _submit_with_wake(input_str, progress)
    except httpx.HTTPError as e:
        return None, None, f"Failed to submit job: {e}", ""

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
            pdf_resp = httpx.get(f"{API_BASE}{data['pdf_url']}", timeout=30)
            # Gradio 6 only serves files from cwd / the SYSTEM temp dir /
            # allowed_paths. Hardcoded /tmp fails on macOS (sys temp is
            # /var/folders/...). tempfile.gettempdir() is the portable path.
            local_path = str(Path(tempfile.gettempdir()) / f"{job_id}.pdf")
            with open(local_path, "wb") as f:
                f.write(pdf_resp.content)
            md_text = httpx.get(
                f"{API_BASE}{data['markdown_url']}", timeout=30
            ).text
            summary = (
                f"**{data.get('company_name', 'Unknown')}** — "
                f"Recommendation: **{data.get('recommendation', '?')}**\n\n"
                f"Generated in {data.get('latency_seconds', 0):.0f}s · "
                f"estimated cost ${data.get('cost_usd_estimate') or 0:.2f}"
            )
            return local_path, md_text, summary, "✅ Complete"

        if data["status"] == "failed":
            return None, None, (
                f"❌ Failed: {data.get('error_message', 'Unknown error')}"
            ), ""

        time.sleep(POLL_INTERVAL_SECONDS)


_prewarm_api()  # nudge the API awake before the UI is even rendered

with gr.Blocks(title="DealScout") as demo:  # theme -> launch() in Gradio 6
    gr.Markdown(
        """
        # DealScout
        ### Multi-agent AI system for VC-grade investment memos
        Paste a startup URL below. The system researches the company, market,
        and founders, then produces a structured investment memo with a
        Pass / Track / Meet recommendation. Typical runtime: 3–5 minutes.
        One analysis at a time during the demo period.
        """
    )
    with gr.Row():
        input_box = gr.Textbox(
            label="Startup URL", placeholder="https://stripe.com", scale=4
        )
        submit_btn = gr.Button("Generate Memo", variant="primary", scale=1)

    status_box = gr.Markdown("")
    with gr.Row():
        with gr.Column():
            pdf_output = gr.File(label="Investment Memo (PDF)", interactive=False)
            summary_box = gr.Markdown("")
        with gr.Column():
            markdown_output = gr.Textbox(
                label="Memo (Markdown)", lines=24, max_lines=24
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

    gr.Markdown(
        """
        ---
        *Built on Python + OpenAI Agents SDK + DeepSeek.
        DealScout is a research aid, not investment advice.*
        """
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "7860"))  # Render injects $PORT
    demo.launch(
        server_name="0.0.0.0", server_port=port, theme=gr.themes.Soft()
    )
