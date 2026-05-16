# F04 — Founder Researcher

**Phase:** 3 — Other Specialists
**Depends on:** F02, F03 (third copy of the same pattern)
**Blocks:** F05 (Orchestrator wraps all three researchers)
**Estimated time:** 30 minutes

---

## What's new

Nothing structural. Same two tools (`search_web`, `fetch_url`), same free-form Markdown output, same `max_turns=10`. Only the prompt changes.

**The one thing to internalize:** searching for *people* is fuzzier than searching for *companies*. Founder queries return more noise — LinkedIn pages we can't read, people with the same name, outdated bios. The prompt has to lean harder on **honesty over completeness.**

---

## What this researcher does

Given a `StartupBrief`, produce notes on:

- **Founders** — names, current roles, brief bio
- **Prior companies** — what each founder did before
- **Notable signals** — exits, acquisitions, patents, well-known prior products
- **Domain fit** — does their background match the problem they're solving?
- **Open questions** — explicitly flag what you couldn't find

Same non-negotiables: must call `search_web` first, every claim cited, admit gaps.

---

## The one thing worth a 30-second think

**You will not get LinkedIn data directly.** LinkedIn aggressively blocks scrapers, and Gemini won't have current bios in training data. Realistic sources:

- Founder's company "About" page (the StartupBrief already has the website)
- Conference talks / podcast appearances
- Press articles announcing the funding round
- The founder's personal blog or Twitter/X

Tell the agent to *expect thin sources* and not invent details to fill the gap.

**Transferable principle:** *Calibrate the agent's expectations of the data world it lives in.* A research agent that thinks every founder has a Wikipedia page will hallucinate. One that knows founder data is fragmented will hedge.

---

## Build steps

### Step 1 — Prompt

Copy `prompts/market_researcher_v1.md` to `prompts/founder_researcher_v1.md`. Rewrite the body, keeping the non-negotiable rules verbatim. Add this paragraph somewhere prominent:

```
Founder data is typically thin and fragmented. You will rarely find a single
authoritative source. Cite what you find; explicitly mark what you couldn't
find. Do NOT pad with generic statements like "they have strong leadership
skills" — only include claims you can cite to a specific source.
```

That paragraph alone prevents 80% of founder-research hallucinations.

### Step 2 — Agent factory

Copy `src/dealscout/agents/market_researcher.py` to `founder_researcher.py`. Change name, prompt key. Done.

```python
def build_founder_researcher() -> Agent:
    return Agent(
        name="FounderResearcher",
        instructions=load_prompt("founder_researcher"),
        tools=[search_web, fetch_url],
        model=build_model(settings.researcher_model),
    )
```

### Step 3 — Pipeline function

Add to `src/dealscout/pipelines/research.py`:

```python
async def run_founder_research(brief: StartupBrief) -> str:
    researcher = build_founder_researcher()
    client = get_llm_client()
    prompt_input = f"""Please research the founders of this company.

Company: {brief.name}
One-liner: {brief.one_liner}
Source: {brief.source_ref}

Context from the source (may mention founders):
{brief.raw_text[:4000]}
"""
    result = await client.run(researcher, prompt_input, max_turns=10)
    return result.final_output
```

### Step 4 — Smoke test

Append to `smoke.py`:

```python
notes_founders = await run_founder_research(brief)
print(f"\n=== FOUNDER RESEARCH ===\n{notes_founders}")
```

### Step 5 — One eval case + one integration test

```yaml
# tests/eval/cases/stripe_founders.yaml
input:
  source_type: url
  source_ref: https://stripe.com
focus: founders
expected_dimensions:
  - "Names Patrick and John Collison"
  - "Mentions their prior company (Auctomatic)"
  - "Cites ≥ 2 sources"
  - "Has an 'Open questions' section if any data was thin"
```

```python
# tests/integration/test_founder_researcher.py
@pytest.mark.integration
@pytest.mark.asyncio
async def test_founder_researcher_names_founders():
    configure_provider()
    brief = await run_intake("https://stripe.com")
    notes = await run_founder_research(brief)
    assert "Collison" in notes  # known-good case
    assert "## References" in notes
```

---

## Quality gates

After the smoke test on Stripe:

- [ ] Output names actual founders (Patrick / John Collison)
- [ ] ≥ 2 cited sources
- [ ] Has an "Open questions" section (because founder data is always thin somewhere)
- [ ] Does NOT contain generic filler like "strong leadership team" or "experienced operators"

**The honesty test:** run it on a smaller startup where the founder is *not* a famous figure. The output should clearly say *what it couldn't find*, not paper over the gap. If it hallucinates a "Stanford CS '15" with no citation, the prompt isn't strong enough on gap-honesty. Fix and re-run.

---

## Definition of done

- [ ] `prompts/founder_researcher_v1.md` exists with the "data is thin" calibration paragraph
- [ ] `agents/founder_researcher.py` builds correctly
- [ ] `run_founder_research(brief)` callable
- [ ] Smoke test prints founder notes with citations
- [ ] Stripe integration test passes
- [ ] Honesty test passed on one small/obscure startup
- [ ] Committed on branch `feature/04-founder-researcher`

---

## After F04 — what to add to `my_work/learnings.md`

Two short answers:

1. *What's the difference between the three researchers' prompts? They all use the same tools — what makes each one specialize?*
2. *In which of the three was the LLM most likely to hallucinate? Why? What did the prompt do about it?*

You're now done with Phase 3. **You have three specialist agents.** Next up is F05 — the Orchestrator — where you'll finally see all three working together via agents-as-tools. That's the one worth slowing down for.
