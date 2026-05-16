# F00 — Project Scaffolding & LLM Adapter (Gemini)

**Phase:** 0 — Foundations
**Depends on:** Nothing
**Blocks:** Every other feature
**Estimated time:** 1 session (2–3 hours focused work)
**Base LLM provider:** Google Gemini (via OpenAI-compatible endpoint)

---

## Why this feature exists

Before any agent code, we need three things in place:

1. **A Python project that actually runs.** `uv`, dependencies, Python 3.11+, a working entry point.
2. **A configuration system** that reads `.env`, validates types, fails loudly on missing keys. No `os.getenv()` scattered everywhere.
3. **A single LLM adapter** that every other piece of code goes through. This is the most important architectural decision in the whole project — get it right now and you get tracing, retries, provider swapping, and testability for free.

**Why Gemini specifically:** Google has a generous free tier (development cost ≈ $0), Flash is cheap enough at scale, and the OpenAI Agents SDK supports it natively via Gemini's OpenAI-compatible endpoint. We get the same SDK ergonomics as if we were using OpenAI directly.

---

## Provider strategy: Gemini via OpenAI-compatible endpoint

Google exposes an OpenAI-compatible API at:
```
https://generativelanguage.googleapis.com/v1beta/openai/
```

We point the OpenAI Agents SDK at this base URL with a Gemini API key. To the SDK, it looks like OpenAI; to us, we get Gemini's models and pricing.

**Alternatives we're NOT using and why:**
- **LiteLLM (`agents[litellm]`)** — adds a dependency and indirection; the OpenAI-compatible endpoint is simpler.
- **Direct `google-genai` SDK** — bypasses the Agents SDK's tooling, handoffs, and tracing. Don't.

---

## What "done" looks like

You can run this and it works:

```bash
uv sync
docker compose up -d langfuse
uv run python -m dealscout.smoke
```

Output: one line saying *"OK: gemini-2.0-flash responded."* Plus a trace appearing at http://localhost:3000 in Langfuse showing the call.

If both are true, F00 is done. If either is flaky, F00 is not done.

---

## Build order within this feature

### Step 1 — Project skeleton

```
dealscout/
├── pyproject.toml
├── .env.example                # template, committed
├── .env                        # real keys, GITIGNORED
├── .gitignore
├── docker-compose.yml          # Langfuse local
├── README.md                   # placeholder for now
├── prompts/                    # empty for now
├── src/dealscout/
│   ├── __init__.py
│   ├── config.py               # Pydantic Settings
│   ├── smoke.py                # smoke test entry point
│   ├── adapters/
│   │   ├── __init__.py
│   │   └── llm.py              # THE adapter
│   ├── observability/
│   │   ├── __init__.py
│   │   └── tracing.py          # Langfuse wiring
│   ├── agents/                 # empty
│   ├── tools/                  # empty
│   ├── domain/                 # empty
│   └── pipelines/              # empty
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── __init__.py
│   │   └── test_llm_adapter.py
│   └── integration/
│       ├── __init__.py
│       └── test_llm_adapter_real.py
└── my_work/                    # sandbox, gitignored contents except README
```

**Acceptance:** the tree exists; empty `__init__.py` in each package; `.gitignore` excludes `.env`, `*.db`, `__pycache__/`, `.venv/`, `my_work/*` (with `!my_work/README.md` exception).

### Step 2 — `pyproject.toml`

```toml
[project]
name = "dealscout"
version = "0.1.0"
description = "AI deal-flow analyst (Gemini-powered)"
requires-python = ">=3.11"
dependencies = [
    "openai-agents>=0.0.x",       # verify the current pin
    "openai>=1.40",               # required by the Agents SDK; we use it directly to configure the Gemini client
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "python-dotenv>=1.0",
    "langfuse>=2.0",
    "httpx>=0.27",
    "tenacity>=8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "respx>=0.20",
    "ruff>=0.5",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = ["integration: real LLM, costs money (free tier on Gemini)"]
```

**Gotcha for Claude:** verify the actual current package name for the OpenAI Agents SDK before pinning. Latest as of writing is `openai-agents` on PyPI but check the SDK's official docs.

### Step 3 — `config.py` (Gemini-aware)

```python
# src/dealscout/config.py
from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM provider: Gemini via OpenAI-compatible endpoint ---
    gemini_api_key: str
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    # Model tier mapping — same idea as OpenAI's mini/4o split, but Gemini.
    # VERIFY current model names against Google's docs before pinning;
    # Google renames these frequently.
    default_model: str = "gemini-2.0-flash"
    orchestrator_model: str = "gemini-2.5-pro"   # heavier reasoning
    researcher_model: str = "gemini-2.0-flash"   # tool-heavy, fast
    intake_model: str = "gemini-2.0-flash"

    # --- Observability ---
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3000"

    # --- Limits ---
    default_max_turns: int = 10
    default_tool_timeout_seconds: float = 30.0

settings = Settings()  # singleton
```

**Why a singleton:** importing `from dealscout.config import settings` everywhere is fine because Pydantic validates at import time. Missing `GEMINI_API_KEY` → the whole app fails to start. *No silent fallbacks for required values.*

**Acceptance:** `python -c "from dealscout.config import settings; print(settings.default_model)"` prints `gemini-2.0-flash`. Removing `GEMINI_API_KEY` from `.env` makes import fail loudly.

### Step 4 — `.env.example`

```bash
# Required — get from https://aistudio.google.com/apikey
GEMINI_API_KEY=AIza...

# Optional — defaults are fine for dev
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
DEFAULT_MODEL=gemini-2.0-flash
ORCHESTRATOR_MODEL=gemini-2.5-pro
RESEARCHER_MODEL=gemini-2.0-flash
INTAKE_MODEL=gemini-2.0-flash

# Observability — leave empty to disable tracing
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=http://localhost:3000
```

**Commit `.env.example`. Never commit `.env`.**

### Step 5 — The LLM adapter (Gemini-pointed)

This is the heart of F00. The OpenAI Agents SDK can be configured to use any OpenAI-compatible endpoint. We configure it once, globally, to point at Gemini.

```python
# src/dealscout/adapters/llm.py
from __future__ import annotations
from typing import Protocol, runtime_checkable
from openai import AsyncOpenAI
from agents import (
    Agent, Runner, RunResult,
    OpenAIChatCompletionsModel,
    set_default_openai_client,
    set_default_openai_api,
    set_tracing_disabled,
)
from dealscout.config import settings

# -----------------------------------------------------------------------------
# Provider wiring (called once at startup)
# -----------------------------------------------------------------------------
# We point the SDK's "default OpenAI client" at Gemini's compatible endpoint.
# After this, every Agent in the project hits Gemini unless explicitly overridden.
# -----------------------------------------------------------------------------
def configure_provider() -> None:
    """Wire the OpenAI Agents SDK to talk to Gemini.
    Call once at process startup before any Agent is instantiated."""
    gemini_client = AsyncOpenAI(
        api_key=settings.gemini_api_key,
        base_url=settings.gemini_base_url,
    )
    set_default_openai_client(gemini_client)
    # Gemini's OpenAI-compatible endpoint uses chat-completions, not Responses API.
    set_default_openai_api("chat_completions")

# Helper to build a model object that's already pointing at our configured client.
# Tools and Agents accept either a model name string or a model object — we use
# objects to avoid relying on global state being set in the right order.
def build_model(model_name: str) -> OpenAIChatCompletionsModel:
    """Build a Gemini-backed model wrapper for use in Agent(model=...)."""
    return OpenAIChatCompletionsModel(
        model=model_name,
        openai_client=AsyncOpenAI(
            api_key=settings.gemini_api_key,
            base_url=settings.gemini_base_url,
        ),
    )

# -----------------------------------------------------------------------------
# Adapter protocol + impls
# -----------------------------------------------------------------------------
@runtime_checkable
class LLMClient(Protocol):
    """Anything that can run an agent. Real or fake."""
    async def run(self, agent: Agent, input: str, max_turns: int | None = None) -> RunResult: ...

class RealLLMClient:
    """Wraps Runner.run with our default limits."""
    async def run(self, agent: Agent, input: str, max_turns: int | None = None) -> RunResult:
        return await Runner.run(
            agent,
            input,
            max_turns=max_turns or settings.default_max_turns,
        )

class FakeLLMClient:
    """Returns scripted responses. Used by unit tests.
    Tests register responses by agent name."""
    def __init__(self) -> None:
        self._responses: dict[str, str] = {}

    def register(self, agent_name: str, response: str) -> None:
        self._responses[agent_name] = response

    async def run(self, agent: Agent, input: str, max_turns: int | None = None) -> RunResult:
        # Build a minimal RunResult-shaped object. The exact shape depends on
        # the installed SDK version — verify before committing.
        ...

# The one place anyone instantiates the client.
def get_llm_client() -> LLMClient:
    return RealLLMClient()
```

**Why this shape:**
- `configure_provider()` is called once at startup and rewires the SDK's *default* client. After that, every `Agent(...)` you construct without specifying a model will hit Gemini.
- `build_model(name)` is the belt-and-suspenders option: each agent gets its own model object explicitly bound to Gemini, with no reliance on global state. Use this in agents.
- `Protocol` for `LLMClient` lets tests swap in `FakeLLMClient` without subclassing.
- `get_llm_client()` is a factory (not a module-level instance) so tests can monkeypatch it cleanly.

**Critical gotcha for Claude:** the exact import names (`set_default_openai_client`, `set_default_openai_api`, `OpenAIChatCompletionsModel`) are SDK-version-dependent. **Verify against the installed SDK** by running `python -c "import agents; print(dir(agents))"` before writing the wiring. If names differ, adapt — but the *shape* of the solution (override the default client + use chat-completions API) is correct.

### Step 6 — Observability wiring (Langfuse + Gemini)

Langfuse needs to capture traces. The simplest path with the OpenAI Agents SDK + a custom (Gemini) OpenAI client is to instrument the OpenAI client itself with Langfuse's OpenAI wrapper.

```python
# src/dealscout/observability/tracing.py
from __future__ import annotations
from dealscout.config import settings

def init_tracing() -> None:
    """Wire Langfuse to capture LLM calls.
    No-op if Langfuse keys are not set."""
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return

    # Langfuse exposes drop-in OpenAI instrumentation.
    # Verify the current import path against the installed Langfuse version:
    #   from langfuse.openai import openai   (older API)
    #   from langfuse import Langfuse        (newer; may need OpenTelemetry plug)
    #
    # The cleanest path with the OpenAI Agents SDK + Gemini's compatible endpoint
    # is OpenTelemetry-based auto-instrumentation. Confirm before coding.
    ...
```

**Gotcha:** Langfuse has changed its integration story several times. For F00, getting *any* trace into Langfuse is the goal — even if it requires their OpenTelemetry path. If Langfuse setup looks like it'll take >45 min, ship F00 with `init_tracing()` as a no-op and a TODO. Trace integration can be polished as a sub-feature.

### Step 7 — `docker-compose.yml` for local Langfuse

Pull the official Langfuse compose file from their docs. Do not write from scratch.

```bash
docker compose up -d langfuse
# Visit http://localhost:3000, create a project, copy the keys to .env
```

**Acceptance:** Langfuse UI loads at localhost:3000, project created, keys in `.env`.

### Step 8 — The smoke test (Gemini-aware)

```python
# src/dealscout/smoke.py
"""Smoke test: prove the LLM adapter works end-to-end with Gemini.

Run: uv run python -m dealscout.smoke
Expected output: 'OK: <model> responded.'
Expected side effect: trace appears in Langfuse (if configured).
"""
from __future__ import annotations
import asyncio
from agents import Agent
from dealscout.adapters.llm import configure_provider, get_llm_client, build_model
from dealscout.config import settings
from dealscout.observability.tracing import init_tracing

async def main() -> None:
    configure_provider()   # Wire the SDK to Gemini
    init_tracing()         # Wire Langfuse (no-op if keys missing)

    agent = Agent(
        name="SmokeTestAgent",
        instructions="You are a helpful assistant. Reply in one short sentence.",
        model=build_model(settings.default_model),
    )
    client = get_llm_client()
    result = await client.run(agent, "Say 'hello' and the word 'OK'.")
    print(f"OK: response received from {settings.default_model}")
    print(f"Output: {result.final_output}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Acceptance:**
1. `uv run python -m dealscout.smoke` prints OK and a Gemini response.
2. If Langfuse is configured, a trace appears for the run.
3. Running it with `GEMINI_API_KEY` removed from `.env` fails *at config load*, not in the middle of the call.

### Step 9 — One unit test, one integration test

```python
# tests/unit/test_llm_adapter.py
from dealscout.adapters.llm import FakeLLMClient, LLMClient

def test_fake_llm_client_satisfies_protocol():
    fake = FakeLLMClient()
    assert isinstance(fake, LLMClient)
```

```python
# tests/integration/test_llm_adapter_real.py
import pytest
from agents import Agent
from dealscout.adapters.llm import configure_provider, build_model, get_llm_client
from dealscout.config import settings

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_gemini_responds():
    configure_provider()
    agent = Agent(
        name="TestAgent",
        instructions="Reply with the single word 'pong'.",
        model=build_model(settings.default_model),
    )
    client = get_llm_client()
    result = await client.run(agent, "ping")
    assert "pong" in result.final_output.lower()
```

**Acceptance:**
- `uv run pytest tests/unit` passes fast, no network.
- `uv run pytest tests/integration -m integration` passes against real Gemini (likely free).

---

## Gemini-specific gotchas to flag for me

When working through this feature (and later ones), surface these if they come up:

- **Verify model names.** Google renames Gemini models often. Before pinning `gemini-2.0-flash` and `gemini-2.5-pro`, check the current available models at the AI Studio docs. The pricing page is also a good place to see what's stable.
- **Free tier limits exist.** Gemini's free tier rate-limits requests per minute. Smoke tests are fine; the eval harness (F07, 10 startups × ~20 calls) may bump against limits. Have a paid key ready.
- **Tool calling may parse args differently.** Gemini sometimes returns tool args as a dict where OpenAI returns a JSON string. The SDK should normalize, but if you see weird JSON errors in F02, this is the first suspect.
- **Parallel tool calls may not work on every Gemini model via the compatible endpoint.** If F05 (Orchestrator calling researchers in parallel) silently runs them serially, that's likely why. Acceptable; we just note it.
- **Structured outputs are supported** but the path through the compatible endpoint sometimes differs from native OpenAI behavior. Test the Memo Writer (F06) carefully when we get there.
- **No "Responses API"** — Gemini's compatible endpoint uses chat-completions only. That's why we call `set_default_openai_api("chat_completions")`.

---

## What we explicitly defer

- ❌ Defining any non-test agent. Save it for F01.
- ❌ Building the FastAPI service. F10.
- ❌ Adding a database. F10.
- ❌ Wiring a second provider (OpenAI, Anthropic). The adapter shape supports it via different `build_model` factories; we add when there's a concrete reason.
- ❌ Pre-building a project-wide error taxonomy. Add error classes when needed.

---

## Definition of done — the checklist

- [ ] Directory tree matches the layout above.
- [ ] `.env.example` committed with `GEMINI_API_KEY` placeholder; `.env` exists locally and is gitignored.
- [ ] `uv sync` completes with no errors.
- [ ] `uv run python -c "from dealscout.config import settings"` succeeds.
- [ ] Removing `GEMINI_API_KEY` from `.env` makes import fail with a clear Pydantic error.
- [ ] `docker compose up -d langfuse` brings up Langfuse at localhost:3000.
- [ ] `uv run python -m dealscout.smoke` prints OK and a real Gemini response.
- [ ] If Langfuse is fully wired: a trace appears for the smoke run. (Acceptable to defer trace wiring with TODO if it gets stuck.)
- [ ] `uv run pytest tests/unit` passes.
- [ ] `uv run pytest tests/integration -m integration` passes.
- [ ] `.gitignore` covers `.env`, `*.db`, `__pycache__/`, `.venv/`, `my_work/*` (with `!my_work/README.md`).
- [ ] Committed on branch `feature/00-foundations`.

---

## Session plan

Roughly 2–3 hours. Don't try to one-shot it.

1. **30 min** — Steps 1–4. Directory layout, `pyproject.toml`, `config.py`, `.env.example`. Verify imports work.
2. **45 min** — Step 5. LLM adapter. **Verify SDK API names first** by running `python -c "import agents; print([x for x in dir(agents) if 'openai' in x.lower() or 'model' in x.lower()])"` before writing wiring.
3. **30 min** — Steps 6–7. Langfuse wiring + compose up. If trace integration looks complicated, TODO it and move on.
4. **30 min** — Step 8. Smoke test green against real Gemini.
5. **30 min** — Step 9. Unit + integration tests green.
6. **15 min** — `.gitignore` audit, README placeholder, commit.

If any step takes >2× estimate, stop and tell me. Likely cause: SDK version mismatch on import names, or Langfuse setup ate the budget.
