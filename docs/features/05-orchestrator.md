# F05 — Orchestrator (Investment Lead)

**Phase:** 4 — Orchestrator
**Depends on:** F02, F03, F04 (all three researchers callable independently)
**Blocks:** F06 (Memo Writer; the Orchestrator will call it as the last tool)
**Estimated time:** 1 long session (3–4 hours) — slower than F03/F04 because the concepts matter

---

## Why this feature exists

For four features you've been building agents that work *in isolation*. F05 is the first one where multiple agents collaborate to do something none of them could do alone. The Orchestrator — let's call it the "Investment Lead" — receives a `StartupBrief` from intake and is responsible for:

1. Deciding **what** to research
2. Deciding **which specialists** to delegate to
3. Deciding **when** the research is sufficient
4. **Synthesizing** the three researchers' free-form Markdown notes into a coherent picture

That last bullet is the one that justifies the existence of an Orchestrator at all. If we didn't synthesize, we'd just be running three researchers in sequence and dumping their output — which is *not* a system, it's a script. The Orchestrator's job is to *think across* the three notes.

**Critical insight for this whole feature:** the Orchestrator does NOT write the memo. Memo writing is F06's job. F05 produces *synthesized research* — still free-form Markdown notes, but coherent across all three angles. F06's structured Memo Writer will take that synthesis and produce the final `InvestmentMemo`.

Keeping these jobs separate is one of the most important design decisions you'll make. We'll talk about why in Decision 1 below.

---

## Mental model — read this slowly

This section is longer than usual. Read carefully; the rest of F05 hinges on these ideas.

### The shape: orchestrator-workers

You've seen this pattern in the AI Agent Patterns doc. Here it is in DealScout-specific form:

```
            StartupBrief (from F01)
                     │
                     ▼
           ┌─────────────────────┐
           │   Orchestrator       │      Model: gemini-2.5-pro
           │   (Investment Lead)  │      Tools: 3 agents-as-tools
           │                      │      max_turns: 15
           └────────┬────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
    agent-as-tool   │           │
        │           │           │
        ▼           ▼           ▼
  ┌─────────┐ ┌──────────┐ ┌──────────┐
  │ Company │ │  Market  │ │ Founder  │
  │Researcher│ │Researcher│ │Researcher│
  └─────────┘ └──────────┘ └──────────┘
        │           │           │
        └─────┬─────┴─────┬─────┘
              │           │
              ▼           ▼
          (their Markdown notes flow back as tool results)
                          │
                          ▼
                Orchestrator synthesizes
                (writes a unified research dossier)
                          │
                          ▼
                ResearchDossier (Markdown)
                          │
                          ▼
                (F06 will turn this into the memo)
```

### Why agents-as-tools, not handoffs

We already settled this conceptually in F01. Now you'll feel it concretely:

**Handoffs would be wrong here** because if the Orchestrator handed off to the Company Researcher, it would *cease to exist* in the conversation. The Company Researcher would return notes, but there'd be no one left to call the Market Researcher next, and certainly no one to synthesize all three.

**Agents-as-tools is right** because the Orchestrator stays in control. It calls Company Researcher (gets notes back as a tool result), then calls Market Researcher (gets notes back), then Founder Researcher (gets notes back), then *thinks about all three together* and produces synthesis.

This is the exact distinction we covered in F01's mental model. F05 is where that distinction becomes load-bearing.

### What the Orchestrator's LLM actually sees

Crucial mental model. When you do this:

```python
company_tool = company_researcher.as_tool(
    tool_name="research_company",
    tool_description="Research the company's product, customers, and traction. Returns Markdown notes."
)
```

…the Orchestrator's LLM (Gemini 2.5 Pro) sees `research_company` as just another function in its tool menu. It looks identical (to the LLM) to a plain `@function_tool` like `search_web` would. The Orchestrator's LLM doesn't know — and doesn't need to know — that calling `research_company` triggers a full agent run with its own ReAct loop, its own Tavily calls, its own ~10 turns.

This is the **abstraction boundary** of the whole project. From the Orchestrator's perspective, it has three powerful "research" functions. From the system's perspective, those functions are entire subsystems. This is why the agents-as-tools pattern is so powerful: it composes.

### The string-in/string-out reality, revisited

You already worked through this in F03 when you asked "why does run_market_research take a StartupBrief?" Now let's see how it plays out at scale.

When the Orchestrator's LLM calls `research_company`, here's what flows:

1. **Orchestrator LLM emits** a tool call: `research_company(input="Research Stripe Inc, focusing on payment volume and recent product launches. Founded 2010, payments infrastructure.")`
2. **SDK routes** that string into the Company Researcher agent as its input message
3. **Company Researcher runs** its full ReAct loop (search_web, fetch_url, reasoning, ~5–10 turns)
4. **Company Researcher's final output** (Markdown notes) becomes the tool result
5. **Orchestrator LLM reads** the Markdown notes in its next turn and decides what to do next

So the boundary between Orchestrator and Company Researcher is *natural language*. The Orchestrator passes a focused research brief as a string. The Company Researcher returns Markdown as a string. Structured data lives in your Python layer (the pipeline code that formats inputs and saves outputs).

**Write this down if you haven't already:** *Agents talk to each other in natural language. Python code is what wires structured data around those calls.*

### The synthesis question

This is the design problem at the heart of F05. After the Orchestrator has all three Markdown notes, what does it produce?

**Bad option:** Concatenate the three notes verbatim. ("# Company\n...\n\n# Market\n...\n\n# Founders\n...") This is what most amateur multi-agent systems do, and it's why they feel like "scripts dressed up as systems." There's no thinking across the three.

**Good option:** Write a unified dossier that *integrates* findings — flags contradictions ("the company's marketing claims 100 customers but research found only 5 named ones"), connects dots ("founders' OSS work in distributed systems explains the engineering depth in the product"), and signals confidence levels ("traction signals are robust; market sizing is rough").

The synthesis is what justifies the Orchestrator's existence. **If your finished F05 produces output that looks like three notes pasted together, the Orchestrator's prompt is wrong.**

---

## Key design decisions (the learning bit)

For each: **what**, **why**, **how it would burn you**, **transferable principle**.

### Decision 1 — The Orchestrator synthesizes; it does NOT write the memo

**What:** F05's output is free-form Markdown — a *synthesized research dossier*. The structured `InvestmentMemo` Pydantic object is F06's job.

**Why:** Two reasons. **(a)** Separation of concerns: synthesis is judgment work (cross-references, contradictions, confidence levels) that benefits from free-form output. Memo writing is structure-imposing work that benefits from a schema. Different jobs, different agents, different prompts. **(b)** Iteration speed: if both jobs lived in one agent, every prompt tweak would risk breaking either synthesis or formatting. Splitting them lets you iterate one without breaking the other.

**How it would burn you:** Imagine you collapse the two and have one Orchestrator that outputs structured `InvestmentMemo` directly. Now you're tuning a prompt that has to do both *think across three research streams* AND *fit thinking into 14 specific Pydantic fields*. Every time you improve schema adherence, synthesis quality degrades. Every time you improve synthesis, fields get sparse. You'll end up doing massive prompt-engineering on a prompt that does too much.

**Transferable principle:** *One responsibility per agent.* The same principle as Single Responsibility from OOP, applied to LLM prompts. When you find yourself writing a system prompt with two distinct goals, split it.

### Decision 2 — Use the bigger model (gemini-2.5-pro)

**What:** Orchestrator uses `settings.orchestrator_model` (Gemini 2.5 Pro by default), not Flash.

**Why:** Three reasons stack. **(a)** Long-context synthesis: the Orchestrator's prompt grows to ~10K tokens (system + three Markdown notes + reasoning). Flash gets fuzzy at that length; Pro stays sharp. **(b)** Cross-document reasoning: connecting dots between the three notes requires the kind of multi-step reasoning Pro is meaningfully better at. **(c)** This is the *one* call where quality matters more than cost — researchers can be Flash, the synthesizer is the brain.

**How it would burn you:** Running everything on Flash to save cost is tempting (~10x cheaper) but the synthesis quality drops noticeably. You'll see weak connection-making, occasional missed contradictions, and lazy "the company has strengths and weaknesses" non-synthesis. Your F07 evals will catch it but you'll have wasted iteration cycles.

**Transferable principle:** *Match model tier to task complexity, not uniformly.* In production systems, almost all calls are "small fast model"; the 5–10% that are reasoning hubs use the frontier model. This is a 10x cost lever.

### Decision 3 — `max_turns=15`, not 10

**What:** Orchestrator gets a higher turn budget than researchers (10) because it's coordinating *across* them.

**Why:** The Orchestrator's turn count is: ~3 researcher calls + reasoning between calls + final synthesis. Each researcher call is one turn from the Orchestrator's perspective (even though it triggers ~10 internal turns inside the researcher — those are hidden from the Orchestrator's counter). 15 leaves room for one extra researcher call if needed (e.g., "I need follow-up market data") plus margin.

**How it would burn you:** Setting `max_turns=10` will *sometimes* be fine and *sometimes* truncate the Orchestrator mid-synthesis with no final output. Nondeterministic failures are the worst kind — you'll spend hours wondering why one run fails when an "identical" one succeeded.

**Transferable principle:** *Turn budgets are not generic defaults — they're a function of the agent's specific workflow.* Each agent's budget should reflect its expected workflow plus margin. Bake the calculation into the doc; don't make future-you wonder.

### Decision 4 — Tool descriptions are prompts for the Orchestrator

**What:** When wrapping each researcher with `.as_tool()`, the `tool_description` is written carefully — it tells the Orchestrator's LLM *when* to call which researcher.

**Why:** The Orchestrator's LLM picks tools based on these descriptions. Vague descriptions → wrong-tool calls (Orchestrator asks Company Researcher about founders). Sharp descriptions → confident, correct routing. Treat each `tool_description` as a mini system prompt.

**How it would burn you:** Default descriptions like "Research the company" vs. "Research the market" sound fine to a human but the Orchestrator's LLM will sometimes get confused — it'll ask the Company Researcher about market sizing, then have nothing left for the actual Company Researcher's job. Bad descriptions cost you tool-selection accuracy and waste budget.

**Transferable principle:** *Tool descriptions ARE prompts.* This is the same principle from F02 (tool docstrings). At the Orchestrator level, your tool descriptions ARE the system prompt — they're what the LLM uses to decide its actions.

### Decision 5 — Synthesis is opinionated, not exhaustive

**What:** The Orchestrator's prompt instructs it to produce a *structured, opinionated* synthesis — not a comprehensive regurgitation. It explicitly highlights contradictions, confidence levels, and the strongest single signal.

**Why:** A "comprehensive" synthesis of three notes is just longer notes. The value of the Orchestrator is *judgment* — what's the most important thing here, what's questionable, what's the bigger picture. Without an opinionated prompt, you get bland summaries; with one, you get analysis.

**How it would burn you:** The single most common failure mode of multi-agent systems is **summary-soup output**. Every section ends with "...has strengths and weaknesses, with both opportunities and challenges." Reads polished, says nothing. Aggressively prompting for opinions and explicit confidence levels prevents this.

**Transferable principle:** *Prompts must demand opinions, not allow them.* LLMs default to hedged, balanced, agree-with-everyone output. If you want sharp thinking, you must explicitly require it — and demand evidence for any strong claim.

### Decision 6 — Parallel tool calls if Gemini supports them, else sequential

**What:** The three researchers are *independent* — there's no data dependency between them. They *could* run in parallel. We'll let the Orchestrator's LLM decide, but accept that Gemini's OpenAI-compatible endpoint may serialize them.

**Why:** Latency. Three sequential researchers at ~30s each = ~90s. Parallel = ~30s. For our 3-minute end-to-end budget, parallel matters. But Gemini's OpenAI-compatible endpoint historically hasn't supported parallel tool calls reliably, so we don't *require* it.

**How it would burn you:** If you write code that assumes parallel execution, you'll get weird behavior when Gemini runs them sequentially. Conversely, if you *force* sequential (by having the prompt say "call them one at a time"), you give up the win when a future SDK update enables parallel. Best move: let the LLM decide, observe in traces, accept whatever happens for v1.

**Transferable principle:** *Don't take dependencies on undocumented or version-dependent behaviors.* If parallel tools matter for production, you'd implement them explicitly in pipeline code (via `asyncio.gather`) rather than relying on the LLM. For a learning project, accept Gemini's behavior and note the limitation.

### Decision 7 — Pipeline-level orchestration is still your code, not the agent

**What:** The Python code that calls `Runner.run(orchestrator, ...)` is in `pipelines/analyze.py`. That code — not the Orchestrator agent — is responsible for: running intake first, passing the brief to the Orchestrator, handling errors, persisting traces.

**Why:** The Orchestrator agent's job is *intelligent coordination of research*. Process orchestration (run intake, then run orchestrator, then handle errors) is plain Python control flow. You don't want an LLM deciding "should I run intake again?" — that's wasted budget on a decision that's deterministic.

**How it would burn you:** People often try to put the entire pipeline inside one mega-agent that "does everything." It works for demos and fails for production. Failures become impossible to debug because the agent is making decisions you'd want to be deterministic (retry policy, error handling, intake ordering).

**Transferable principle:** *Let the LLM make decisions only where the decision requires intelligence.* Deterministic flow control belongs in your code. Workflow orchestration belongs in code. Agent orchestration (which specialist to call, when to stop researching) belongs in the LLM. Mixing them is a mistake.

---

## What the synthesized dossier looks like

A concrete target — refer to this while building. Roughly 1500–2500 words of Markdown, structured like:

```markdown
# Research Synthesis: <Company Name>

## At-a-glance
<3–4 sentences that integrate company, market, and founder snapshots.>

## What's strongest in this research
<2–3 bullets — the most credible findings across all three angles, with citations.>

## What's most concerning
<2–3 bullets — the most credible risks across all three angles, with citations.>

## Contradictions and tensions
<Explicit list of places where the three notes don't align. Empty if none — say so explicitly. "No major contradictions found" is acceptable and useful.>

## Confidence assessment
- Company data: <strong / moderate / thin>, because <reason>
- Market data: <strong / moderate / thin>, because <reason>
- Founder data: <strong / moderate / thin>, because <reason>

## Integrated narrative
<3–5 paragraphs that connect company + market + founder findings into a single story. This is the heart of the synthesis — the part that justifies the Orchestrator's existence.>

## Open questions
<Aggregated from all three researchers, deduplicated, with which researcher flagged each.>

## Source map
<All citations from all three researchers, deduplicated by URL.>
```

The "Integrated narrative" section is the litmus test. If it could be written without all three researchers' inputs — if it could come from any single one — the synthesis isn't doing its job.

---

## Build order within this feature

### Step 1 — Define the dossier shape (in your head, not as code)

Before writing the Orchestrator prompt, decide what the dossier looks like. The template above is a starting point — adjust based on what you actually want for F06's input. The dossier is the *contract* between F05 and F06.

Free-form Markdown is the right output format here (same reasoning as F02 — synthesis is judgment work). But the *structure* of the Markdown should be predictable so F06's Memo Writer can rely on it.

### Step 2 — The Orchestrator system prompt

```
prompts/orchestrator_v1.md
```

This prompt does more work than any prompt you've written so far. Sketch:

```markdown
# Role: Investment Lead / Orchestrator (v1)
Purpose: Coordinate three specialist researchers (company, market, founders) and synthesize their findings into an opinionated research dossier.
Inputs: A StartupBrief formatted as a prompt.
Outputs: A Markdown dossier (see template).
Last evaluated: TBD on eval set v1, pass rate: N/A (initial)

---

You are the Investment Lead at DealScout. You don't do research yourself — you direct three specialist research agents and synthesize what they find.

## Your tools

You have three research specialists. Each is an entire research agent under
the hood — calling one of these triggers a full investigation that takes
~30 seconds and produces Markdown research notes:

- research_company: investigates product, customers, traction, recent news
- research_market: investigates market size, competitive landscape, why now
- research_founders: investigates founders' backgrounds and prior work

You also have one final tool:
- write_dossier: USE THIS LAST. Pass it your final synthesized dossier as the
  full Markdown text. This signals that research is complete.

## Workflow

1. Read the StartupBrief carefully.
2. Call all three research specialists. You may call them in any order or
   in parallel — there are no data dependencies between them. Give each
   specialist a *focused* research brief — not the full StartupBrief
   verbatim, but a tailored prompt explaining what you want them to
   investigate.
3. After receiving all three notes, read them carefully. Look for:
   - Contradictions between notes
   - Reinforcing evidence across notes
   - Critical gaps any researcher flagged
4. If a critical gap is exposed, you MAY do one follow-up call to the
   relevant researcher with a more focused question. Do this at most ONCE —
   you have a 15-turn budget.
5. Write the final dossier (template below) and submit it via write_dossier.

## Non-negotiable rules

- **You MUST call all three researchers.** Even if you "know" the company,
  the researchers have access to live data that you don't.
- **The dossier MUST be opinionated.** Do not write "the company has
  strengths and weaknesses." Identify *the strongest single signal* and
  *the most concerning single signal* with citations.
- **You MUST flag confidence levels.** Mark each major section (company /
  market / founders) as strong, moderate, or thin based on evidence
  quantity and quality.
- **You MUST flag contradictions.** If notes disagree on a fact, name it
  and say which source is more credible.
- **Preserve citations** from the researchers' notes. The final dossier
  must include a source map.

## Dossier template

[paste the template from "What the synthesized dossier looks like" above]

## Tactical guidance

- When briefing a specialist, focus their attention: "Research Stripe
  specifically on payment volume trends in the last 12 months and any
  product launches in 2024+. The startup is Series H-stage with publicly
  reported $1.4T volume — focus on recent inflection signals."
- Don't paraphrase the StartupBrief at length when briefing specialists —
  they don't need history, they need a research focus.
- If a researcher returns thin notes (e.g., few citations, lots of open
  questions), note this in the dossier's confidence assessment rather than
  re-running the researcher. Re-running wastes budget for diminishing returns.

Begin by reading the StartupBrief and calling your researchers.
```

**Read this prompt aloud.** If it doesn't sound like a brief you'd give a smart but inexperienced analyst, fix it before continuing. Prompts that don't read well don't work well.

### Step 3 — Wrap the three researchers as tools

```python
# src/dealscout/agents/orchestrator.py
from __future__ import annotations
from agents import Agent
from dealscout.adapters.llm import build_model
from dealscout.config import settings
from dealscout.prompts import load_prompt

# Import the researcher factories
from dealscout.agents.company_researcher import build_company_researcher
from dealscout.agents.market_researcher import build_market_researcher
from dealscout.agents.founder_researcher import build_founder_researcher

# Import the write_dossier tool (next step)
from dealscout.tools.write_dossier import write_dossier


def build_orchestrator() -> Agent:
    company_researcher = build_company_researcher()
    market_researcher = build_market_researcher()
    founder_researcher = build_founder_researcher()

    # Each as_tool() call wraps a full agent as a single callable tool.
    # The tool_description is what the Orchestrator's LLM uses to decide
    # when to call which researcher — write these like API docs.
    company_tool = company_researcher.as_tool(
        tool_name="research_company",
        tool_description=(
            "Investigate the company's product, customers, traction signals, "
            "and recent news. Returns Markdown research notes with citations. "
            "Use this when you need to understand WHAT the company does and "
            "HOW they're doing. Do NOT use this for market sizing or founder "
            "background — separate tools exist for those."
        ),
    )

    market_tool = market_researcher.as_tool(
        tool_name="research_market",
        tool_description=(
            "Investigate the market segment, TAM, competitive landscape, and "
            "why-now tailwinds. Returns Markdown notes with citations. Use "
            "this when you need the broader category context. Do NOT use "
            "this to research the specific company or its founders."
        ),
    )

    founder_tool = founder_researcher.as_tool(
        tool_name="research_founders",
        tool_description=(
            "Investigate the founders' backgrounds, prior companies, and "
            "domain fit for the problem they're solving. Returns Markdown "
            "notes with citations. Expect thin sources — founder data is "
            "fragmented. Use this when you need to assess team credibility."
        ),
    )

    return Agent(
        name="InvestmentLead",
        instructions=load_prompt("orchestrator"),
        tools=[company_tool, market_tool, founder_tool, write_dossier],
        model=build_model(settings.orchestrator_model),  # Pro, not Flash
        # max_turns is set when we call Runner.run, not on the agent
    )
```

### Step 4 — The `write_dossier` tool (the "I'm done" signal)

The Orchestrator needs a way to signal "research is complete; here's my synthesis." We could use `output_type=str` and rely on the final output, but a dedicated tool makes the trace cleaner and the stopping condition explicit.

```python
# src/dealscout/tools/write_dossier.py
from __future__ import annotations
from agents import function_tool

@function_tool
def write_dossier(dossier_markdown: str) -> str:
    """Submit the final synthesized research dossier.

    Call this LAST, after all three research specialists have returned
    their notes and you have synthesized findings. Pass the full Markdown
    dossier as a single string.

    The dossier should follow the template in your system prompt:
    at-a-glance, what's strongest, what's most concerning, contradictions,
    confidence assessment, integrated narrative, open questions, source map.

    Args:
        dossier_markdown: The complete synthesized dossier in Markdown.

    Returns:
        Confirmation that the dossier was received. After this call, your
        work is done.
    """
    # This is a passthrough — the dossier is just returned so we can
    # extract it from the trace. In a more complex setup we'd persist it
    # here. For F05, the pipeline code grabs it from the run result.
    return "Dossier received. Research complete."
```

Note this is `@function_tool` (regular tool), not an agent-as-tool. It's a plain function that lets the Orchestrator say "I'm done." Why have a tool for this at all? Two reasons:

1. **Cleaner trace.** Without it, the dossier appears in the "final assistant message" which is harder to find programmatically. With it, the dossier is a tool call argument — easy to extract.
2. **Explicit stopping condition.** The presence of `write_dossier` in the tools list tells the Orchestrator's LLM exactly how to signal completion. Without this, the LLM might keep researching past the point of diminishing returns.

### Step 5 — Pipeline function

```python
# src/dealscout/pipelines/analyze.py
from __future__ import annotations
from typing import NamedTuple
from dealscout.adapters.llm import get_llm_client
from dealscout.agents.orchestrator import build_orchestrator
from dealscout.domain.brief import StartupBrief


class AnalysisResult(NamedTuple):
    """The result of running the full F05 pipeline."""
    dossier_markdown: str
    brief: StartupBrief


async def run_analysis(brief: StartupBrief) -> AnalysisResult:
    """Run intake-to-dossier: invoke the Orchestrator, which delegates to
    the three researchers and produces a synthesized dossier.

    Caller is responsible for calling configure_provider() once first.
    Caller is also responsible for running intake to produce the brief.
    """
    orchestrator = build_orchestrator()
    client = get_llm_client()

    # Brief the Orchestrator with the StartupBrief content.
    # Same string-in pattern you've seen since F02.
    prompt_input = f"""You are analyzing the following startup. Coordinate your
research specialists and produce a synthesized dossier.

Name: {brief.name}
One-liner: {brief.one_liner}
Source type: {brief.source_type}
Source: {brief.source_ref}

Notes from the source page or deck:
{brief.raw_text[:4000]}

Section headers / slide titles (structure hints):
{', '.join(brief.headers_or_sections[:15])}
"""

    result = await client.run(orchestrator, prompt_input, max_turns=15)

    # Extract the dossier from the trace. The Orchestrator submits it via
    # the write_dossier tool — find that tool call's arguments.
    dossier = _extract_dossier_from_result(result)
    return AnalysisResult(dossier_markdown=dossier, brief=brief)


def _extract_dossier_from_result(result) -> str:
    """Pull the dossier out of the run result.

    The Orchestrator calls write_dossier as its final action. We can
    extract the dossier_markdown argument from that tool call. The exact
    API for inspecting run results depends on the SDK version — verify
    against the installed Agents SDK.
    """
    # Most common shape: result.new_items contains tool-call records
    # with the arguments accessible. Verify against your SDK version.
    for item in reversed(result.new_items):
        if hasattr(item, "tool_name") and item.tool_name == "write_dossier":
            return item.arguments.get("dossier_markdown", "")
    # Fallback: the final_output may contain the dossier text directly
    if isinstance(result.final_output, str):
        return result.final_output
    raise RuntimeError("Could not extract dossier from run result")
```

**Gotcha for Claude:** The exact way to inspect `RunResult` items varies between SDK versions. **Verify this against the installed Agents SDK** before settling on the extractor. Run `result.new_items` for a smoke run and print the structure — that'll show you the right way to find the `write_dossier` tool call.

### Step 6 — Update the smoke test

```python
# src/dealscout/smoke.py
"""Smoke test through F05: intake + full orchestrated research."""
from __future__ import annotations
import asyncio
import time
from dealscout.adapters.llm import configure_provider
from dealscout.observability.tracing import init_tracing
from dealscout.pipelines.intake import run_intake
from dealscout.pipelines.analyze import run_analysis


async def main() -> None:
    configure_provider()
    init_tracing()

    started = time.time()
    brief = await run_intake("https://stripe.com")
    intake_elapsed = time.time() - started
    print(f"\n=== INTAKE ({intake_elapsed:.1f}s) ===")
    print(f"Name: {brief.name}")
    print(f"One-liner: {brief.one_liner}\n")

    started_analysis = time.time()
    result = await run_analysis(brief)
    analysis_elapsed = time.time() - started_analysis
    total = time.time() - started

    print(f"=== SYNTHESIZED DOSSIER ({analysis_elapsed:.1f}s) ===\n")
    print(result.dossier_markdown)
    print(f"\n=== TOTAL: {total:.1f}s ===")


if __name__ == "__main__":
    asyncio.run(main())
```

**Acceptance:**
1. Runs end-to-end without errors.
2. Total time under 4 minutes (target: under 3).
3. The dossier has all template sections (at-a-glance, strongest, most concerning, contradictions, confidence, integrated narrative, open questions, source map).
4. The Langfuse trace shows a clear hierarchy: Orchestrator → three researcher sub-agents (each with their own Tavily calls) → write_dossier.
5. **The integrated narrative section actually integrates** — not just three subsections pasted together.

### Step 7 — One eval case + integration test

```yaml
# tests/eval/cases/stripe_dossier.yaml
input:
  source_type: url
  source_ref: https://stripe.com
focus: full-dossier
expected_dimensions:
  - "Has all template sections (at-a-glance, strongest, concerning, contradictions, confidence, narrative, open questions, sources)"
  - "Integrated narrative connects company/market/founder findings — not just three subsections"
  - "Confidence assessment names specific reasons (not vague 'strong')"
  - "Contradictions section is non-empty OR explicitly states 'no major contradictions'"
  - "Source map contains ≥ 8 unique URLs (~3 from each researcher)"
notes: |
  The integrated narrative is the litmus test. If it could be written
  without all three researchers' inputs, the Orchestrator isn't synthesizing.
```

```python
# tests/integration/test_orchestrator.py
import pytest
from dealscout.adapters.llm import configure_provider
from dealscout.pipelines.intake import run_intake
from dealscout.pipelines.analyze import run_analysis

@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_produces_full_dossier():
    configure_provider()
    brief = await run_intake("https://stripe.com")
    result = await run_analysis(brief)
    d = result.dossier_markdown

    # Structural checks
    assert "At-a-glance" in d or "at-a-glance" in d.lower()
    assert "strongest" in d.lower()
    assert "concerning" in d.lower() or "concerns" in d.lower()
    assert "confidence" in d.lower()
    assert "open questions" in d.lower()

    # Quality proxies
    assert d.count("[") >= 8  # at least 8 citation markers
    assert len(d) > 2000  # substantive synthesis, not a stub
```

---

## Quality gate before declaring done

After the smoke test, read the dossier carefully and check:

- [ ] All template sections present
- [ ] Confidence assessment names *specific reasons*, not just "strong/moderate/thin" alone
- [ ] Contradictions section is honest — either named contradictions or explicit "no major contradictions found"
- [ ] **The integrated narrative section actually integrates** (re-read it; does it require all three researchers' inputs?)
- [ ] Citations from all three researchers preserved in the source map
- [ ] Total time under 4 minutes
- [ ] Cost under $0.30 (Pro is more expensive than Flash; budget grows accordingly)
- [ ] Trace in Langfuse shows: Orchestrator → 3 researcher sub-trees → write_dossier call

**If the integrated narrative is weak**, the Orchestrator prompt is the lever. Iterate before moving on.

---

## Gemini-specific gotchas to flag for me

- **Pro is meaningfully slower than Flash.** Each Orchestrator turn may take 8–15 seconds. The total wall-clock budget reflects this.
- **Pro is also rate-limited differently.** Free tier may hit quota fast. If you blow it during the smoke test, you can switch the Orchestrator to Flash temporarily — synthesis quality will drop but the pipeline will work.
- **Parallel tool calls.** Gemini's OpenAI-compatible endpoint may serialize the three researcher calls. Accept this; don't fight it. If you see them running sequentially in the trace, that's expected.
- **Long context.** The Orchestrator's prompt grows to ~10K tokens after three researcher results come in. Pro handles this; Flash gets fuzzy. Confirm Pro is actually being used by checking the trace.
- **Tool name confusion.** Gemini sometimes calls tools by similar names (e.g., it'll output `"research_company_info"` instead of `"research_company"`). The SDK should reject this; if you see "tool not found" errors, that's why. Tighten the prompt's tool-name references.

---

## What we explicitly defer

- ❌ **Real parallel execution via asyncio.gather.** If we wanted guaranteed parallelism, we'd run researchers from Python and skip the agent-as-tool pattern for them. Not needed for v1 — accept Gemini's behavior.
- ❌ **Adaptive turn budget.** The Orchestrator gets 15 turns regardless of task complexity. Smarter budgeting is a future optimization.
- ❌ **Researcher retry on thin results.** If a researcher returns weak notes, the Orchestrator currently can do one follow-up call but won't trigger a full re-run. Acceptable for v1.
- ❌ **Cross-run learning.** Each analysis is independent. Adding memory across runs is a different project.
- ❌ **Detailed cost tracking per call.** F07 will surface costs in the eval scorecard.

---

## Definition of done — the checklist

- [ ] `prompts/orchestrator_v1.md` exists, reads like a brief to a smart analyst
- [ ] `src/dealscout/tools/write_dossier.py` exists
- [ ] `src/dealscout/agents/orchestrator.py` exists; wraps three researchers and includes `write_dossier`
- [ ] `src/dealscout/pipelines/analyze.py` has `run_analysis(brief) -> AnalysisResult`
- [ ] Smoke test runs end-to-end on Stripe, prints a dossier with all template sections
- [ ] **Integrated narrative section meaningfully integrates** (this is the subjective gate — re-read it critically)
- [ ] Langfuse trace shows Orchestrator coordinating three sub-trees + write_dossier
- [ ] Total wall-clock time under 4 minutes
- [ ] Cost per run under $0.30
- [ ] Stripe eval case + integration test pass
- [ ] Committed on branch `feature/05-orchestrator`

---

## Session plan

Roughly 3–4 hours. **Don't try to one-shot this.**

1. **40 min** — Re-read the Mental Model section. Then write the Orchestrator prompt (Step 2). *Read it aloud before continuing.* If it doesn't sound like a brief to a smart analyst, fix it.
2. **30 min** — Steps 3–4. Wrap researchers as tools; build `write_dossier`. Verify the Orchestrator agent factory instantiates without errors.
3. **30 min** — Step 5. Pipeline function. **Verify how to inspect the SDK's RunResult** by running a quick test and printing `result.new_items` structure before finalizing the dossier extractor.
4. **45 min** — Step 6. Smoke test on Stripe. **Look at the Langfuse trace carefully** — you should see the hierarchical structure clearly. If you don't, traces aren't propagating from sub-agents correctly.
5. **30 min** — Read the dossier *critically*. Check the integrated narrative. If it's weak, iterate the prompt and re-run.
6. **30 min** — Step 7. Eval case + integration test.
7. **15 min** — Commit, update `my_work/learnings.md`.

If the integrated narrative is bad after one prompt iteration, **stop and ping me before iterating further** — there's a class of prompt-engineering moves specific to synthesis tasks that's easier to walk through together than to debug solo.

---

## What to add to `my_work/learnings.md` after F05

These are the questions that, if you can answer them in your own words, mean you've internalized the Orchestrator pattern:

1. *Why is the Orchestrator an agent and not a Python function? What does it do that a function couldn't?*
2. *The Orchestrator separates "synthesis" from "memo writing" (deferred to F06). Why? What would go wrong if they were one agent?*
3. *The three researchers are wrapped as tools, but `write_dossier` is also a tool — and it's a plain @function_tool, not an agent-as-tool. Why this asymmetry?*
4. *Looking at your Langfuse trace: what do you see in the hierarchy that you couldn't have seen with print() statements? Why does this matter for production?*

The fourth question is the most important. F05 is where the value of observability becomes obvious — you literally can't debug this system without traces.

---

## After F05

You've now built a multi-agent system. **Take a moment.** This is non-trivial. Most "AI engineers" listed on LinkedIn cannot build what you've just built.

Next is F06 — the Memo Writer. That's where you finally produce the polished investment memo PDF you saw in the sample. Schema-driven, structured output, mechanical rendering. Compared to F05, F06 is engineering rather than agent design — a different kind of work.

Then F07 (evals) is where this project becomes a CV piece instead of just a project. Plan accordingly.
