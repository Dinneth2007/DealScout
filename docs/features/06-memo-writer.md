# F06 — Memo Writer + PDF Renderer

**Phase:** 5 — Memo
**Depends on:** F05 (produces the dossier this feature consumes)
**Blocks:** F07 (eval harness scores the memo's structured fields)
**Estimated time:** 1 long session or 2 short sessions (3–4 hours)

---

## Why this feature exists

F05 produces a synthesized research dossier — well-structured Markdown, opinionated, with citations. F06 turns that dossier into the **actual deliverable**: a polished PDF investment memo with a Pass / Track / Meet recommendation.

Two distinct concerns live in this feature:

1. **Memo Writer (an agent):** read the F05 dossier and produce a structured `InvestmentMemo` Pydantic object — every field validated, recommendation explicit, citations preserved.
2. **Renderer (plain Python):** take the `InvestmentMemo` and render it to PDF + Markdown using ReportLab. Deterministic. No LLM.

Keeping these two responsibilities separate is the single most important design decision in F06. The agent does *structure-imposing judgment work*. The renderer does *mechanical transformation*. Neither does the other's job.

---

## Mental model

### The two-stage shape

```
            F05 dossier (Markdown string)
                       │
                       ▼
            ┌──────────────────────┐
            │  Memo Writer agent   │     output_type=InvestmentMemo
            │  model: deepseek-chat │     no tools needed
            │  max_turns: 5         │     (it just transforms)
            └──────────┬───────────┘
                       │
                       ▼
                InvestmentMemo (Pydantic)
                       │
                       ▼
            ┌──────────────────────┐
            │   Renderer (Python)  │     plain function, no LLM
            └──────────┬───────────┘
                       │
                ┌──────┴──────┐
                ▼             ▼
            memo.pdf      memo.md
```

### Why the Memo Writer has no tools

This is intentional and worth absorbing. The Memo Writer doesn't need search, doesn't need fetch, doesn't need anything external. Its entire input — the synthesized dossier — is already in its prompt. Its only job is *fit dossier into schema*.

Agents without tools are still useful. They're transformation agents — they read one shape of text and produce another. F06's Memo Writer is the cleanest example you'll build in this project.

### Why the renderer is not an agent

Three reasons stack:

1. **Determinism.** Same `InvestmentMemo` input → identical PDF every time. The artifact users see should not be nondeterministic.
2. **Cost & latency.** LLM rendering would add ~$0.03 and ~30s per memo for zero quality gain.
3. **Auditability.** When something looks wrong in the PDF, you debug Python — not a prompt. Stack traces are a thousand times better than "the LLM kind of did something weird this run."

### The pipeline shape (Decision A you already made)

`pipelines/analyze.py` becomes the end-to-end driver:

```python
async def run_full_analysis(input_str: str) -> FullAnalysisResult:
    brief = await run_intake(input_str)              # F01
    dossier = await run_analysis(brief)              # F05 — synthesis
    memo = await run_memo_writer(dossier)            # F06 — structure
    pdf_path, md_path = render_memo(memo)            # F06 — render
    return FullAnalysisResult(brief, dossier, memo, pdf_path, md_path)
```

Plain Python control flow. The LLM makes decisions inside each agent; the *order* of agents is deterministic code.

---

## Key design decisions (the learning bit)

### Decision 1 — The InvestmentMemo schema mirrors the sample PDF's sections

**What:** Derive Pydantic field names directly from the sample memo's visual sections. If the sample has an "Executive summary" section, the schema has `executive_summary: str`. If it has "Three strengths," the schema has `strengths: list[str] = Field(..., min_length=3, max_length=3)`.

**Why:** The schema *is* the contract between Memo Writer and Renderer. Every field maps to a section. No field exists without a corresponding render block; no render block reads data that isn't a field. This 1:1 mapping is what makes the system debuggable.

**How it would burn you:** Loose schema (e.g., `body: dict[str, Any]`) feels flexible but every render bug becomes a discovery problem. "Why is the Strengths section empty?" turns into hours of LLM-output forensics. Tight schema fails fast at the agent boundary, not silently at render time.

**Transferable principle:** *Your data schemas should be your visual layout's mirror image.* The closer the mapping, the easier the debugging.

### Decision 2 — The recommendation is a structured field with mandatory rationale

**What:** The schema has two recommendation fields:
```python
recommendation: Literal["PASS", "TRACK", "MEET"]
recommendation_rationale: str = Field(..., min_length=50, max_length=400)
```

**Why:** The recommendation is the most important single thing in the memo. Making it a `Literal` means the agent *cannot* return "Strong Meet" or "Pass with reservations" or "Maybe Track" — three values, that's it. The mandatory rationale prevents the LLM from issuing a verdict without explaining itself. The length bounds prevent both one-word rationales ("Solid.") and rambling.

**How it would burn you:** A free-form `recommendation: str` field invites variation: "PASS," "Pass," "I would pass," "Recommendation: PASS." Now your F07 eval scoring is brittle — you'd be writing regex against LLM output. Structured choice fields make the agent commit and make downstream code simple.

**Transferable principle:** *For high-stakes outputs, force the LLM to commit to one option from a closed set, and demand an explicit reason.* This is what turns LLM output from "interpretation required" to "actionable data."

### Decision 3 — Citations preserved by reference, not regenerated

**What:** The schema includes `references: list[Reference]` where each `Reference` has `index: int` (the `[N]` marker) and `description: str` (e.g., "Crunchbase — Modal Labs funding page"). The Memo Writer must preserve the indices and URLs from the dossier's source map.

**Why:** The dossier already has citations and a source map. The Memo Writer's job is to fit content into the schema, not to re-cite. Asking the LLM to "find citations for these claims" would invite hallucination of sources it didn't actually see.

**How it would burn you:** If the prompt says "ensure each claim is cited," the LLM will sometimes invent citations to satisfy the rule. With "preserve citations from the dossier," the LLM either carries the original `[N]` markers correctly or drops them — both visible, both auditable.

**Transferable principle:** *Don't ask the LLM to do work that was already done upstream.* Each agent should add value, not duplicate effort. Re-doing upstream work is the most common way agent pipelines hallucinate.

### Decision 4 — Strict list lengths via Pydantic Field constraints

**What:** Strengths and concerns are exactly 3 each (`min_length=3, max_length=3`). Open questions is bounded `min_length=2, max_length=6`. Recent news bounded `min_length=0, max_length=8`.

**Why:** The sample memo's design has three strengths and three concerns *as a deliberate visual constraint*. Five strengths and one concern would be a layout problem and an analytical signal that the agent didn't really think about concerns. Enforcing it at the schema level makes the agent commit to its top three of each.

**How it would burn you:** Without constraints, the LLM will sometimes produce "Three strengths: 1, 2, 3, also..." (four strengths). Or "concerns: ['Various challenges exist']" (one vague concern). Pydantic validation catches both at the agent boundary.

**Transferable principle:** *Schema constraints are prompts by other means.* Every `min_length`, `max_length`, `Literal`, `Field(pattern=...)` is a constraint the LLM must respect. You can prompt for it *and* enforce it — both, not either.

### Decision 5 — The renderer is dumb and the schema does the thinking

**What:** The renderer is ~200 lines of "for each field, draw the corresponding section." No conditionals on content quality. No fallbacks for missing data. If the schema validates, the renderer runs.

**Why:** Every conditional in the renderer is a place future-you will get confused. ("Why is the founders section missing? Oh, the renderer has an `if not memo.founders_detail` branch from three months ago.") Better: validate at the schema, then render straight through.

**How it would burn you:** Defensive renderers hide schema bugs. You'll spend hours debugging "why doesn't this field appear" only to find the renderer silently skipped it because the data shape was *almost* right.

**Transferable principle:** *Validate at the boundary, trust within.* Same principle as F01's `StartupBrief`, now at the F06 layer. The schema is the seam.

### Decision 6 — Markdown output alongside PDF, same render path

**What:** The renderer produces both `memo.md` (Markdown) and `memo.pdf` from the same `InvestmentMemo`. Different output adapters, same data source.

**Why:** Markdown is the universal format. It renders in GitHub, in Notion, in Slack, in your own dev workflow. PDF is for sharing. Both should exist. Producing both from the same Pydantic object guarantees they don't drift.

**How it would burn you:** If you skip Markdown now, you'll later want it for F07 evals (rubric scoring is easier against text than PDF). And you'll want it for the LinkedIn post screenshot. Build the dual output now; it's 30 extra minutes.

**Transferable principle:** *If a piece of data should exist in multiple formats, render them all from the same source object.* Never generate format B by parsing format A.

---

## Build order

### Step 1 — The InvestmentMemo schema

```
src/dealscout/domain/memo.py
```

Reference the sample PDF (`DealScout_Sample_Memo_Modal.pdf`) section by section as you write this. Every visual block → one field.

```python
# src/dealscout/domain/memo.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field

class FounderProfile(BaseModel):
    name: str
    role: str = Field(..., description="e.g., 'CEO, co-founder'")
    background: str = Field(..., min_length=40, description="Brief bio with citations as [N] markers")

class NewsItem(BaseModel):
    date_or_quarter: str = Field(..., description="e.g., '2025-Q1' or '2024-10'")
    description: str = Field(..., description="One-line news description with citation")

class Reference(BaseModel):
    index: int = Field(..., ge=1, description="The [N] marker number")
    description: str = Field(..., description="Source description: 'Crunchbase — Modal funding page'")

class InvestmentMemo(BaseModel):
    """The final structured investment memo. Mirrors the sample PDF's sections 1:1."""

    # ── At-a-glance card ──────────────────────────────────────
    company_name: str
    one_liner: str = Field(..., max_length=200,
        description="One-sentence company description, ideally the company's own.")
    founded: str = Field(..., description="e.g., '2021, San Francisco'")
    stage: str = Field(..., description="e.g., 'Series A (2024) [1]'")
    founders_summary: str = Field(..., description="Comma-separated founder names")
    investors: str = Field(..., description="Lead and notable investors, with citations")
    segment: str = Field(..., description="Market segment, e.g., 'AI infrastructure'")
    team_size: str = Field(..., description="e.g., '~40 (per LinkedIn) [4]' or 'Not disclosed'")

    # ── Recommendation ────────────────────────────────────────
    recommendation: Literal["PASS", "TRACK", "MEET"]
    recommendation_rationale: str = Field(..., min_length=50, max_length=400,
        description="One-paragraph reasoning for the recommendation.")

    # ── Body ──────────────────────────────────────────────────
    executive_summary: str = Field(..., min_length=400, max_length=1500,
        description="Two-paragraph summary integrating company + market + founders.")

    strengths: list[str] = Field(..., min_length=3, max_length=3,
        description="Exactly three top strengths, each with citations.")
    concerns: list[str] = Field(..., min_length=3, max_length=3,
        description="Exactly three top concerns, each with citations or reasoning.")
    open_questions: list[str] = Field(..., min_length=2, max_length=6,
        description="Critical questions the research couldn't answer.")

    product: str = Field(..., min_length=200, description="Product/technology section.")
    customers: str = Field(..., min_length=100, description="Customer profile and named accounts.")
    traction_signals: list[str] = Field(..., min_length=2, max_length=6,
        description="Bullet points of concrete traction evidence with citations.")

    market_segment: str = Field(..., min_length=150,
        description="What market this competes in; TAM with assumptions if applicable.")
    competitive_landscape: str = Field(..., min_length=200,
        description="Named competitors with brief positioning each.")
    why_now: str = Field(..., min_length=150,
        description="Tailwinds making this the right moment.")

    founders_detail: list[FounderProfile] = Field(..., min_length=1, max_length=5)
    founder_market_fit: str = Field(..., min_length=80,
        description="Assessment of whether founders match the problem.")

    recent_news: list[NewsItem] = Field(default_factory=list, max_length=8)

    bull_case: str = Field(..., min_length=100, max_length=600)
    bear_case: str = Field(..., min_length=100, max_length=600)
    mind_changers: str = Field(..., min_length=80,
        description="What evidence would change the recommendation.")

    references: list[Reference] = Field(..., min_length=4,
        description="The source map, indexed.")

    # ── Metadata ──────────────────────────────────────────────
    cost_usd_estimate: float | None = Field(None, ge=0,
        description="Optional: estimated USD cost for this run; surfaced in the footer.")
    latency_seconds: float | None = Field(None, ge=0,
        description="Optional: wall-clock latency; surfaced in the footer.")
```

**Acceptance:** `python -c "from dealscout.domain.memo import InvestmentMemo; print(InvestmentMemo.model_json_schema())"` prints a valid schema with all the constraints.

### Step 2 — The Memo Writer prompt

```
prompts/memo_writer_v1.md
```

```markdown
# Role: Memo Writer (v1)
Purpose: Convert a synthesized research dossier (free-form Markdown) into a strictly-structured InvestmentMemo (Pydantic JSON).
Inputs: A research dossier string from the Orchestrator.
Outputs: An InvestmentMemo object matching the schema.
Last evaluated: TBD on eval set v1, pass rate: N/A (initial)

---

You are the Memo Writer for DealScout.

Your job is mechanical and demanding: read the synthesized research dossier
and produce a strictly-structured investment memo. You are NOT a researcher.
You do not fetch new information. You do not invent citations. You transform.

## Rules — non-negotiable

1. **Every field of the InvestmentMemo schema must be populated.** If the
   dossier doesn't provide enough information for a required field, write
   "Not disclosed in public sources" or similar honest placeholder — but
   do NOT leave fields empty or fabricate content.

2. **Citations must be preserved verbatim.** The dossier contains `[N]`
   markers and a source map. Carry these markers through into the memo's
   body fields. The `references` field must reproduce the source map.

3. **The recommendation must be one of PASS, TRACK, MEET.** Pick the one
   that best reflects the dossier's overall signal:
   - PASS: serious red flags, weak founders, or fundamentally wrong market
   - TRACK: interesting but too early or too uncertain to engage now
   - MEET: strong signal across dimensions, worth a partner meeting

4. **The recommendation_rationale must reference specific signals from the
   dossier** — not generic praise or hedging. 50–400 chars. One paragraph.

5. **Strengths and concerns are exactly THREE each.** Not two. Not five.
   Pick the most important three. The schema will reject other counts.

6. **No editorialization beyond what the dossier supports.** Your output
   reflects the dossier's findings, not your independent opinion about
   the company. If the dossier admits gaps, your memo admits gaps.

## Field-by-field guidance

- `company_name`, `one_liner`: from the dossier's at-a-glance section.
- `founded`, `stage`, `founders_summary`, `investors`, `segment`,
  `team_size`: from at-a-glance, with citations preserved.
- `executive_summary`: 2 paragraphs integrating company + market + founder
  findings. NOT a generic paragraph about the company.
- `strengths` / `concerns`: derived from the dossier's "what's strongest"
  and "what's most concerning" sections. Three bullets each, each with
  citations.
- `open_questions`: copy from the dossier's open questions section.
- `product`, `customers`, `traction_signals`: from the dossier's company-
  research material.
- `market_segment`, `competitive_landscape`, `why_now`: from market.
- `founders_detail`: one FounderProfile per named founder. Each background
  must be ≥40 chars; "Background not publicly documented" is acceptable.
- `founder_market_fit`: synthesize the dossier's assessment.
- `recent_news`: list items from the dossier's recent news. May be empty.
- `bull_case`, `bear_case`: short scenarios; the dossier's
  integrated narrative is your raw material.
- `mind_changers`: what evidence would shift the recommendation.
- `references`: enumerate every `[N]` in the dossier's source map.

## Output

Produce a single InvestmentMemo JSON object that matches the schema. The
SDK will validate it. If validation fails, you will be re-prompted with
the validation errors and must correct the structure.

Do not include any text outside the JSON object. Do not add a preamble.
```

**Acceptance:** the prompt is committed; reading aloud, it sounds like a clear job description for a mechanical-but-demanding role.

### Step 3 — The Memo Writer agent

```python
# src/dealscout/agents/memo_writer.py
from __future__ import annotations
from agents import Agent
from dealscout.adapters.llm import build_model
from dealscout.config import settings
from dealscout.domain.memo import InvestmentMemo
from dealscout.prompts import load_prompt

def build_memo_writer() -> Agent:
    return Agent(
        name="MemoWriter",
        instructions=load_prompt("memo_writer"),
        model=build_model(settings.default_model),
        output_type=InvestmentMemo,   # The SDK enforces the schema
        # No tools — pure transformation
    )
```

**Gotcha for Claude:** verify that DeepSeek's structured-output path through the SDK actually works for a schema this complex. If you see schema-validation failures on the first smoke run, the fallback (already prepared from F01's notes) is to drop `output_type` and instruct the LLM to produce JSON in the prompt, then parse with `InvestmentMemo.model_validate_json()` in the pipeline.

### Step 4 — The pipeline function

```python
# src/dealscout/pipelines/memo.py
from __future__ import annotations
from dealscout.adapters.llm import get_llm_client
from dealscout.agents.memo_writer import build_memo_writer
from dealscout.domain.memo import InvestmentMemo

async def run_memo_writer(dossier_markdown: str) -> InvestmentMemo:
    """Convert a synthesized dossier into a structured InvestmentMemo.

    Caller is responsible for calling configure_provider() once first.
    """
    writer = build_memo_writer()
    client = get_llm_client()

    prompt_input = f"""Convert the following research dossier into an InvestmentMemo.

Preserve all citations. Recommendation must reflect the dossier's overall signal.

=== DOSSIER ===
{dossier_markdown}
"""
    result = await client.run(writer, prompt_input, max_turns=5)

    if not isinstance(result.final_output, InvestmentMemo):
        raise RuntimeError(
            f"Memo Writer did not produce an InvestmentMemo; got {type(result.final_output)}"
        )
    return result.final_output
```

**Acceptance:** running this against the F05 dossier (the one you already generated synthetically) returns a valid `InvestmentMemo`.

### Step 5 — The renderer

Two files:

```
src/dealscout/rendering/
├── __init__.py
├── markdown.py     # InvestmentMemo → Markdown string
└── pdf.py          # InvestmentMemo → PDF file (ReportLab)
```

For PDF, **reference the sample memo's code** (`build_sample_memo.py` from earlier). The structure is already there — palette, page chrome, sections. Adapt it to read from an `InvestmentMemo` instance rather than hardcoded content.

Pseudocode for `pdf.py`:

```python
def render_pdf(memo: InvestmentMemo, output_path: str) -> str:
    """Render an InvestmentMemo to PDF at output_path. Returns the path."""
    # Same setup as build_sample_memo.py:
    #   - SimpleDocTemplate, LETTER, margins
    #   - page_chrome callback
    #   - Build a list of flowables

    story = []
    story.append(_title_block(memo))           # company_name, one_liner
    story.append(_at_a_glance_card(memo))      # 4x2 grid
    story.append(_recommendation_banner(memo)) # colored pill + rationale
    story.append(_executive_summary(memo))
    story.append(_what_stands_out_callouts(memo))  # 3-column strengths/concerns/questions
    story.append(_product_section(memo))
    story.append(_customers_section(memo))
    story.append(_traction_signals_bullets(memo))
    story.append(_market_section(memo))
    story.append(_founders_section(memo))
    story.append(_recent_news_bullets(memo))
    story.append(_investment_thesis(memo))     # bull, bear, mind_changers
    story.append(_references_list(memo))
    story.append(_footer_disclaimer(memo))     # uses cost_usd_estimate & latency

    doc.build(story, onFirstPage=page_chrome, onLaterPages=page_chrome)
    return output_path
```

For `markdown.py`, simpler — just format each field with headers. Roughly:

```python
def render_markdown(memo: InvestmentMemo) -> str:
    lines = [
        f"# {memo.company_name}",
        f"*{memo.one_liner}*",
        "",
        "## At a glance",
        f"- **Founded:** {memo.founded}",
        # ...
        "",
        f"## Recommendation: {memo.recommendation}",
        memo.recommendation_rationale,
        # ...
    ]
    return "\n".join(lines)
```

**Acceptance:**
- `render_pdf(memo, "/tmp/test.pdf")` produces a PDF that opens.
- `render_markdown(memo)` returns a non-empty string with all section headers.
- The PDF looks recognizably like the sample memo (same palette, same structure) — not pixel-perfect, but the same shape.

### Step 6 — Wire it into the full pipeline

Update `pipelines/analyze.py` to add the F06 stage:

```python
# src/dealscout/pipelines/analyze.py
from pathlib import Path
from typing import NamedTuple
from dealscout.domain.brief import StartupBrief
from dealscout.domain.memo import InvestmentMemo
from dealscout.pipelines.intake import run_intake
from dealscout.pipelines.memo import run_memo_writer
from dealscout.rendering.pdf import render_pdf
from dealscout.rendering.markdown import render_markdown

class FullAnalysisResult(NamedTuple):
    brief: StartupBrief
    dossier_markdown: str
    memo: InvestmentMemo
    pdf_path: str
    markdown_path: str

async def run_full_analysis(input_str: str, output_dir: str = "./output") -> FullAnalysisResult:
    """End-to-end: input string → memo PDF + Markdown."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    brief = await run_intake(input_str)
    analysis = await run_analysis(brief)
    memo = await run_memo_writer(analysis.dossier_markdown)

    # Render outputs
    safe_name = memo.company_name.lower().replace(" ", "_").replace("/", "_")
    pdf_path = f"{output_dir}/memo_{safe_name}.pdf"
    md_path = f"{output_dir}/memo_{safe_name}.md"

    render_pdf(memo, pdf_path)
    with open(md_path, "w") as f:
        f.write(render_markdown(memo))

    return FullAnalysisResult(brief, analysis.dossier_markdown, memo, pdf_path, md_path)
```

### Step 7 — Smoke test (against the synthetic dossier you already have)

This is the key insight for testing F06: **you don't need the full pipeline to work to test F06.** You have a real, valid F05 dossier from your synthetic-brief run. Save it as a fixture and run the Memo Writer + renderer against it directly.

```python
# src/dealscout/smoke_memo.py
"""Smoke test for F06: feed a saved F05 dossier through Memo Writer + renderer."""
from __future__ import annotations
import asyncio
from pathlib import Path
from dealscout.adapters.llm import configure_provider
from dealscout.observability.tracing import init_tracing
from dealscout.pipelines.memo import run_memo_writer
from dealscout.rendering.pdf import render_pdf
from dealscout.rendering.markdown import render_markdown

async def main() -> None:
    configure_provider()
    init_tracing()

    # Load the dossier you saved from F05 verification
    dossier = Path("tests/fixtures/stripe_dossier.md").read_text()

    print("Running Memo Writer...")
    memo = await run_memo_writer(dossier)
    print(f"OK — generated memo for {memo.company_name}")
    print(f"   Recommendation: {memo.recommendation}")
    print(f"   Strengths: {len(memo.strengths)}, Concerns: {len(memo.concerns)}")
    print(f"   References: {len(memo.references)}")

    pdf_path = "/tmp/smoke_memo.pdf"
    md_path = "/tmp/smoke_memo.md"
    render_pdf(memo, pdf_path)
    Path(md_path).write_text(render_markdown(memo))
    print(f"\nPDF: {pdf_path}")
    print(f"MD:  {md_path}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Save the dossier first.** Run your existing F05 synthetic-brief verification one more time, capture the dossier output to `tests/fixtures/stripe_dossier.md`, and use that as the fixture.

**Acceptance:**
- Smoke test runs without errors.
- PDF opens, looks recognizably like the sample memo.
- Markdown renders all sections with content.
- `memo.recommendation` is one of PASS/TRACK/MEET.
- `memo.strengths` and `memo.concerns` are exactly 3 each.
- `memo.references` has ≥4 entries.

### Step 8 — Integration test

```python
# tests/integration/test_memo_writer.py
import pytest
from pathlib import Path
from dealscout.adapters.llm import configure_provider
from dealscout.pipelines.memo import run_memo_writer
from dealscout.rendering.pdf import render_pdf
from dealscout.rendering.markdown import render_markdown

@pytest.mark.integration
@pytest.mark.asyncio
async def test_memo_writer_produces_valid_memo(tmp_path):
    """F06 against the saved Stripe dossier fixture."""
    configure_provider()
    dossier = Path("tests/fixtures/stripe_dossier.md").read_text()
    memo = await run_memo_writer(dossier)

    # Schema-level
    assert memo.recommendation in {"PASS", "TRACK", "MEET"}
    assert len(memo.strengths) == 3
    assert len(memo.concerns) == 3
    assert len(memo.references) >= 4

    # Content-level (loose)
    assert "stripe" in memo.company_name.lower()
    assert len(memo.executive_summary) >= 400

    # Renderers don't crash
    pdf = tmp_path / "test.pdf"
    render_pdf(memo, str(pdf))
    assert pdf.exists() and pdf.stat().st_size > 5000  # non-trivial PDF
    md = render_markdown(memo)
    assert "## Recommendation" in md or "Recommendation:" in md
```

---

## Quality gates before declaring done

- [ ] Schema-driven Memo Writer produces a valid `InvestmentMemo` from the Stripe dossier fixture
- [ ] PDF visually resembles the sample memo (same shape, palette, page chrome)
- [ ] Markdown output contains all sections in readable form
- [ ] Recommendation field is one of the three Literal values, with a rationale ≥50 chars
- [ ] Citations from the dossier are preserved in the memo body (some `[N]` markers visible)
- [ ] `references` field has at least 4 entries from the dossier source map
- [ ] Per-run cost for F06 alone < $0.05 (Memo Writer is cheap; no tools)

---

## DeepSeek-specific gotchas to flag

- **Structured output reliability.** This is the bigger risk for F06. The InvestmentMemo schema is the most complex you've used. If DeepSeek's structured-output mode through the OpenAI-compatible endpoint fails repeatedly, the fallback is the same one we noted for F01: drop `output_type`, ask the LLM to emit JSON, parse manually with `InvestmentMemo.model_validate_json()`. Try the native path first; only fall back if you see actual failures.
- **List-length enforcement.** Pydantic's `min_length`/`max_length` on lists will reject outputs that don't match. Watch the trace — DeepSeek may emit 4 strengths and you'll see validation errors. The fix is in the prompt: emphasize "EXACTLY THREE strengths" more aggressively, and the agent loop will self-correct on retry.
- **Citation preservation.** DeepSeek occasionally drops `[N]` markers when reformatting prose. If smoke test outputs have empty references, that's why — tighten the prompt's preservation rule.
- **Cost.** The Memo Writer's prompt is large (~15K tokens with the dossier). DeepSeek's cache will help on subsequent runs of the same dossier (e.g., during prompt iteration).

---

## What we explicitly defer

- ❌ **OCR pass to validate citation URLs are real.** Out of scope; F07 evals will surface obviously broken citations.
- ❌ **Streaming PDF generation.** Memos are small (4–5 pages). Render synchronously.
- ❌ **Custom company logos in the PDF.** No need until productionization.
- ❌ **Internationalization of the memo template.** English only.
- ❌ **Per-section regeneration.** If a memo has a weak section, F08 prompt iteration is the fix, not a "regenerate this section" feature.

---

## Definition of done

- [ ] `src/dealscout/domain/memo.py` with full `InvestmentMemo` schema (and `FounderProfile`, `NewsItem`, `Reference`)
- [ ] `prompts/memo_writer_v1.md` exists
- [ ] `src/dealscout/agents/memo_writer.py` builds an Agent with `output_type=InvestmentMemo`
- [ ] `src/dealscout/pipelines/memo.py` with `run_memo_writer(dossier) -> InvestmentMemo`
- [ ] `src/dealscout/rendering/pdf.py` with `render_pdf(memo, path) -> path`
- [ ] `src/dealscout/rendering/markdown.py` with `render_markdown(memo) -> str`
- [ ] `pipelines/analyze.py` updated with `run_full_analysis(input_str)` end-to-end
- [ ] `tests/fixtures/stripe_dossier.md` saved from F05 run
- [ ] `smoke_memo.py` runs and produces a PDF + Markdown
- [ ] Integration test `test_memo_writer.py` passes
- [ ] PDF visually resembles the sample
- [ ] Committed on branch `feature/06-memo-writer`

---

## Session plan

Roughly 3–4 hours.

1. **15 min** — Save the Stripe dossier from F05 to `tests/fixtures/stripe_dossier.md`. This is your test fixture for everything in F06.
2. **30 min** — Step 1. Schema. Reference the sample PDF section by section. Validate with `model_json_schema()`.
3. **30 min** — Steps 2–3. Prompt + agent. Read the prompt aloud.
4. **20 min** — Step 4. Pipeline function. Quick test against the fixture to confirm the agent produces a valid memo.
5. **75 min** — Step 5. Renderer. **Start by copying `build_sample_memo.py` as the skeleton.** Replace the hardcoded content with reads from the `InvestmentMemo`. The Markdown version is faster — write it first to confirm the schema is complete, then PDF.
6. **30 min** — Step 6. Wire it into `pipelines/analyze.py`.
7. **30 min** — Steps 7–8. Smoke test + integration test.
8. **15 min** — Commit, learnings file update.

If the schema-validated agent output fails on the first try, **don't immediately add fallback parsing**. Read the validation error — it'll tell you exactly which field the LLM got wrong, and that's a prompt fix, not an architecture fix.

---

## What to add to `my_work/learnings.md`

After F06 is green:

1. *Why is the Memo Writer an agent with no tools? What kind of "agent" is it?*
2. *The renderer is plain Python, not an agent. Why? What would be wrong with making it an agent?*
3. *What's the relationship between `Field(min_length=3, max_length=3)` on `strengths` and the prompt's "EXACTLY THREE" instruction? Why do we have both?*
4. *Open your PDF next to the sample memo. What's different? What's the same? If you swapped in someone else's company's memo, would the layout still work, or would it break in places?*

The fourth one is the F07 readiness check. If you can imagine the layout breaking on different content, that's where evals will catch the bug. Note it down — F07 starts in a couple of features.

---

## After F06

You will have, for the first time, **a working end-to-end DealScout pipeline.** URL or PDF → polished investment memo. That's the demo you can show on LinkedIn.

But don't post yet. F07 (evals) is what turns this from "a demo" into "an engineered AI system." Wait for that scorecard before going public.
