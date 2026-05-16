# F02 — Company Researcher

**Phase:** 2 — First Specialist
**Depends on:** F00 (LLM adapter, Gemini), F01 (`StartupBrief` schema, `fetch_url` tool)
**Blocks:** F03, F04 (copy this pattern), F05 (Orchestrator wraps this)
**Estimated time:** 1 long session (3–4 hours focused work)

---

## Why this feature exists

F01 was extraction — pull structured fields out of one document. F02 is **research** — judgment about *what to look up* and *when you've seen enough*. This is the first agent in DealScout that does meaningful intellectual work, and it's the template for F03 and F04.

We build *one* researcher fully — prompt, tools, eval cases, clean trace — and then F03/F04 are 30 minutes of copy-and-adapt each. **Get this one right.** Every shortcut you take here multiplies by three.

---

## Mental model — read carefully

### What "the LLM browses the web" actually means

The Company Researcher does not "look things up." Gemini is a stateless function over a frozen training snapshot. **All current information enters via tools you control.**

When the Researcher needs to know what Stripe sells today:
1. Gemini emits a tool-call JSON: `{"name": "search_web", "arguments": {"query": "Stripe what does the company do 2025"}}`
2. Your Python code runs `search_web` against the Tavily API
3. The result goes back into Gemini's prompt
4. Gemini reads it and decides: "I have the product description; now I need traction data — call `search_web` again with a different query."

This loop is **ReAct** — Reason, Act, Observe, repeat. The Researcher decides what to do next based on what it found. You bound the loop (`max_turns=10`). When Gemini decides it has enough, it stops calling tools and writes a final answer.

If you're tempted to think "couldn't I just give the LLM the URL and let it browse?" — re-read the conversation we just had about why grounding features are black boxes. The principle: *agents should operate on data you fetched, not data they claim to have retrieved.*

### F02 architecture

```
                StartupBrief (from F01)
                         │
                         ▼
              ┌────────────────────────┐
              │  Company Researcher    │
              │  model: flash          │
              │  max_turns: 10         │
              │  output_type: None     │
              │     (free-form text)   │
              │                        │
              │  tools:                │
              │    - search_web        │
              │    - fetch_url         │
              └───────────┬────────────┘
                          │
                  research notes
                  (markdown, free-form)
```

Note: **no structured output for the researcher.** Output is free-form Markdown notes. The Orchestrator in F05 will synthesize, and the Memo Writer in F06 will structure. Separation of concerns: this agent does *research*, not formatting.

### What "good research notes" look like

A target you can refer to while building. Roughly 600–1200 words of Markdown like:

```
## Company: Stripe

### Product
Stripe provides payments infrastructure — APIs for accepting cards,
managing subscriptions, issuing cards, and embedded financial services.
Recently expanded into AI billing tools [1].

### Customers
- Mid-market and enterprise: Amazon, Salesforce, Shopify cited as customers [2]
- SMBs via Stripe Atlas and Stripe Climate
- Estimated millions of businesses globally [3]

### Traction signals
- $1.4T payment volume in 2024 per company blog [1]
- Reportedly profitable on adjusted operating income basis [4]
- IPO speculation ongoing; no confirmed filing as of search date

### Competitors mentioned in sources
Adyen, Square (Block), PayPal Braintree, Checkout.com

### Open questions for downstream agents
- Exact growth rate of new business signups vs. enterprise expansion
- Margin profile on financial services vs. core payments

[1] https://stripe.com/blog/...
[2] https://stripe.com/customers
[3] https://www.theinformation.com/...
[4] https://www.bloomberg.com/...
```

Two non-negotiable properties:
1. **Every claim cites a source URL.** Without citations, the Memo Writer can't pass through to a final memo. Citations are how we trust the agent.
2. **The agent admits what it didn't find.** "Open questions for downstream agents" is a deliberate hedge against hallucination. We'd rather see a gap than a guess.

---

## Key design decisions (the learning bit)

For each: **what**, **why**, **how it would burn you**, **transferable principle**.

### Decision 1 — Tavily for search, not Google/Bing/Brave

**What:** Search tool calls Tavily's API, which is purpose-built for LLM consumption.

**Why:** Tavily returns *cleaned snippets* — title, URL, short summary. Google/Bing return raw HTML you have to scrape. Brave is fine but slightly noisier. Tavily's responses are LLM-ready, meaning fewer prompt-engineering battles ("ignore the cookie banner," "skip the ad copy"). For a learning project where you want focus on agent design, not scraping, Tavily wins.

**How it would burn you:** Tavily's free tier is 1000 searches/month. If you blow that during F08 prompt iteration, you'll get rate-limited mid-experiment. Have a budget upgrade path planned (paid tier starts cheap). And don't let production traffic hit the free tier — that's the moment your demo dies on LinkedIn.

**Transferable principle:** *Match the data tool's output shape to the LLM's input shape.* Tools that hand the LLM raw HTML force the LLM to do parser work, wasting tokens and adding errors. Tools that return clean structure let the LLM focus on judgment.

### Decision 2 — Two tools (`search_web` + `fetch_url`), not one mega-tool

**What:** The Researcher gets two distinct tools, each with a narrow purpose.

**Why:** "Search" and "read this specific URL" are different operations. Combining them into one `web(query_or_url)` tool would force the LLM to disambiguate, and the docstring becomes a confusing essay. Two narrow tools = two clear docstrings = better LLM judgment about which to call.

**How it would burn you:** Imagine you have `web()` that does both. The LLM gets a search result URL and wants to read it. Does it call `web(url)`? The docstring has to explain both modes. Mistakes compound — sometimes the LLM searches when it meant to fetch.

**Transferable principle:** *Tool surfaces are like API surfaces. One verb per endpoint. Narrow tools beat clever tools.*

### Decision 3 — Free-form Markdown output, NOT structured

**What:** The Researcher's output type is plain string (Markdown). No Pydantic schema.

**Why:** Research is messy. Some companies have rich news, some have nothing. Forcing a fixed schema (`recent_news: list[str]`, `customers: list[str]`) means the LLM must invent fields when reality is empty, or leave them empty and degrade the schema. Free-form lets the Researcher write the right notes for the company in front of it. The Orchestrator and Memo Writer downstream will impose structure on the synthesis.

**How it would burn you:** Structure too early and the agent fights its own schema. You'll see weird hallucinations like `"customers": ["Customer 1", "Customer 2"]` because the schema demanded an array.

**Transferable principle:** *Impose structure at the right layer.* Extraction (F01) deserves a schema. Synthesis (F06) deserves a schema. Research in between is judgment work — let it breathe.

### Decision 4 — Force the first tool call in the system prompt

**What:** The prompt says: *"You MUST start by calling search_web. Do not answer from prior knowledge."*

**Why:** Gemini Flash is fast and confident. Without prompting otherwise, it'll often answer "Stripe is a payments company" from training data and skip searching entirely. That looks fine on Stripe — terrifying on an obscure Series-A startup the model has never heard of, where it'll confidently hallucinate.

**How it would burn you:** Silent hallucination. Your eval might pass on famous companies and *catastrophically fail* on the long-tail ones DealScout actually exists to analyze. You won't notice until F07 — and by then a lot of prompt iteration is wasted.

**Transferable principle:** *Don't trust the LLM to choose grounding voluntarily.* If retrieval is required for correctness, the prompt must make it non-negotiable. "Use tools when needed" is not enough — "you must call X first" is.

### Decision 5 — Citations are required, in the prompt

**What:** The prompt mandates `[N]` citation markers and a references list at the bottom. The Researcher gets explicit instructions to never make a claim without a citation.

**Why:** Citations are how we *audit* the Researcher's work in F07 evals. They're also what makes the final investment memo credible. An uncited memo is a creative writing exercise. A cited memo is a research artifact.

**How it would burn you:** Without explicit prompting, Gemini will write smooth prose, drop the citations, and produce something that *sounds* researched but isn't traceable. Half your "facts" will be regurgitated training data. Catching this in evals later is painful.

**Transferable principle:** *Verifiability must be designed in, not bolted on.* If you want to audit the agent later, you must constrain it now.

### Decision 6 — Tools cache nothing (yet)

**What:** Every call to `search_web` or `fetch_url` hits the network. No caching layer.

**Why:** During F02 you'll re-run the same queries dozens of times while iterating prompts. Caching would speed that up, but it also masks bugs (you fix the agent but get stale cached results, or vice versa). For now, eat the cost — Tavily's free tier covers it.

**How it would burn you:** When F08 (prompt iteration) hits and you're running 10 evals × 20 calls × 5 versions = 1000 searches, the free tier is gone. We'll add caching there. Don't preempt.

**Transferable principle:** *Add caching when iteration speed becomes painful, not before.* Premature caching is a debugging trap.

### Decision 7 — `max_turns=10`, not unbounded

**What:** Hard cap of 10 turns through the Runner loop.

**Why:** 10 turns ≈ 4 searches + 3 fetches + 2 reasoning steps + final answer. Enough for thorough research without runaway cost. If a researcher needs more, the prompt is wrong, not the budget.

**How it would burn you:** Unbounded loops + a slightly off prompt = $5 research runs. Easy to do, hard to spot until the bill arrives.

**Transferable principle:** *Every agent has a turn budget. Pick it deliberately; tune it from evals.* If you can't articulate why the number is what it is, it's wrong.

---

## Build order within this feature

### Step 1 — Tavily key + adapter

Get a free Tavily key at https://tavily.com. Add to `.env`:

```bash
TAVILY_API_KEY=tvly-...
```

Update `config.py`:

```python
# add to Settings class
tavily_api_key: str  # required
```

Build the adapter (no LLM concerns, just HTTP):

```python
# src/dealscout/adapters/search.py
from __future__ import annotations
from dataclasses import dataclass
import httpx
from dealscout.config import settings

@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str

@dataclass
class SearchResult:
    hits: list[SearchHit]
    error: str | None = None

async def search_tavily(query: str, max_results: int = 5,
                        timeout_seconds: float = 20.0) -> SearchResult:
    """Search the web via Tavily. Never raises."""
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.tavily_api_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",  # 'advanced' costs more credits
                    "include_answer": False,
                },
            )
            resp.raise_for_status()
    except httpx.HTTPError as e:
        return SearchResult(hits=[], error=str(e))

    data = resp.json()
    hits = [
        SearchHit(
            title=item.get("title", ""),
            url=item.get("url", ""),
            snippet=item.get("content", ""),
        )
        for item in data.get("results", [])
    ]
    return SearchResult(hits=hits)
```

**Acceptance:** `await search_tavily("Stripe payments")` returns non-empty hits. Calling with a bad key returns error.

### Step 2 — The `search_web` tool

```python
# src/dealscout/tools/search_web.py
from __future__ import annotations
from agents import function_tool
from dealscout.adapters.search import search_tavily

@function_tool
async def search_web(query: str, max_results: int = 5) -> dict:
    """Search the web for current information about companies, markets, or people.

    Use this when you need facts you don't already have from previous tool calls.
    Specifically use this for: company products, traction, customers, recent news,
    competitors mentioned in articles, market data.

    Do NOT use this to read a specific known URL — use fetch_url for that.

    Args:
        query: A focused search query, 3–8 words. Examples:
               "Stripe payment volume 2024"
               "Plaid competitors fintech API"
               "Anthropic funding round valuation"
        max_results: How many hits to return. Default 5. Use 3 for narrow
                     queries, 10 for broad market overviews.

    Returns:
        {
          "hits": [
            {"title": str, "url": str, "snippet": str},
            ...
          ],
          "error": str | None
        }
    """
    result = await search_tavily(query, max_results=max_results)
    return {
        "hits": [{"title": h.title, "url": h.url, "snippet": h.snippet}
                 for h in result.hits],
        "error": result.error,
    }
```

**Notice:** the docstring is the LLM's instruction manual for this tool. It includes when to use it, when *not* to use it, and example queries. This is prompt engineering at the tool level.

**Acceptance:** unit test with a mocked `search_tavily` confirms the tool returns the right dict shape.

### Step 3 — The Researcher prompt

```
prompts/company_researcher_v1.md
```

```markdown
# Role: Company Researcher (v1)
Purpose: Given a StartupBrief, research the company's product, customers, traction, and competitive context. Produce free-form Markdown research notes with citations.
Inputs: StartupBrief (name, one_liner, raw_text, headers_or_sections, source_ref)
Outputs: Markdown research notes, ~600-1200 words, every claim cited with [N] linking to a numbered references list at the bottom.
Last evaluated: TBD on eval set v1, pass rate: N/A (initial)

---

You are the Company Researcher for DealScout, an AI investment-memo assistant.

Your job: take a StartupBrief and produce research notes a venture analyst could use to write an investment memo. You research **the company itself** — not the market (that's another agent's job) and not the founders (also another agent).

## What to cover

For every company, produce sections on:
- **Product** — what they actually sell, who buys it, the core value proposition
- **Customers** — segments, named customers if findable, scale (rough)
- **Traction signals** — revenue, growth rate, funding, users — whatever is publicly known
- **Recent news** — major events in the last ~6 months
- **Competitors mentioned in sources** — list, don't analyze; the Market Researcher does the landscape
- **Open questions** — anything you couldn't find; downstream agents will know to address these

## Rules — non-negotiable

1. **You MUST start by calling search_web.** Do not answer from prior knowledge. Even if you "know" the company, current data may differ from training data.
2. **Every factual claim must cite a source.** Use `[N]` markers and a `## References` list at the end with the full URL. If you can't cite it, don't say it.
3. **Distinguish what you found from what you didn't.** If recent news is sparse, say so. If you couldn't find customer names, say so. *Admitting gaps is more valuable than papering over them.*
4. **You have ~10 tool calls.** Budget accordingly. Don't search the same thing twice with different wording — that's a sign you should fetch a specific URL instead.
5. **Use fetch_url to read specific pages** when search snippets aren't enough. For example: search returns the company's "About" page; fetch it to read the full product description.

## Tactics

- Start broad: `"<company name> what does <company name> do"`
- Then specific: `"<company name> customers"`, `"<company name> funding 2024"`, `"<company name> competitors"`
- If the StartupBrief raw_text is rich (lots of pitch deck content), use search to *verify* claims, not duplicate them
- Stop searching when each new query returns results you've already cited

## Output format

```markdown
## Company: <Name>

### Product
<paragraph or bullets, every fact cited>

### Customers
<paragraph or bullets, every fact cited>

### Traction signals
<paragraph or bullets, every fact cited>

### Recent news
<bullets with dates>

### Competitors mentioned in sources
<plain list>

### Open questions for downstream agents
<bullets — what you couldn't find or want flagged>

## References
[1] https://...
[2] https://...
```

Do not include any text outside this format. Do not add a preamble like "Here are the research notes:" — start directly with the `## Company:` heading.
```

**Acceptance:** the prompt is committed; reading it aloud, it sounds like a clear job description. The "non-negotiable" rules are unambiguous.

### Step 4 — Build the Researcher agent

```python
# src/dealscout/agents/company_researcher.py
from __future__ import annotations
from agents import Agent
from dealscout.adapters.llm import build_model
from dealscout.config import settings
from dealscout.prompts import load_prompt
from dealscout.tools.search_web import search_web
from dealscout.tools.fetch_url import fetch_url

def build_company_researcher() -> Agent:
    return Agent(
        name="CompanyResearcher",
        instructions=load_prompt("company_researcher"),
        tools=[search_web, fetch_url],
        model=build_model(settings.researcher_model),  # Flash by default
        # NOTE: no output_type — we want free-form Markdown
    )
```

**Acceptance:** `python -c "from dealscout.agents.company_researcher import build_company_researcher; print(build_company_researcher().name)"` prints `CompanyResearcher`.

### Step 5 — Pipeline entry point

```python
# src/dealscout/pipelines/research.py
from __future__ import annotations
from dealscout.adapters.llm import get_llm_client
from dealscout.agents.company_researcher import build_company_researcher
from dealscout.domain.brief import StartupBrief

async def run_company_research(brief: StartupBrief) -> str:
    """Run the Company Researcher on a StartupBrief. Returns Markdown notes.

    Caller is responsible for calling configure_provider() once first.
    """
    researcher = build_company_researcher()
    client = get_llm_client()

    # The Researcher gets the brief as its input message.
    # We hand it the *content* it needs to work on, formatted as text.
    prompt_input = f"""Please research this company.

Name: {brief.name}
One-liner: {brief.one_liner}
Source: {brief.source_ref}

Notes from the source page/deck:
{brief.raw_text[:4000]}

Section headers / slide titles for structure hints:
{', '.join(brief.headers_or_sections[:15])}
"""

    result = await client.run(researcher, prompt_input, max_turns=10)
    return result.final_output  # str of Markdown
```

**Acceptance:** running this against a known `StartupBrief` returns non-empty Markdown matching the expected format.

### Step 6 — Update the smoke test

```python
# src/dealscout/smoke.py — replace previous F01 version
"""Smoke test through F02: full intake + company research."""
from __future__ import annotations
import asyncio
from dealscout.adapters.llm import configure_provider
from dealscout.observability.tracing import init_tracing
from dealscout.pipelines.intake import run_intake
from dealscout.pipelines.research import run_company_research

async def main() -> None:
    configure_provider()
    init_tracing()

    brief = await run_intake("https://stripe.com")
    print(f"\n=== INTAKE ===")
    print(f"Name: {brief.name}")
    print(f"One-liner: {brief.one_liner}\n")

    notes = await run_company_research(brief)
    print(f"=== COMPANY RESEARCH ===\n")
    print(notes)

if __name__ == "__main__":
    asyncio.run(main())
```

**Acceptance:**
1. `uv run python -m dealscout.smoke` produces (a) a valid brief from intake, then (b) Markdown research notes with at least 3 citations.
2. Langfuse trace shows: intake handoff + multiple `search_web` / `fetch_url` calls in the research phase.
3. Cost per run < $0.05.

### Step 7 — Lightweight informal evals

Not full F07 yet — just create the directory and the first three cases so you start the discipline.

```
tests/eval/
├── README.md
└── cases/
    ├── stripe.yaml           # well-known, easy
    ├── modal_com.yaml        # mid-known startup
    └── obscure_ycombinator.yaml  # long-tail; pick any small recent YC company
```

```yaml
# tests/eval/cases/stripe.yaml
input:
  source_type: url
  source_ref: https://stripe.com
expected_dimensions:
  - "Mentions 'payments' as primary product"
  - "References at least 2 named customers OR explicit 'large customers' phrasing"
  - "Cites at least 4 sources"
  - "Lists at least 2 competitors"
  - "Has an 'Open questions' section that is non-empty"
notes: |
  Easy case. If Stripe research fails here, prompts are deeply broken.
```

```yaml
# tests/eval/cases/modal_com.yaml
input:
  source_type: url
  source_ref: https://modal.com
expected_dimensions:
  - "Mentions 'serverless' or 'compute infrastructure' as primary product"
  - "References developer / ML engineer customer segment"
  - "Cites at least 3 sources"
  - "Has an 'Open questions' section"
notes: |
  Mid-difficulty. Modal is well-documented but smaller than Stripe.
```

```yaml
# tests/eval/cases/obscure_ycombinator.yaml
input:
  source_type: url
  source_ref: https://<pick a small recent YC startup>
expected_dimensions:
  - "Acknowledges limited public information"
  - "Cites at least 2 sources (or explicitly says sources are thin)"
  - "Does NOT hallucinate customers / revenue without citation"
notes: |
  The honesty test. The Researcher should report what it can't find
  rather than make things up.
```

For now, just *run them by hand*. Read each output, compare against expected dimensions, write a one-line pass/fail. We'll automate scoring in F07.

**Acceptance:** all three cases run via the smoke test (just change the URL); for each, you've written down (in `my_work/learnings.md` or similar) whether it met the expected dimensions.

### Step 8 — Unit tests

```python
# tests/unit/test_search_adapter.py
import pytest
import respx
import httpx
from dealscout.adapters.search import search_tavily

@pytest.mark.asyncio
async def test_search_tavily_parses_results(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    sample = {"results": [
        {"title": "Stripe", "url": "https://stripe.com", "content": "Payments infra."},
    ]}
    with respx.mock:
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json=sample))
        result = await search_tavily("Stripe")
    assert len(result.hits) == 1
    assert result.hits[0].title == "Stripe"
    assert result.error is None

@pytest.mark.asyncio
async def test_search_tavily_returns_error_on_failure(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    with respx.mock:
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(500))
        result = await search_tavily("anything")
    assert result.error is not None
    assert result.hits == []
```

```python
# tests/integration/test_company_researcher.py
import pytest
from dealscout.adapters.llm import configure_provider
from dealscout.pipelines.intake import run_intake
from dealscout.pipelines.research import run_company_research

@pytest.mark.integration
@pytest.mark.asyncio
async def test_company_researcher_produces_notes_with_citations():
    configure_provider()
    brief = await run_intake("https://stripe.com")
    notes = await run_company_research(brief)
    assert "## References" in notes
    assert notes.count("[") >= 3  # at least 3 citation markers
    assert "Open questions" in notes
```

**Acceptance:**
- Unit tests pass fast, no network.
- Integration test passes against real Gemini + Tavily (costs <$0.05).

---

## Gemini-specific gotchas to flag for me

- **Tool laziness.** Gemini may answer from training data even with the "MUST start by calling search_web" instruction. If you see this in traces, escalate the prompt: capitalize, repeat, or add an explicit "if you skip the search step, your answer will be rejected" line. Yes, that works.
- **Tool call args may be dicts, not JSON strings.** If you see weird type errors in the tool decorator, that's why. The SDK should normalize but check if issues arise.
- **Parallel tool calls may run serially.** Gemini's OpenAI-compatible endpoint historically didn't support parallel tools well. If the Researcher tries to call `search_web` and `fetch_url` in the same turn, one may run after the other. Acceptable — F02 doesn't depend on parallelism.
- **Token limits on tool returns.** If a fetched page is huge, the result feeds back into the context window. We trim to 8000 chars in `scrape_url`. If Gemini complains about context length, that's the lever.
- **Citation drift.** Gemini may cite `[1]` in the body but forget to include `[1]` in references. Run the smoke test, eyeball the output. If it's broken, add to prompt: "Before finishing, verify every `[N]` in the body has a matching entry in `## References`."

---

## What we explicitly defer

- ❌ Caching search/fetch results. F08 (prompt iteration) when free tier gets tight.
- ❌ Date-aware queries ("recent news" → searches for last 6 months specifically). v2 if evals show stale results.
- ❌ Quality scoring of sources (peer-reviewed > blog > Reddit). v2.
- ❌ Multilingual research. English only.
- ❌ Tool call timeouts at the per-tool level beyond the 30s default. Add when something hangs.

---

## Definition of done — the checklist

- [ ] `TAVILY_API_KEY` in `.env`; `tavily_api_key` field in `Settings`.
- [ ] `src/dealscout/adapters/search.py` exists; `search_tavily` never raises.
- [ ] `src/dealscout/tools/search_web.py` exists with a clear docstring.
- [ ] `prompts/company_researcher_v1.md` committed.
- [ ] `src/dealscout/agents/company_researcher.py` builds an Agent with two tools.
- [ ] `src/dealscout/pipelines/research.py` has `run_company_research(brief) -> str`.
- [ ] `uv run python -m dealscout.smoke` runs intake + research, prints valid Markdown with ≥3 citations.
- [ ] Langfuse trace shows: intake (with handoff) → research phase with multiple tool calls visible.
- [ ] Per-run cost < $0.05 (check Gemini dashboard or estimate via tokens in trace).
- [ ] `tests/eval/cases/` has the three YAML eval cases.
- [ ] You've run the smoke test against all three cases and noted pass/fail in `my_work/`.
- [ ] `uv run pytest tests/unit` passes.
- [ ] `uv run pytest tests/integration -m integration` passes.
- [ ] Committed on branch `feature/02-company-researcher`.

---

## Session plan

Roughly 3–4 hours.

1. **20 min** — Step 1. Tavily key, adapter, verify with one real query.
2. **15 min** — Step 2. `search_web` tool.
3. **30 min** — Step 3. Researcher prompt. *Read it aloud after writing.* If you wouldn't hire a researcher who got this brief, fix it.
4. **15 min** — Steps 4–5. Agent + pipeline.
5. **30 min** — Step 6. Smoke test. *Look at the Langfuse trace.* You should see the agent's reasoning between tool calls — this is the moment ReAct stops being abstract.
6. **45 min** — Step 7. Run all three eval cases by hand. Read the output of each *carefully*. Write down what's good and what's broken. Resist the urge to fix prompts now — capture observations for F08.
7. **30 min** — Step 8. Tests.
8. **15 min** — Commit, update `my_work/learnings.md`.

If the agent doesn't cite sources after the smoke test, *stop and fix the prompt before continuing*. Uncited research is the failure mode that breaks everything downstream.

---

## What to add to `my_work/learnings.md` after F02

Write down — in your own words, no Claude help:

1. *Why does the Researcher need a tool to access the web instead of "knowing things from training"? (One paragraph.)*
2. *What's the difference between a tool's docstring and a system prompt? Which one teaches the LLM to **pick** a tool vs. how to **use** the tool?*
3. *Why is the output free-form Markdown instead of a Pydantic schema? Where in the pipeline does structure get imposed?*
4. *Read your three eval case outputs side-by-side. What's the biggest quality gap between the Stripe case and the obscure-YC case? What does that tell you about where prompts will need to improve?*

The fourth question is the most important one. It's the seed of F07 and F08.
