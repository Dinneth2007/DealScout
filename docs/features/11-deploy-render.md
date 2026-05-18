# F11 — Deployment to Render

**Phase:** 7 — Productionization
**Depends on:** F10 (FastAPI service + Gradio UI working locally)
**Blocks:** Public LinkedIn post
**Estimated time:** 1 focused session (2–3 hours)
**LLM cost during deployment:** $0
**LLM cost after deployment (verification + demo runs):** ~$0.60–$1.00

---

## Why this feature exists

You have a working two-service app on your laptop. F11 puts it on a server that anyone can reach. The point isn't "deploying" as a technical exercise — the point is *having a public URL you can attach to a LinkedIn post and a CV.*

Three things F11 must accomplish:

1. The deployed URL stays alive 24/7 (with free-tier cold-start caveat).
2. The deployed app doesn't drain your DeepSeek budget if someone abuses it.
3. The deployment is *defensible in an interview* — you can explain what you chose and why.

If F11 fails on any of those three, you've shipped a liability, not a portfolio piece.

---

## Why Render, not HF Spaces / Fly / AWS

This is the first thing an interviewer might ask, so internalize the answer.

**Chose:** Render free tier, two-service blueprint deploy.

**Rejected — Hugging Face Spaces:** would have required collapsing the FastAPI + Gradio split into one process. That collapse hides one of the project's better architectural decisions (the F10 service/UI separation). Render lets the two services stay separate.

**Rejected — Fly.io:** Docker-based, no free tier as of late 2024 (now pay-as-you-go with a credit card requirement). First-time Docker deploys eat 6+ hours debugging build issues. Wrong cost/benefit for a first deployment.

**Rejected — AWS:** the "AWS" signal is the wrong signal for an AI engineering portfolio. There's no single "deploy to AWS" path — it's a choice of App Runner vs Elastic Beanstalk vs ECS vs Lambda + API Gateway, each a different deployment shape and learning curve. Bill spikes from misconfigured services are a real risk. AWS makes sense if you're targeting AWS-shop roles specifically; otherwise it adds noise to your AI engineering story.

**Trade-offs accepted with Render free tier:**
- Cold starts after 15 minutes of inactivity (~30s wake-up on first request).
- 512MB RAM per service — tight, but DealScout fits.
- $7/mo "Starter" plan removes sleep + bumps RAM if needed later.

Write this down somewhere — these are the answers to "why did you deploy on Render?"

---

## Mental model

### Two services, one repo, one deployment

```
┌────────────────────────────────────────────────────────────┐
│              GitHub repo (one)                             │
│              └─ render.yaml (Blueprint defines BOTH)       │
└───────────────────────┬────────────────────────────────────┘
                        │ push triggers build
                        ▼
        ┌───────────────────────────────────┐
        │             Render                │
        │                                   │
        │   ┌────────────────────────────┐  │
        │   │ dealscout-api              │  │   FastAPI
        │   │ uvicorn ... --port $PORT   │  │
        │   │ https://dealscout-api      │  │
        │   │ .onrender.com              │  │
        │   └─────────────┬──────────────┘  │
        │                 │ internal HTTP   │
        │                 │                 │
        │   ┌─────────────▼──────────────┐  │
        │   │ dealscout-ui               │  │   Gradio
        │   │ python -m dealscout...     │  │
        │   │ https://dealscout-ui       │  │   ← Public URL
        │   │ .onrender.com              │  │     (what people click)
        │   └────────────────────────────┘  │
        └───────────────────────────────────┘
```

The UI service is the public face. The API service is technically also public on its own URL (curl-able for the design-savvy who want to see the API surface), but most users only ever see the Gradio URL.

### What Render is actually doing for you

For each service in `render.yaml`, on every git push:
1. Clones your repo to a fresh build container
2. Runs the `buildCommand` (installs Python deps)
3. Runs the `startCommand` (boots your service)
4. Routes a `*.onrender.com` URL to it with HTTPS
5. Restarts it if it crashes; sleeps it after 15min idle

You don't configure servers. You don't write nginx configs. You don't manage SSL. You describe what you want in `render.yaml`; Render provides the rest.

This is good for your purposes (fast deployment) but it's also why a deployment story alone isn't a CV moat — what *is* a moat is the architecture, the evals, the observability, the cost discipline. Render is the wrapper, not the product.

### Why a Blueprint, not the UI wizard

Render lets you create services manually through their dashboard. Don't. Use `render.yaml` (their "Blueprint" format) committed to your repo. Three reasons:

1. **Reproducibility.** Anyone — including future-you — can re-create the deploy from the repo alone. No tribal knowledge in a web dashboard.
2. **Reviewability.** `render.yaml` is in your repo. A reviewer can read it. UI clicks are invisible.
3. **It's the senior-engineer move.** Configuration-as-code beats configuration-in-clicks every time. This is the same principle as your Pydantic Settings (env-var-driven) vs hardcoded values.

---

## Key design decisions

### Decision 1 — Two services on Render, not one collapsed process

**What:** Render runs two separate services: `dealscout-api` (FastAPI) and `dealscout-ui` (Gradio). The Gradio service makes HTTP calls to the API service.

**Why:** Preserves the architectural separation from F10. Lets you point recruiters at *two* URLs — the UI for demos, the API for technical curiosity ("look, here's the OpenAPI docs at `/docs`"). The API service is independently testable via curl.

**How it would burn you:** Collapsing them into one process for deployment convenience hides one of the more interesting design decisions in DealScout. You'd have to explain "actually I built it as two services but merged them for deploy" — which sounds defensive. Better to deploy what you actually built.

**Transferable principle:** *Deploy the architecture you designed, not a simplified version of it.* If your architecture doesn't survive contact with production constraints, that tells you something useful about the architecture — don't paper over it.

### Decision 2 — Free tier accepted, cold start documented

**What:** Free tier on both services. Sleep behavior is acknowledged in the UI ("First load may take ~30s if the service has been idle").

**Why:** $0/month for an indefinite portfolio demo. The 30s cold start affects the *first* request after 15min idle; subsequent requests are instant. For a demo URL where the typical visitor pattern is "click once, run a memo, leave," the cold start hits once and is masked by the 4-minute memo generation anyway.

**How it would burn you:** Paying $7/mo for "Starter" before you know whether anyone clicks the link is premature optimization. Easy to upgrade later if traffic justifies it.

**Transferable principle:** *Accept the constraints of the free tier explicitly, in the UX, rather than upgrading defensively.* Either the constraint is acceptable (document it) or it's not (upgrade). Don't ignore it.

### Decision 3 — Pre-warm the API from the UI's startup

**What:** When Gradio's UI boots, it pings the API's `/health` endpoint. This wakes the API service if it's sleeping, so by the time a user clicks submit, the API is warm.

**Why:** Reduces the worst-case latency. A user who hits a fully-cold deploy waits ~30s for UI + ~30s for API = ~60s before anything happens. The pre-warm cuts that roughly in half.

**How it would burn you:** No pre-warm means the user clicks "submit" on a warm Gradio, sees the progress bar start, then waits silently for 30s while the API wakes up. Looks broken to anyone not familiar with cold starts.

**Transferable principle:** *Hide infrastructure quirks from the user with small, deliberate touches.* The cold start is real; the user shouldn't have to know it exists.

### Decision 4 — Secrets in Render's dashboard, never in render.yaml

**What:** `render.yaml` declares which env vars exist; for secrets it sets `sync: false`. The actual secret values are set via Render's dashboard after deploy.

**Why:** `render.yaml` is committed to your public repo. Anything in it is public. Secrets go in Render's secret store (encrypted at rest, never visible after entry).

**How it would burn you:** Putting `DEEPSEEK_API_KEY: "sk-..."` in `render.yaml` commits your key to GitHub. Even after you remove and rotate it, the git history retains it. Anyone who scrapes public GitHub gets your key.

**Transferable principle:** *Configuration is in code; secrets are out of code.* This is the same principle as `.env` not being committed. Render's `sync: false` is the deployment-time version of `.gitignore` for env vars.

### Decision 5 — Per-IP rate limit + provider spend caps (defense in depth)

**What:** Three independent layers of cost protection:
1. Per-IP rate limit in your code (3 runs / 24h / IP).
2. DeepSeek daily spend cap in their billing dashboard ($2/day).
3. Tavily monthly query budget ($500 free tier limit).

**Why:** Any one of these can fail. Rate limit code might have a bug. Spend caps might not apply mid-request. Defense in depth means a single failure doesn't drain your account.

**How it would burn you:** Trust the rate limit alone, and a logic bug means $30 of DeepSeek calls before you notice. Trust the spend cap alone, and you discover it doesn't apply until *after* the offending request completes. All three together, in independent systems, give you actual safety.

**Transferable principle:** *Cost guards belong on multiple layers, run by multiple systems, that fail independently.* This is the production principle behind every meaningful "I won't get a surprise bill" story.

### Decision 6 — render.yaml committed, deployed via Blueprint sync

**What:** The `render.yaml` is in your repo's root. When you connect the repo to Render, Render reads it and provisions both services from one config.

**Why:** See "Why a Blueprint" above. Configuration-as-code is the right pattern. It also means *re-deploying after a code change is just `git push`* — Render watches the repo, sees the commit, rebuilds.

**How it would burn you:** Without a Blueprint, you create services manually through Render's UI. The config lives in their dashboard, undocumented. If you ever need to recreate the deployment (e.g., for a colleague, or after Render rate-limits your account, or just six months from now when you've forgotten what you set), you're starting from scratch.

**Transferable principle:** *If your infrastructure can be expressed as text, express it as text and commit it.* Same principle as terraform, k8s manifests, GitHub Actions YAML.

---

## Build order

### Step 0 — Verify F10 is shippable

Before touching Render, confirm locally:

```bash
# In one terminal
make api
# In another terminal
make ui
```

Open `http://localhost:7860`. Submit Stripe. Watch the full flow. Get the PDF.

**If anything is flaky locally, fix it before deploying.** Deployment doesn't fix broken code; it makes broken code harder to debug because now there are network and platform variables on top.

### Step 1 — Rotate API keys (10 min, $0)

Do this first. Once your repo is public and your deployment is live, your old keys are exposed if they were ever accidentally committed.

1. Go to DeepSeek dashboard → API keys → revoke current key → generate new one.
2. Go to Tavily dashboard → API keys → revoke current key → generate new one.
3. Update your local `.env` with the new values.
4. Verify locally: `make api` should still work with the new keys.

If you've never committed `.env`, this step is still worth doing — it makes the keys you'll paste into Render's dashboard freshly minted and clean.

### Step 2 — Set provider spend caps (10 min, $0)

**DeepSeek:**
1. Sign in to DeepSeek's billing dashboard.
2. Find "Spending limit" or "Budget" section.
3. Set daily cap to **$2/day**.
4. Set email alert at 50% of daily ($1).

**Tavily:**
1. Sign in to Tavily dashboard.
2. Find usage limits.
3. Set monthly query cap to **500** (free tier is 1000; 500 keeps you safely under).
4. Set email alert at 50%.

Both alerts go to the email on the account. Make sure you'll actually see them — not buried in a "service notifications" folder.

### Step 3 — Add the per-IP rate limit (30 min, $0)

Create the module:

```python
# src/dealscout/service/rate_limit.py
from __future__ import annotations
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Optional

# (count, window_start) per IP
_BUCKETS: OrderedDict[str, tuple[int, datetime]] = OrderedDict()
_LOCK = Lock()
_LIMIT_PER_IP = 3
_WINDOW = timedelta(hours=24)
_MAX_TRACKED_IPS = 10_000  # cap memory; LRU eviction

def check_rate_limit(ip: str) -> Optional[str]:
    """Return None if request allowed; an error message if rate-limited.

    Per-IP limit of 3 requests per 24h. In-memory only — resets on process
    restart. For a single-instance demo deployment that's acceptable;
    production would use Redis.
    """
    if not ip:
        return None  # don't block requests with no identifiable IP

    now = datetime.now(timezone.utc)
    with _LOCK:
        # LRU eviction
        if len(_BUCKETS) > _MAX_TRACKED_IPS:
            _BUCKETS.popitem(last=False)

        count, window_start = _BUCKETS.get(ip, (0, now))
        if now - window_start > _WINDOW:
            count, window_start = 0, now

        if count >= _LIMIT_PER_IP:
            wait_seconds = _WINDOW - (now - window_start)
            hours = int(wait_seconds.total_seconds() / 3600)
            return (f"Demo rate limit hit ({_LIMIT_PER_IP} runs per 24h per IP). "
                    f"Try again in ~{hours}h.")

        _BUCKETS[ip] = (count + 1, window_start)
        _BUCKETS.move_to_end(ip)
        return None

def reset_rate_limit() -> None:
    """Test-only — clears all buckets."""
    with _LOCK:
        _BUCKETS.clear()
```

Wire it into the Gradio handler in `src/dealscout/service/ui.py`. The Gradio submit function needs an extra parameter `request: gr.Request` so Gradio injects the client request info:

```python
# Modify the submit_and_wait function in ui.py
import gradio as gr
from dealscout.service.rate_limit import check_rate_limit

def submit_and_wait(input_str: str, request: gr.Request, progress=gr.Progress()):
    # Identify caller. Render puts the real client IP in X-Forwarded-For;
    # Gradio's request object exposes headers.
    headers = dict(request.headers) if request and hasattr(request, 'headers') else {}
    ip = (headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if not ip and request and request.client:
        ip = request.client.host

    rate_error = check_rate_limit(ip)
    if rate_error:
        return None, None, f"⏱️ {rate_error}", ""

    # ... rest of existing submit_and_wait ...
```

**Test locally:** lower `_LIMIT_PER_IP` to 1 temporarily, submit twice from your browser. The second submit should show the rate-limit error. Then restore to 3.

### Step 4 — Make ports env-driven (15 min, $0)

Render assigns the port via the `$PORT` env var. Hardcoded ports break.

**FastAPI service** — your `Makefile` or start command needs:
```bash
uvicorn dealscout.service.api:app --host 0.0.0.0 --port $PORT
```

**Gradio service** — in `src/dealscout/service/ui.py`, the launch line:
```python
import os
if __name__ == "__main__":
    port = int(os.getenv("PORT", "7860"))
    demo.launch(server_name="0.0.0.0", server_port=port)
```

**Gradio's API base must be env-driven** — Gradio needs to know where FastAPI is. In `ui.py`:
```python
import os
API_BASE = os.getenv("DEALSCOUT_API_BASE", "http://localhost:8000")
```

This is the variable Render will set at runtime to point Gradio at the API service.

Verify locally: `PORT=8001 make api` should start FastAPI on 8001. `PORT=7861 DEALSCOUT_API_BASE=http://localhost:8001 make ui` should start Gradio on 7861, hitting API on 8001.

### Step 5 — Add the pre-warm health ping (15 min, $0)

The Gradio service pings the API's `/health` endpoint when it boots. Add to `ui.py` near the top, after imports:

```python
import httpx
import logging

log = logging.getLogger(__name__)

def _prewarm_api() -> None:
    """Ping the API once at UI startup to wake it from sleep."""
    try:
        httpx.get(f"{API_BASE}/health", timeout=5.0)
        log.info("API pre-warm ping successful")
    except Exception as e:
        log.warning("API pre-warm failed (this is OK on first deploy): %s", e)

# Call before defining the Gradio interface
_prewarm_api()
```

This is fire-and-forget. If the API isn't up yet (first deploy, both services starting), it logs a warning and continues. The user's first actual request will still cold-start the API; the pre-warm is just an extra nudge.

### Step 6 — Generate `requirements.txt` (10 min, $0)

Render reads dependencies from `requirements.txt`. Generate it from your `pyproject.toml`:

```bash
uv pip compile pyproject.toml -o requirements.txt
```

Verify:
- It exists at repo root.
- It contains `fastapi`, `uvicorn`, `gradio`, `pydantic`, `pydantic-settings`, `openai-agents`, `openai`, `pypdf`, `beautifulsoup4`, `httpx`, `tenacity`, `python-dotenv`, `reportlab`. Plus their transitive deps.
- It does NOT contain dev-only packages (`pytest`, `ruff`, `respx`) — those are in your `[dev]` group.

Commit it.

### Step 7 — Write `render.yaml` (15 min, $0)

At repo root:

```yaml
services:
  - type: web
    name: dealscout-api
    runtime: python
    plan: free
    region: oregon  # or whichever is closest to your target audience
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn dealscout.service.api:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    envVars:
      - key: PYTHON_VERSION
        value: "3.11.9"
      - key: DEEPSEEK_API_KEY
        sync: false     # set manually in Render dashboard
      - key: TAVILY_API_KEY
        sync: false
      - key: LANGFUSE_PUBLIC_KEY
        sync: false     # optional; leave blank to disable tracing
      - key: LANGFUSE_SECRET_KEY
        sync: false
      - key: DEEPSEEK_BASE_URL
        value: https://api.deepseek.com/v1
      - key: DEFAULT_MODEL
        value: deepseek-chat
      - key: ORCHESTRATOR_MODEL
        value: deepseek-chat
      - key: RESEARCHER_MODEL
        value: deepseek-chat
      - key: INTAKE_MODEL
        value: deepseek-chat

  - type: web
    name: dealscout-ui
    runtime: python
    plan: free
    region: oregon
    buildCommand: pip install -r requirements.txt
    startCommand: python -m dealscout.service.ui
    envVars:
      - key: PYTHON_VERSION
        value: "3.11.9"
      - key: DEALSCOUT_API_BASE
        fromService:
          type: web
          name: dealscout-api
          property: hostport   # gives 'dealscout-api.onrender.com:443'
```

Notes on what each block does:
- `type: web` — public web service (not a worker or static site).
- `runtime: python` — Render auto-detects Python from `requirements.txt`; this is explicit.
- `plan: free` — sleep after 15min idle, 512MB RAM. Upgrade later if needed.
- `healthCheckPath: /health` — Render hits this to verify the service is up.
- `sync: false` — declares the env var exists but doesn't put the value in the YAML.
- `fromService` — magic that lets dealscout-ui read dealscout-api's URL automatically.

**Important:** the `DEALSCOUT_API_BASE` value from `fromService.property: hostport` gives you `dealscout-api.onrender.com:443`. Your code expects a URL like `https://dealscout-api.onrender.com`. You may need to either:
- Hand-wrap with `https://` in `ui.py`: `API_BASE = f"https://{os.getenv('DEALSCOUT_API_BASE', 'localhost:8000')}"` — careful, this breaks the localhost case.
- Or use `property: host` and prepend `https://` manually.

Cleanest is to use `property: host` (just the hostname) and have a small helper in `ui.py`:

```python
_raw = os.getenv("DEALSCOUT_API_BASE", "http://localhost:8000")
if _raw.startswith("http"):
    API_BASE = _raw
else:
    API_BASE = f"https://{_raw}"
```

Test this locally with both `DEALSCOUT_API_BASE=http://localhost:8000` and `DEALSCOUT_API_BASE=dealscout-api.onrender.com` before pushing.

### Step 8 — Update `.gitignore` (5 min, $0)

Confirm these are excluded:

```
.env
.env.*
!.env.example
*.db
__pycache__/
.venv/
*.pyc
output/
/tmp/
.pytest_cache/
.ruff_cache/
my_work/*
!my_work/README.md
tests/fixtures/*.pdf
```

Run `git status` and confirm nothing sensitive is staged. If `.env` shows up — you've previously committed it. Stop, remove it from history with `git rm --cached .env`, rotate keys again, and only then push.

### Step 9 — Polish the README (30 min, $0)

This is the single most important commit you'll make. Recruiters open the README before the code. Make it land.

Structure to follow:

```markdown
# DealScout

> A multi-agent AI system that produces VC-grade investment memos from a startup URL or pitch deck.

**Live demo:** https://dealscout-ui.onrender.com (will fill in after deploy)
**Sample output:** [Modal Labs memo (PDF)](docs/DealScout_Sample_Memo_Modal.pdf)

![Screenshot](docs/screenshots/gradio_demo.png)

## What's interesting about this project

Most "AI agent" demos are single-prompt chatbots dressed up. DealScout is a
deliberately-engineered multi-agent system with [briefly state your 3 best
design decisions — e.g., handoffs at intake, agents-as-tools for research,
structured outputs at the boundaries, observability via Langfuse, cost
guards in production].

## Architecture

[Embed the architecture diagram. Reference docs/features/* if reviewers
want depth.]

## Stack

- Python 3.11+, OpenAI Agents SDK
- DeepSeek (via OpenAI-compatible endpoint) for LLM
- Pydantic 2 for schema, Tavily for search
- FastAPI + Gradio for the service
- Langfuse for observability
- Deployed on Render free tier (two services via Blueprint)

## Running locally

```bash
git clone <repo>
cd dealscout
uv sync
cp .env.example .env  # fill in API keys
make api   # terminal 1
make ui    # terminal 2
# Open http://localhost:7860
```

## Architecture decisions

[Link to or summarize the key decisions from your CLAUDE.md and feature docs.]

## What I deliberately didn't build (and why)

[Memory across sessions, multi-agent debate, vector DB, fine-tuning.
Briefly explain the why-not for each. This section signals senior judgment.]

## License & disclaimer

DealScout is a research aid, not investment advice.
```

The "What I deliberately didn't build" section is gold for signaling senior judgment. Reviewers respect engineers who can articulate scope decisions.

### Step 10 — Push to GitHub (10 min, $0)

```bash
git add -A
git status   # CONFIRM no .env, no API keys, no /tmp paths
git diff --cached  # quick scan for accidents
git commit -m "F11: production hardening + render.yaml for deployment"
git push
```

Visit your GitHub repo in a browser. Verify:
- `render.yaml` is visible at root.
- `.env` is NOT in the repo (look at the file tree).
- `requirements.txt` is at root.
- README renders correctly.

### Step 11 — Deploy to Render (30 min, $0)

1. **Sign up at render.com.** GitHub-linked sign-in is easiest. No credit card needed for free tier.

2. **Click "New +" → "Blueprint."**

3. **Connect your GitHub repo.** Grant Render access to the dealscout repo (or all repos).

4. **Render reads `render.yaml` automatically** and shows you both services it will create. Confirm.

5. **Render prompts for secrets** (the `sync: false` ones). Paste:
   - `DEEPSEEK_API_KEY` = your rotated key
   - `TAVILY_API_KEY` = your rotated key
   - `LANGFUSE_PUBLIC_KEY` = blank or your local Langfuse key (Langfuse is no-op'd in your code if blank)
   - `LANGFUSE_SECRET_KEY` = same

6. **Click "Apply."** Render starts building both services. Watch the logs.

7. **Build logs will show** `pip install -r requirements.txt` running, then your start command, then either "service is live" or an error. Common first-deploy errors:
   - *ModuleNotFoundError:* a dep is missing from `requirements.txt`. Add it locally with `uv add`, regenerate `requirements.txt`, push.
   - *Service crashes immediately:* check env vars are all set. Most common: `DEEPSEEK_API_KEY` typo.
   - *Health check failing:* the API service must respond 200 at `/health` within Render's deadline. Confirm the `/health` endpoint exists in your FastAPI code (F10 spec has it).

8. **Once both services show "Live,"** open the dealscout-ui URL (Render shows it on the service's page). Gradio should load.

9. **Submit Stripe.** Watch progress. Get the PDF.

### Step 12 — Cost-guard verification (15 min, ~$0.40)

Spend the $0.40 to verify guards work. *Don't skip this.*

1. **Rate limit test.** Submit Stripe four times from your browser. First three should run normally; fourth should show the rate-limit error message. If all four run, the rate limit is broken — debug before going further.

2. **Spend cap visibility.** Visit your DeepSeek dashboard. Confirm the day's spend is showing (~$0.40 after three runs). Confirm the daily cap is still set.

3. **Sleep behavior.** Wait 20 minutes without using the demo. Then submit a URL — note the cold-start delay. This is what a recruiter will experience on first click. Document it in the UI if it's painful.

### Step 13 — Take the LinkedIn screenshot (10 min, $0)

Most important visual artifact of the project.

1. Open the live deployed Gradio URL.
2. Submit Stripe (yes, it costs $0.10; worth it).
3. Wait for completion.
4. Screenshot the *completed state* — Gradio UI showing the recommendation, the company name, the PDF download visible.
5. Save to `docs/screenshots/gradio_demo_deployed.png`.
6. Commit and push.

This screenshot is what recruiters see in your LinkedIn post. It should show:
- The Gradio UI (signals: real app, not a terminal)
- A real company name and recommendation (signals: it actually works)
- The deployed URL in the browser address bar (signals: live, not localhost)

### Step 14 — Update README with the live URL (5 min, $0)

Replace the placeholder live URL in your README with the actual Render URL. Commit. Push.

The README is now the canonical entry point. Live URL at the top, screenshot below, architecture below that.

---

## Quality gates

- [ ] Both services show "Live" on Render's dashboard
- [ ] Public Gradio URL loads (HTTPS, no certificate warnings)
- [ ] Submitting Stripe completes successfully end-to-end on the deployed URL
- [ ] PDF downloads correctly through the deployed URL
- [ ] Rate limit triggers after 3 requests from same browser (in 24h window)
- [ ] DeepSeek dashboard shows day's spending is tracked
- [ ] DeepSeek daily cap is set to $2
- [ ] Tavily monthly cap is set
- [ ] README on GitHub shows the live URL prominently
- [ ] No `.env` or API keys visible anywhere in the public repo
- [ ] Screenshot of deployed UI saved to `docs/screenshots/gradio_demo_deployed.png`
- [ ] Committed on branch `feature/11-deploy` and merged to main

---

## Common first-deploy gotchas

These are the things that will cost you an hour if you don't know about them:

**1. The pip install timeout.** Render's free tier has a 15-minute build timeout. ReportLab and some scientific deps can be slow to install. If you blow the timeout, switch from source builds to wheels by adding `--prefer-binary` to your buildCommand: `pip install --prefer-binary -r requirements.txt`.

**2. Cold start during health check.** Render hits `/health` to verify the service is up. If your FastAPI startup is slow (because `configure_provider()` makes an LLM call?), the health check times out. Make startup synchronous and fast — no LLM calls during app initialization, only during request handling.

**3. The `fromService` env var.** Whether `property: host` gives `dealscout-api.onrender.com` or `https://dealscout-api.onrender.com` depends on Render's current behavior — verify in the dashboard after first deploy. Your `ui.py` needs to handle both shapes safely (the helper code I gave you does).

**4. Render's outbound bandwidth.** Free tier has limits. Each memo generates a few API calls to DeepSeek + Tavily; well within limits for demo traffic. If you somehow get viral traffic, you'll see bandwidth warnings.

**5. Cold-start during a long-running request.** If the API is asleep when Gradio calls it, the call hangs for ~30s waiting for wake-up. The pre-warm helps; setting a longer timeout on the Gradio-side `httpx.post` to `/analyze` helps more. Make sure your client timeout is ≥45s.

**6. Two services, one repo, parallel builds.** Render builds both services in parallel from the same repo. If your `render.yaml` is wrong, *both* fail and the error messages are interleaved. Read each service's logs separately.

---

## What we explicitly defer

- ❌ **Custom domain.** Render supports it; not worth the DNS hassle for v1. `dealscout-ui.onrender.com` is fine.
- ❌ **Background workers.** Render has a "background worker" service type; we're using `web` for both because Gradio + FastAPI need a web port. If you ever need true background tasks, you'd add a third service.
- ❌ **Database.** Render Postgres is one click; we're not using it. Memos written to ephemeral disk; lost on restart. Acceptable for demo.
- ❌ **CI/CD.** Render auto-deploys on push to main. That IS your CI/CD for v1. GitHub Actions for tests can come later.
- ❌ **Multi-region or auto-scaling.** Free tier is single-region, single-instance. Fine.
- ❌ **Persistent rate-limit storage.** In-memory; resets on restart. A determined abuser could trigger a redeploy to reset. For demo scale, acceptable.

---

## Definition of done

- [ ] Steps 1–14 above all complete
- [ ] You can hand the live URL to a stranger and they can generate a memo
- [ ] You can `curl https://dealscout-api.onrender.com/health` and get a 200
- [ ] Total LLM cost for verification ≤ $0.60
- [ ] LinkedIn screenshot captured and committed
- [ ] README is the kind of file you'd be proud to point a hiring manager at
- [ ] Committed on branch `feature/11-deploy` and merged to main

---

## Session plan

About 3 hours of focused work.

1. **20 min** — Steps 1, 2. Rotate keys, set spend caps. Boring but the most important.
2. **45 min** — Steps 3, 4, 5. Rate limit code, port env vars, pre-warm ping. Test all of this locally before pushing.
3. **20 min** — Steps 6, 7, 8. Generate requirements.txt, write render.yaml, audit gitignore.
4. **30 min** — Step 9. README. Don't rush this — it's the most-read artifact in your repo.
5. **5 min** — Step 10. Push to GitHub.
6. **40 min** — Step 11. Render Blueprint deploy. Most of this is staring at build logs.
7. **15 min** — Step 12. Cost-guard verification on the live URL.
8. **15 min** — Steps 13, 14. Screenshot, README update, final commit.

**Mandatory pauses where I want you to ping me:**

- After Step 5 (local pre-warm + rate limit working) — share the rate-limit test output.
- After Step 11 (Render build complete) — share build logs (success or failure either way).
- Before posting on LinkedIn — share the screenshot and the post text. Final sanity check.

---

## What to add to `my_work/learnings.md` after F11

1. *Why two services on Render instead of one? What does the separation buy me that one process wouldn't?*
2. *What are the three independent cost guards in my deployment, and what would break if one of them was missing?*
3. *The free tier sleeps after 15min idle. Why did I accept that constraint instead of paying $7/mo to avoid it? Under what circumstances would I upgrade?*
4. *If I had to deploy this for a real production user base (1000 memos/day), what would I change first? Second? Third?*

The fourth question is interview prep. Be able to answer it.

---

## After F11

You have a deployed AI system with a public URL. That's a real artifact.

What's next is the LinkedIn post itself — the artifact that translates "I built this" into "people see I built this." Don't rush it. The post is its own piece of work, worth a focused half-hour.

Then the project enters maintenance mode. F07 (evals) remains the highest-value next feature if/when you have time. F08 (prompt iteration) follows naturally. But those are *enhancements*; what you've shipped is already a complete portfolio piece.
