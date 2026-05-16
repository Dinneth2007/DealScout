# F01 — Intake (Triage + URL/PDF Handoffs)

**Phase:** 1 — Intake
**Depends on:** F00 (LLM adapter, Gemini wired, Langfuse working)
**Blocks:** F02 (Company Researcher needs `StartupBrief` to consume)
**Estimated time:** 1 long session or 2 short sessions (3–4 hours focused work)

---

## Why this feature exists

Every downstream agent — researchers, orchestrator, memo writer — needs the same starting point: a normalized `StartupBrief` describing the company. F01 is the *contract layer*. It takes messy user input (a URL string or a PDF path) and produces a clean, typed object.

We could do this with plain Python (regex to detect URLs, route to two functions). We're deliberately not, because **F01 is also the project's first multi-agent pattern: handoffs.** Learning handoffs here, on a low-stakes task, means you'll wield them confidently in F05 (Orchestrator) and any future project.

---

## Mental model — read this carefully

This is the most important conceptual section in F01. Reread it if you get confused later.

### Handoff vs. agent-as-tool — the one distinction that matters

**Handoff:** "I'm not the right agent for this. The conversation now belongs to that agent." Triage is *done* after the handoff. URL Intake takes over completely.

**Agent-as-tool:** "I need a result from a specialist, then I'll continue." The caller stays in control. The specialist returns, the caller decides what to do next.

| | Handoff | Agent-as-tool |
|---|---------|---------------|
| Who continues after the call? | The new agent | The caller |
| What does the caller see? | Nothing — it's done | A return value |
| Best for | Role changes, takeovers | Subroutine calls, parallel specialists |

F01 uses **handoffs** because intake is a role change. Triage's only job is routing — once it's picked the right intake agent, it has nothing left to contribute.

F02 onwards will use **agents-as-tools** because researchers are subroutines the Orchestrator coordinates.

**Why you must internalize this:** people accidentally use the wrong one constantly. Symptoms: orchestrator agents that "forget" what they were doing after delegating (handoff used where as_tool was correct), or specialist agents that loop forever trying to summarize back to a caller (as_tool used where handoff was correct).

### F01 architecture

```
                   Raw input (str)
                         │
                         ▼
            ┌────────────────────────┐
            │     Triage Agent       │
            │   model: flash         │
            │   no tools             │
            │   handoffs:            │
            │     - URLIntake        │
            │     - PDFIntake        │
            └───────────┬────────────┘
                        │
              handoff (LLM picks one)
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
   ┌──────────────────┐   ┌──────────────────┐
   │  URL Intake      │   │  PDF Intake      │
   │  model: flash    │   │  model: flash    │
   │  tools:          │   │  tools:          │
   │    - fetch_url   │   │    - parse_pdf   │
   │  output_type:    │   │  output_type:    │
   │    StartupBrief  │   │    StartupBrief  │
   └─────────┬────────┘   └────────┬─────────┘
             │                     │
             └──────────┬──────────┘
                        ▼
                  StartupBrief
                  (Pydantic)
```

### What `StartupBrief` is

The contract between F01 and everything downstream. Every field should be derivable from a URL or a deck. Nothing here requires external research.

```python
class StartupBrief(BaseModel):
    name: str                        # "Stripe"
    one_liner: str                   # "Payments infrastructure for the internet"
    source_type: Literal["url", "pdf"]
    source_ref: str                  # original URL or filepath
    raw_text: str                    # the scraped/parsed text we'll pass to researchers
    detected_url: str | None = None  # for PDFs, if we found a URL inside
    headers_or_sections: list[str] = []  # nav items / deck slide titles — gives structure hints
```

Researchers in F02 will receive this. The `raw_text` is what they read; the `headers_or_sections` are hints. We deliberately don't try to extract things like "industry," "stage," or "TAM" here — those are research jobs.

---

## Key design decisions (the learning bit)

For each decision: **what**, **why**, **how it would burn you**, **transferable principle**.

### Decision 1 — LLM-driven Triage instead of Python regex

**What:** Triage is an LLM agent, not a Python `if/else` on `input.startswith("http")`.

**Why:** Two reasons. (1) Real inputs are messier than you think — users paste URLs with trailing whitespace, file paths that look like domains, S3 URLs, file:// URIs. An LLM router is more tolerant. (2) Pedagogically, we want to learn handoffs on a simple task before doing them on a hard one.

**How it would burn you:** In production at high QPS this is overkill — every analysis pays one LLM call (~50ms, ~$0.0001) just to do `instanceof`. For a research-memo product running tens of analyses per day, it's invisible. If you ever build something that triages millions of requests, fall back to Python.

**Transferable principle:** *Match the routing technology to the routing complexity.* Regex for simple cases, LLM for ambiguous cases, fine-tuned classifier for high-volume + ambiguous. Don't reach for an LLM router by default in production; do reach for it when learning the pattern or when the input is genuinely fuzzy.

### Decision 2 — Handoffs, not agents-as-tools

**What:** Triage uses `handoffs=[url_intake, pdf_intake]`, not `tools=[url_intake.as_tool(...), pdf_intake.as_tool(...)]`.

**Why:** Intake is a *role change*. Triage's job is done once it's picked the right intake agent. There's nothing for Triage to do with the result — it doesn't summarize, synthesize, or post-process. The conversation belongs to Intake from that point on.

**How it would burn you:** If you used `as_tool`, Triage would receive the `StartupBrief` back, then have to either (a) return it verbatim (which is a wasted LLM call to do nothing) or (b) "summarize" it (which would degrade the structured output). Both are worse than just handing the conversation over.

**Transferable principle:** *Use handoffs for role changes, agents-as-tools for subroutine calls.* The test: after the called agent finishes, does the caller have meaningful work to do? Yes → tool. No → handoff.

### Decision 3 — Two narrow intake agents, not one polymorphic one

**What:** Two separate agents (URLIntake, PDFIntake) with their own prompts and tools, not one IntakeAgent with both tools.

**Why:** The optimal prompt for "extract structure from scraped HTML" is different from "extract structure from PDF pages." A polymorphic agent would have a longer, more confusing prompt; its tool choice would be slightly less reliable; and its eval rubrics would mush together. Two narrow agents are clearer to write, test, and prompt-engineer.

**How it would burn you:** A "do-everything" agent quietly underperforms — you don't notice because there's no comparison, but its accuracy plateaus 10–15 points below what specialized agents achieve. By F07, your evals will show it; by F08, you'd be refactoring back to specialists.

**Transferable principle:** *Narrow agents beat polymorphic agents.* The rule of thumb: if you can describe two distinct prompts on a single page, they're probably two agents.

### Decision 4 — `output_type=StartupBrief` on the intake agents (structured output)

**What:** Both intake agents declare `output_type=StartupBrief`. The SDK enforces that the final message parses into the Pydantic schema.

**Why:** Free-form text outputs are great for chatbots and a disaster for pipelines. We need every downstream agent to receive the same shape. Pydantic + the SDK's structured-output support gives us that guarantee with one line.

**How it would burn you:** Without it, you'd write defensive parsing code in F02, F03, F04, F05 — six places that all have to handle the same "what if the LLM didn't include the company name" question. Each one becomes a separate bug. Schema enforcement at the boundary kills the whole class.

**Transferable principle:** *Validate at the boundary, trust within.* This is the same principle as input validation on HTTP routes. Once you trust `StartupBrief` is well-formed, every downstream agent gets simpler.

**Gemini-specific note:** structured outputs via the OpenAI-compatible endpoint sometimes need an explicit `response_format` or a `Strict` schema flag. If the SDK doesn't auto-pass this through, fall back to telling the LLM to "respond with JSON matching this schema" + a `model_validate_json` post-step. We'll only patch this if F01 evals fail.

### Decision 5 — Tools return structured dicts, not raw strings

**What:** `fetch_url` returns `{"title": str, "main_text": str, "headers": list[str], "final_url": str, "error": str | None}`. `parse_pdf` returns an analogous shape. Not just text.

**Why:** The LLM sees this structure and can reason about each piece independently. With raw text dumped at it, the LLM has to re-do the extraction work that the tool already partially did. Structure is information.

**How it would burn you:** If `fetch_url` returns just the page text, the LLM has to scan for the company name, the one-liner, the section headers — all over again. Token waste, error surface area, and slower.

**Transferable principle:** *Tools should return parsed structure, not raw bytes.* The tool is doing real work — preserve that work in the return value.

### Decision 6 — Tools degrade gracefully (return errors as data)

**What:** `fetch_url` never raises. If the request times out or 404s, it returns `{"error": "Timeout fetching url after 30s", "final_url": url, ...}` and the LLM decides what to do.

**Why:** An exception inside a tool aborts the agent run. If the URL is bad, that's not the *agent's* failure — the agent should respond "I couldn't fetch this URL; please confirm it's correct." That requires the agent to *see* the error and reason about it.

**How it would burn you:** Raise-on-failure tools make agents brittle to messy real-world inputs. Worse: they make traces useless — instead of seeing the LLM's reasoning about a failure, you see a Python stack trace.

**Transferable principle:** *In tool calling, errors are data, not exceptions.* This is opposite to typical Python style. Make peace with it.

### Decision 7 — `max_turns` set explicitly per agent

**What:** Triage gets `max_turns=2` (basically one LLM call + handoff). Intake agents get `max_turns=5` (fetch + maybe a retry + final structured output).

**Why:** Tight bounds catch runaway loops early. Triage trying to call its handoff 10 times means something is deeply wrong; better to surface that as an error than burn budget.

**How it would burn you:** Default `max_turns=10` (or unbounded if the SDK's default changed) and a misconfigured agent can rack up dozens of unnecessary calls before erroring. Hard to spot in dev, painful in prod.

**Transferable principle:** *Every agent's max_turns should reflect the agent's job complexity, not be a generic default.* If you can't justify the number, the number is wrong.

---

## Build order within this feature

### Step 1 — Define `StartupBrief` and friends

```
src/dealscout/domain/
├── __init__.py
└── brief.py
```

```python
# src/dealscout/domain/brief.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl

class StartupBrief(BaseModel):
    """The contract between intake and everything downstream.
    Every field must be derivable from a URL or a deck — NO external research."""

    name: str = Field(..., description="Company name as best detected.")
    one_liner: str = Field(..., description="One-sentence description, ideally the company's own.")
    source_type: Literal["url", "pdf"]
    source_ref: str = Field(..., description="Original URL or filepath the user provided.")
    raw_text: str = Field(..., description="Cleaned text passed to downstream researchers.")
    detected_url: str | None = Field(None, description="For PDFs, a URL found in the deck (if any).")
    headers_or_sections: list[str] = Field(default_factory=list,
        description="Page section headers or deck slide titles — structure hints.")
```

**Acceptance:** `python -c "from dealscout.domain.brief import StartupBrief; print(StartupBrief.model_json_schema())"` prints a valid JSON schema. Every downstream feature will read this file.

### Step 2 — Build the `fetch_url` tool

```
src/dealscout/adapters/
├── scraper.py            # HTTP + HTML extraction, no LLM concerns
└── ...
src/dealscout/tools/
├── __init__.py
└── fetch_url.py          # The @function_tool wrapper
```

The adapter does the messy work. The tool is a thin wrapper.

```python
# src/dealscout/adapters/scraper.py
from __future__ import annotations
import httpx
from bs4 import BeautifulSoup
from dataclasses import dataclass

@dataclass
class ScrapeResult:
    title: str
    main_text: str
    headers: list[str]
    final_url: str
    error: str | None = None

async def scrape_url(url: str, timeout_seconds: float = 30.0) -> ScrapeResult:
    """Fetch a URL and extract title, main text, and section headers.
    Never raises — returns ScrapeResult with .error populated on failure."""
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "DealScout/0.1"})
            resp.raise_for_status()
    except httpx.HTTPError as e:
        return ScrapeResult(title="", main_text="", headers=[], final_url=url, error=str(e))

    soup = BeautifulSoup(resp.text, "html.parser")
    # Strip nav, footer, scripts to reduce noise
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    title = (soup.title.string or "").strip() if soup.title else ""
    headers = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])][:20]
    main_text = " ".join(soup.get_text(" ", strip=True).split())[:8000]

    return ScrapeResult(
        title=title,
        main_text=main_text,
        headers=headers,
        final_url=str(resp.url),
    )
```

```python
# src/dealscout/tools/fetch_url.py
from __future__ import annotations
from agents import function_tool
from dealscout.adapters.scraper import scrape_url
from dealscout.config import settings

@function_tool
async def fetch_url(url: str) -> dict:
    """Fetch a URL and return its title, main text, and section headers.

    Use this when given a startup's website URL and you need to read the page.
    Do NOT use this for search — there is no search tool in intake.

    Args:
        url: A fully-qualified https URL.

    Returns:
        {
          "title": str,
          "main_text": str,    # cleaned, ~8000 chars max
          "headers": list[str],
          "final_url": str,    # after redirects
          "error": str | None  # populated if fetch failed; main_text empty
        }
    """
    result = await scrape_url(url, timeout_seconds=settings.default_tool_timeout_seconds)
    return {
        "title": result.title,
        "main_text": result.main_text,
        "headers": result.headers,
        "final_url": result.final_url,
        "error": result.error,
    }
```

**Acceptance:**
- `await scrape_url("https://stripe.com")` returns non-empty title and main_text.
- `await scrape_url("https://nonexistent-domain-xyz-12345.com")` returns a `ScrapeResult` with `error` set, doesn't raise.
- A unit test using `respx` mocks `httpx` and verifies the tool returns the expected dict.

### Step 3 — Build the `parse_pdf` tool

```
src/dealscout/adapters/
└── pdf.py                # pypdf wrapper

src/dealscout/tools/
└── parse_pdf.py
```

```python
# src/dealscout/adapters/pdf.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from pypdf import PdfReader

@dataclass
class PdfResult:
    text: str
    slide_titles: list[str]
    page_count: int
    detected_url: str | None
    error: str | None = None

async def parse_pdf_file(path: str) -> PdfResult:
    """Extract text + slide titles from a PDF. Never raises."""
    p = Path(path)
    if not p.exists() or not p.is_file():
        return PdfResult(text="", slide_titles=[], page_count=0,
                         detected_url=None, error=f"File not found: {path}")
    try:
        reader = PdfReader(str(p))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as e:
        return PdfResult(text="", slide_titles=[], page_count=0,
                         detected_url=None, error=f"PDF parse error: {e}")

    # First line of each page is often the slide title (rough but useful)
    slide_titles = []
    for page_text in pages:
        first_line = next((ln.strip() for ln in page_text.splitlines() if ln.strip()), "")
        if first_line:
            slide_titles.append(first_line[:120])

    # Crude URL detection in the full text
    import re
    urls = re.findall(r"https?://[^\s)\]\}]+", "\n".join(pages))
    detected_url = urls[0] if urls else None

    full_text = "\n".join(pages)[:16000]  # 2x scraper budget; decks are denser
    return PdfResult(
        text=full_text,
        slide_titles=slide_titles,
        page_count=len(pages),
        detected_url=detected_url,
    )
```

```python
# src/dealscout/tools/parse_pdf.py
from __future__ import annotations
from agents import function_tool
from dealscout.adapters.pdf import parse_pdf_file

@function_tool
async def parse_pdf(path: str) -> dict:
    """Parse a pitch deck PDF and return its text, slide titles, and any embedded URL.

    Use this when given a path to a PDF file. Do NOT use this for URLs.

    Args:
        path: Local filesystem path to a .pdf file.

    Returns:
        {
          "text": str,                  # extracted text, ~16000 chars max
          "slide_titles": list[str],    # first line of each page, rough
          "page_count": int,
          "detected_url": str | None,   # first URL found inside the deck
          "error": str | None
        }
    """
    result = await parse_pdf_file(path)
    return {
        "text": result.text,
        "slide_titles": result.slide_titles,
        "page_count": result.page_count,
        "detected_url": result.detected_url,
        "error": result.error,
    }
```

**Acceptance:**
- Calling `parse_pdf_file` on a known deck returns non-empty text + slide titles.
- Calling on a missing file returns `error` set, doesn't raise.
- A unit test uses a tiny test fixture PDF (`tests/fixtures/sample_deck.pdf`).

### Step 4 — Write the three system prompts

Prompts live in `prompts/` and are versioned. Filename convention: `<role>_v1.md`.

```
prompts/
├── triage_v1.md
├── url_intake_v1.md
└── pdf_intake_v1.md
```

Template for each:

```markdown
# Role: Triage (v1)
Purpose: Route the user's input to the correct intake specialist.
Inputs: a single raw string (URL or filepath).
Outputs: a handoff to URLIntake or PDFIntake.
Last evaluated: TBD on eval set v1, pass rate: N/A (initial)

---

You are the Triage Agent for DealScout.

Your only job is to decide whether the user's input is:
- a URL (starts with http:// or https://, or is clearly a domain) → hand off to URLIntake
- a PDF file path (ends with .pdf, or is a path) → hand off to PDFIntake

Do not attempt to fetch or parse anything yourself. Do not respond with text — always hand off.

If the input is ambiguous (e.g., a string with no scheme and no .pdf), prefer URLIntake and prepend "https://" mentally.
```

```markdown
# Role: URLIntake (v1)
Purpose: Given a URL, fetch it and produce a StartupBrief.
Inputs: a URL string.
Outputs: StartupBrief (Pydantic).

---

You are the URL Intake Agent for DealScout.

Workflow:
1. Call fetch_url with the given URL.
2. If `error` is set, respond with a StartupBrief where name="Unknown", one_liner="Unable to fetch", and raw_text includes the error.
3. Otherwise, extract:
   - name: from the title or the most prominent brand mention in headers/main_text.
   - one_liner: the company's own tagline if found, else a one-sentence summary you derive.
   - raw_text: the main_text from the tool, verbatim.
   - headers_or_sections: the headers array from the tool.
   - source_type: "url"
   - source_ref: the original URL.

Do not invent details. If the page doesn't say what the company does, the one_liner should be "Unclear from landing page."
```

```markdown
# Role: PDFIntake (v1)
Purpose: Given a PDF path, parse it and produce a StartupBrief.
Inputs: a filesystem path to a PDF.
Outputs: StartupBrief (Pydantic).

---

You are the PDF Intake Agent for DealScout.

Workflow:
1. Call parse_pdf with the given path.
2. If `error` is set, respond with a StartupBrief where name="Unknown", one_liner="Unable to parse PDF", and raw_text includes the error.
3. Otherwise, extract:
   - name: from the first slide's title, or the most prominent company name in the deck.
   - one_liner: from the deck's "vision" or "what we do" slide, or derive from the first 2-3 slides.
   - raw_text: the text from the tool, verbatim.
   - headers_or_sections: the slide_titles from the tool.
   - source_type: "pdf"
   - source_ref: the original path.
   - detected_url: the detected_url from the tool, if any.

Do not invent details. If the deck doesn't explain what the company does, one_liner should be "Unclear from deck."
```

**Acceptance:** all three files exist; each loads via a `load_prompt(name)` helper (next step).

### Step 5 — Prompt loader

```python
# src/dealscout/prompts/__init__.py
from __future__ import annotations
from pathlib import Path
import re

PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"

def load_prompt(name: str, version: int | None = None) -> str:
    """Load prompts/<name>_v<N>.md. If version is None, picks the highest-numbered file."""
    candidates = sorted(PROMPTS_DIR.glob(f"{name}_v*.md"))
    if not candidates:
        raise FileNotFoundError(f"No prompt file matching {name}_v*.md in {PROMPTS_DIR}")
    if version is not None:
        target = PROMPTS_DIR / f"{name}_v{version}.md"
        if not target.exists():
            raise FileNotFoundError(f"Prompt {target} does not exist")
        return target.read_text(encoding="utf-8")
    return candidates[-1].read_text(encoding="utf-8")
```

**Acceptance:** `load_prompt("triage")` returns the file contents as a string.

### Step 6 — Build the three agents

```
src/dealscout/agents/
├── __init__.py
├── triage.py
├── url_intake.py
└── pdf_intake.py
```

```python
# src/dealscout/agents/url_intake.py
from __future__ import annotations
from agents import Agent
from dealscout.adapters.llm import build_model
from dealscout.config import settings
from dealscout.domain.brief import StartupBrief
from dealscout.prompts import load_prompt
from dealscout.tools.fetch_url import fetch_url

def build_url_intake_agent() -> Agent:
    return Agent(
        name="URLIntake",
        instructions=load_prompt("url_intake"),
        tools=[fetch_url],
        model=build_model(settings.intake_model),
        output_type=StartupBrief,
    )
```

```python
# src/dealscout/agents/pdf_intake.py
from __future__ import annotations
from agents import Agent
from dealscout.adapters.llm import build_model
from dealscout.config import settings
from dealscout.domain.brief import StartupBrief
from dealscout.prompts import load_prompt
from dealscout.tools.parse_pdf import parse_pdf

def build_pdf_intake_agent() -> Agent:
    return Agent(
        name="PDFIntake",
        instructions=load_prompt("pdf_intake"),
        tools=[parse_pdf],
        model=build_model(settings.intake_model),
        output_type=StartupBrief,
    )
```

```python
# src/dealscout/agents/triage.py
from __future__ import annotations
from agents import Agent
from dealscout.adapters.llm import build_model
from dealscout.config import settings
from dealscout.prompts import load_prompt
from dealscout.agents.url_intake import build_url_intake_agent
from dealscout.agents.pdf_intake import build_pdf_intake_agent

def build_triage_agent() -> Agent:
    url_intake = build_url_intake_agent()
    pdf_intake = build_pdf_intake_agent()

    return Agent(
        name="Triage",
        instructions=load_prompt("triage"),
        handoffs=[url_intake, pdf_intake],   # <-- THE handoff pattern
        model=build_model(settings.default_model),
    )
```

**Gotcha for Claude:** verify the exact parameter name for handoffs in the installed SDK. It may be `handoffs=` (list of Agents) or `handoff=` (singular). Run `python -c "from agents import Agent; help(Agent.__init__)"` if unsure.

### Step 7 — Pipeline entry point

```
src/dealscout/pipelines/
├── __init__.py
└── intake.py
```

```python
# src/dealscout/pipelines/intake.py
from __future__ import annotations
from dealscout.adapters.llm import configure_provider, get_llm_client
from dealscout.agents.triage import build_triage_agent
from dealscout.domain.brief import StartupBrief

async def run_intake(raw_input: str) -> StartupBrief:
    """Run the full intake pipeline: Triage → URL/PDF Intake → StartupBrief.

    Caller is responsible for calling configure_provider() once before invoking this.
    """
    triage = build_triage_agent()
    client = get_llm_client()
    result = await client.run(triage, raw_input, max_turns=8)
    # After handoff + intake, the final output should be a StartupBrief
    if not isinstance(result.final_output, StartupBrief):
        raise RuntimeError(
            f"Intake did not produce a StartupBrief; got {type(result.final_output)}"
        )
    return result.final_output
```

**Acceptance:** `await run_intake("https://stripe.com")` returns a `StartupBrief` with non-empty name and one_liner.

### Step 8 — Smoke test for F01

Replace (or augment) the existing smoke test:

```python
# src/dealscout/smoke.py
"""Smoke test through F01: runs the full intake pipeline on a known URL."""
from __future__ import annotations
import asyncio
from dealscout.adapters.llm import configure_provider
from dealscout.observability.tracing import init_tracing
from dealscout.pipelines.intake import run_intake

async def main() -> None:
    configure_provider()
    init_tracing()
    brief = await run_intake("https://stripe.com")
    print(f"OK: name={brief.name!r}")
    print(f"    one_liner={brief.one_liner!r}")
    print(f"    headers ({len(brief.headers_or_sections)}): {brief.headers_or_sections[:3]}")
    print(f"    raw_text ({len(brief.raw_text)} chars): {brief.raw_text[:200]}...")

if __name__ == "__main__":
    asyncio.run(main())
```

**Acceptance:** running it prints a recognizable description of Stripe and a trace shows up in Langfuse with the handoff visible.

### Step 9 — Tests

Three unit tests, two integration tests.

```python
# tests/unit/test_scraper.py
import pytest
import respx
import httpx
from dealscout.adapters.scraper import scrape_url

@pytest.mark.asyncio
async def test_scrape_url_extracts_title_and_headers():
    sample_html = """
        <html><head><title>Acme - Payments</title></head>
        <body><h1>Acme</h1><h2>Pricing</h2><p>We do payments.</p></body></html>
    """
    with respx.mock:
        respx.get("https://acme.example").mock(return_value=httpx.Response(200, text=sample_html))
        result = await scrape_url("https://acme.example")
    assert result.title == "Acme - Payments"
    assert "Acme" in result.headers
    assert result.error is None

@pytest.mark.asyncio
async def test_scrape_url_returns_error_on_404():
    with respx.mock:
        respx.get("https://acme.example").mock(return_value=httpx.Response(404))
        result = await scrape_url("https://acme.example")
    assert result.error is not None
    assert result.main_text == ""
```

```python
# tests/unit/test_pdf_adapter.py
import pytest
from dealscout.adapters.pdf import parse_pdf_file

@pytest.mark.asyncio
async def test_parse_pdf_returns_error_on_missing_file():
    result = await parse_pdf_file("/nonexistent/path.pdf")
    assert result.error is not None
    assert result.text == ""
```

```python
# tests/integration/test_intake_pipeline.py
import pytest
from dealscout.adapters.llm import configure_provider
from dealscout.pipelines.intake import run_intake

@pytest.mark.integration
@pytest.mark.asyncio
async def test_intake_url_produces_valid_brief():
    configure_provider()
    brief = await run_intake("https://stripe.com")
    assert brief.source_type == "url"
    assert len(brief.name) > 0
    assert len(brief.raw_text) > 200
    assert brief.one_liner != ""

@pytest.mark.integration
@pytest.mark.asyncio
async def test_intake_pdf_produces_valid_brief(tmp_path):
    # Use the fixture deck if you have one, else skip
    import pathlib
    fixture = pathlib.Path("tests/fixtures/sample_deck.pdf")
    if not fixture.exists():
        pytest.skip("sample_deck.pdf fixture not present")
    configure_provider()
    brief = await run_intake(str(fixture))
    assert brief.source_type == "pdf"
    assert len(brief.name) > 0
```

**Acceptance:**
- `uv run pytest tests/unit` passes fast.
- `uv run pytest tests/integration -m integration` passes (URL test always; PDF test if fixture exists).

---

## Gemini-specific gotchas to flag for me

When working through this feature, surface these:

- **Handoffs depend on tool calling under the hood.** If Triage doesn't hand off and instead responds with text like "I would hand off to URLIntake," the LLM didn't actually invoke the handoff tool. Cause: usually the SDK didn't register the handoff as a function the LLM can see. Run with verbose tracing to confirm.
- **Structured output via the OpenAI-compatible endpoint.** If `output_type=StartupBrief` fails (LLM returns text that doesn't parse), fall back to: instruct the LLM in the prompt to "respond with JSON matching this schema: ..." and parse manually. We've reserved this as a fallback; don't preemptively switch.
- **Gemini may not call tools eagerly.** Sometimes Flash answers without calling `fetch_url` and just hallucinates a brief. The fix is in the system prompt — make it more imperative: "You MUST call fetch_url. Do not answer without calling it."
- **First-line slide title detection is rough.** Decks with logos or imagery on slide 1 give garbage titles. Acceptable for v1 — we'll improve in evals if it matters.

---

## What we explicitly defer

- ❌ OCR for image-heavy PDFs. F11 or later if evals show pain.
- ❌ Headless browser scraping for JS-rendered sites. User can paste the deck instead.
- ❌ Multi-language detection. Assume English.
- ❌ Caching scrape results across runs. Premature; add when F11 deploys.
- ❌ Retries inside `fetch_url`. The tool returns an error; the LLM can decide to retry by calling again.

---

## Definition of done — the checklist

- [ ] `src/dealscout/domain/brief.py` exists with `StartupBrief`.
- [ ] `src/dealscout/adapters/scraper.py` exists; never raises; returns `ScrapeResult`.
- [ ] `src/dealscout/adapters/pdf.py` exists; never raises; returns `PdfResult`.
- [ ] `src/dealscout/tools/fetch_url.py` and `parse_pdf.py` exist and wrap their adapters.
- [ ] `prompts/triage_v1.md`, `url_intake_v1.md`, `pdf_intake_v1.md` all exist.
- [ ] `src/dealscout/prompts/__init__.py` has a working `load_prompt(name)`.
- [ ] All three agent factories (`build_triage_agent`, etc.) work.
- [ ] `src/dealscout/pipelines/intake.py` has `run_intake(raw_input) -> StartupBrief`.
- [ ] `uv run python -m dealscout.smoke` runs intake on Stripe's URL and prints a valid `StartupBrief`.
- [ ] Langfuse trace shows: Triage → handoff → URLIntake → fetch_url → final structured output.
- [ ] `uv run pytest tests/unit` passes (scraper + pdf adapter tests).
- [ ] `uv run pytest tests/integration -m integration` passes (URL pipeline test).
- [ ] PDF integration test passes IF a `tests/fixtures/sample_deck.pdf` exists; else skipped.
- [ ] Committed on branch `feature/01-intake`.

---

## Session plan

Roughly 3–4 hours. Use two sessions if needed.

1. **30 min** — Steps 1–2. `StartupBrief`, scraper adapter, `fetch_url` tool. Verify scraper works on a real URL via a quick `asyncio.run(scrape_url(...))`.
2. **30 min** — Step 3. PDF adapter + tool. Test on any pitch deck you can find. (If you don't have one: download YC's public Airbnb deck or similar.)
3. **30 min** — Steps 4–5. Prompts + loader. Read each prompt aloud — they should sound like job descriptions.
4. **45 min** — Step 6. Three agent factories. Verify each can be instantiated without errors (`python -c "from dealscout.agents.triage import build_triage_agent; build_triage_agent()"`).
5. **30 min** — Step 7. Pipeline + smoke test. Get it green. Open Langfuse and *look at the trace* — visualize the handoff.
6. **45 min** — Step 8–9. Tests. Get all green.
7. **15 min** — Commit, update `my_work/learnings.md` with what you learned about handoffs.

If at the end of session 1 the smoke test isn't green, stop and debug. Don't pile more code on broken foundations.

---

## What to add to `my_work/learnings.md` after F01

When F01 is done, write a short note answering these (in your own words):

1. *In one sentence, when do I use a handoff vs. an agent-as-tool?*
2. *Why did we make `fetch_url` return errors as data instead of raising?*
3. *Why is `StartupBrief` a Pydantic schema with required fields instead of a dict?*
4. *What's the difference between a tool's docstring and a system prompt? Who reads each?*

If you can't answer any of these without looking at the doc, that's the section to re-read. Don't skip this — these are the patterns you'll repeat in every AI project you build after this.
