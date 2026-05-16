# F03 — Market Researcher

**Phase:** 3 — Other Specialists
**Depends on:** F02 (this is a parallel copy of that pattern)
**Blocks:** F05 (Orchestrator wraps all three researchers)
**Estimated time:** 30–60 minutes (copy-adapt, no new architecture)

---

## What's actually new vs. F02

This is structurally identical to F02. **Don't over-think it.** What changes:

1. **Different prompt** — researches *the market*, not the company.
2. **Same two tools** — `search_web` and `fetch_url` (no new tool surface).
3. **Slightly different output format** — still free-form Markdown, but section headings are about market, not company.

That's the whole feature. Everything else is copy-paste from F02.

---

## What this researcher does

Given a `StartupBrief`, produce Markdown notes on:

- **Market segment** — what industry/category the startup competes in
- **TAM / market size** — rough estimate with sources (don't fabricate precise numbers)
- **Trends** — growth direction, tailwinds, headwinds (last ~12 months)
- **Competitor landscape** — known players with brief one-line positioning each
- **Buyer dynamics** — who pays, why now, switching costs
- **Open questions for downstream agents**

Same rules as F02: must call `search_web` first, every claim cited, admit gaps explicitly.

---

## One genuinely new concept: Fermi estimation in a prompt

For TAM specifically, we want the LLM to reason about market size *visibly* when sources are thin — show the assumptions, not just a number.

In the prompt: instead of "estimate the TAM," say "if no published TAM exists, derive one with explicit assumptions (e.g., 'There are ~X businesses in this segment, average ACV ~$Y, so TAM ≈ $X·Y'). Cite source for each assumption."

That single instruction prevents the most annoying TAM hallucination: "$5B market" with no derivation.

**Transferable principle:** *make reasoning visible in the output, not just final answers.* This is the same idea as showing your work in a math test — and the same reason it improves accuracy.

---

## Build steps (do them fast)

### Step 1 — Prompt

Copy `prompts/company_researcher_v1.md` to `prompts/market_researcher_v1.md`. Edit:

- Change the role header and Purpose line
- Rewrite the "What to cover" sections to be the six above
- Replace the example output skeleton with market-flavored sections
- Add the Fermi instruction to the TAM section
- Keep the non-negotiable rules (must-call-search-first, must-cite) verbatim

### Step 2 — Agent factory

Copy `src/dealscout/agents/company_researcher.py` to `market_researcher.py`. Change:

- Agent `name="MarketResearcher"`
- `load_prompt("market_researcher")`
- Same tools, same model setting

```python
def build_market_researcher() -> Agent:
    return Agent(
        name="MarketResearcher",
        instructions=load_prompt("market_researcher"),
        tools=[search_web, fetch_url],
        model=build_model(settings.researcher_model),
    )
```

### Step 3 — Pipeline function

In `src/dealscout/pipelines/research.py`, add a sibling function:

```python
async def run_market_research(brief: StartupBrief) -> str:
    researcher = build_market_researcher()
    client = get_llm_client()

    prompt_input = f"""Please research the market for this company.

Company: {brief.name}
One-liner: {brief.one_liner}
Source: {brief.source_ref}

Context from the source:
{brief.raw_text[:4000]}
"""
    result = await client.run(researcher, prompt_input, max_turns=10)
    return result.final_output
```

Note: the prompt explicitly says "research the MARKET" — small phrasing, big effect on agent focus.

### Step 4 — Smoke test

Append to `src/dealscout/smoke.py`:

```python
notes_market = await run_market_research(brief)
print(f"\n=== MARKET RESEARCH ===\n{notes_market}")
```

Run it. Verify the trace shows fresh `search_web` calls scoped to market queries (not the same queries F02 made).

### Step 5 — One eval case + one integration test

Add `tests/eval/cases/stripe_market.yaml`:

```yaml
input:
  source_type: url
  source_ref: https://stripe.com
focus: market
expected_dimensions:
  - "Names the payments / fintech industry"
  - "Provides TAM with at least one cited assumption"
  - "Lists at least 3 competitors with brief positioning"
  - "Cites ≥ 3 sources"
```

```python
# tests/integration/test_market_researcher.py
@pytest.mark.integration
@pytest.mark.asyncio
async def test_market_researcher_includes_competitors():
    configure_provider()
    brief = await run_intake("https://stripe.com")
    notes = await run_market_research(brief)
    assert "## References" in notes
    assert notes.count("[") >= 3
```

---

## Quality gate before declaring done

Run the smoke test against Stripe. The Market output must:

- [ ] Have a section that names the industry (payments, fintech)
- [ ] Include at least one TAM-related claim with an explicit assumption
- [ ] List competitors *different* from those in the F02 Company notes? *(see below)*
- [ ] Cite ≥3 sources
- [ ] Have an "Open questions" section

**About that "different competitors" check:** F02's Company Researcher lists competitors *mentioned in sources*. F03's Market Researcher should produce a *broader landscape* — these should overlap but not be identical. If they're identical, F03's prompt isn't pulling its weight (it's just re-doing F02). Tweak the prompt to emphasize "landscape" vs. "mentioned in articles."

---

## Definition of done

- [ ] `prompts/market_researcher_v1.md` exists, sounds like a market analyst's brief
- [ ] `src/dealscout/agents/market_researcher.py` builds correctly
- [ ] `run_market_research(brief)` callable from the pipeline
- [ ] Smoke test prints market notes with ≥3 citations
- [ ] One eval case + one integration test
- [ ] Committed on branch `feature/03-market-researcher`

---

## After F03 — what to add to `my_work/learnings.md`

Two short answers:

1. *What's the input shape an agent-as-tool will see when F05 wraps these researchers? Why does it work that way?*
2. *Looking at the F02 Company notes and F03 Market notes side-by-side for the same company: where do they overlap and where do they genuinely differ? If they overlap too much, what does that tell you about the prompts?*

F04 next — Founder Researcher — will be even shorter. Same pattern, third time.
