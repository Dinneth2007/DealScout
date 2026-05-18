# DealScout

A multi-agent system that turns a startup URL or pitch deck into a VC-style
investment memo — researched, cited, and ending in a Pass / Track / Meet call.

**Live demo:** https://dealscout-ui.onrender.com
**API:** https://dealscout-api.onrender.com/docs

![DealScout UI](docs/screenshots/gradio_demo.png)

## What this is

Most "AI agent" demos are one prompt behind a chat box. DealScout is a small
multi-agent pipeline that does real work: it routes the input, runs three
specialist researchers against live web search, synthesizes their findings
into one opinionated dossier, and only then writes a structured memo.

A run takes a few minutes and produces a 6-page PDF plus Markdown.

## How it works

```
URL / PDF
   │
   ▼
Triage ──handoff──► URL / PDF Intake ──► StartupBrief
                                            │
                                            ▼
                                      Orchestrator
                         (Company · Market · Founder researchers
                          wrapped as tools, web search via Tavily)
                                            │
                                            ▼
                                  synthesized dossier
                                            │
                                            ▼
                                  Memo Writer (typed)
                                            │
                                            ▼
                                   memo.pdf + memo.md
```

Design choices worth calling out:

- **Handoff at the front, agents-as-tools in the middle.** Triage *hands off*
  to intake (it's done once it routes); the Orchestrator *calls* researchers
  as tools so it stays in control to synthesize across all three.
- **Free-form in the middle, typed at the edges.** Intake and the final memo
  are validated Pydantic schemas; research and synthesis are free Markdown,
  because forcing a schema on judgment work degrades it.
- **One LLM adapter.** Every model call goes through a single seam, so the
  provider is a config switch (DeepSeek or Gemini) with no code changes.
- **Cost guards in depth.** Per-IP rate limit in the app, plus provider spend
  caps — independent layers, so one failing doesn't drain the account.

## Stack

Python 3.11 · OpenAI Agents SDK · DeepSeek (OpenAI-compatible API) ·
Pydantic 2 · Tavily search · FastAPI + Gradio · ReportLab ·
deployed on Render as two services.

## Run it locally

```bash
uv sync
cp .env.example .env          # set DEEPSEEK_API_KEY and TAVILY_API_KEY
make api                      # FastAPI on :8000
make ui                       # Gradio on :7860 (separate terminal)
```

Tests:

```bash
uv run pytest tests/unit                        # fast, no network
uv run pytest tests/integration -m integration  # real LLM, costs money
```

## Deployment

Two Render web services from one `render.yaml` blueprint: `dealscout-api`
(FastAPI) and `dealscout-ui` (Gradio), wired together at deploy time.
Pushing to `main` redeploys. Free tier, so the first request after idle
takes ~30s to wake.

## What I deliberately left out

- **Automated eval harness.** Eval cases are defined (`tests/eval/cases/`);
  scoring them into a scorecard is the next piece of real work, not a
  shortcut I'm hiding.
- **A database.** Memos are written to disk and lost on restart — fine for a
  demo, wrong for production, and a deliberate scope line.
- **Real-time progress (WebSockets), auth, multi-user concurrency.** Polling
  and a global one-job-at-a-time lock are correct for this scale.
- **A hand-built frontend.** Gradio is the evidence the system works, not the
  product; a React app would add a week and prove nothing extra.

## Disclaimer

DealScout is a research aid, not investment advice.
