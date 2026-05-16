# DealScout — Feature Roadmap

**Purpose of this doc:** load this when deciding what to work on next, when scoping how much is left, or when explaining the project to someone.

Features are numbered in **build order**, not priority. Don't skip ahead — each feature builds on the ones before it. Each numbered feature has its own `docs/features/<NN>-<name>.md` spec.

---

## The big picture

DealScout ships in **8 phases**, roughly one phase per week of focused work (less if you batch sessions). Each phase ends with a working demo of something — never a half-built mess.

| Phase | Feature | Status |
|-------|---------|--------|
| 0 — Foundations | F00 — Scaffolding & Gemini LLM Adapter | ✅ done |
| 1 — Intake | F01 — Triage + URL/PDF Intake (Handoffs) | ✅ done |
| 2 — First Specialist | F02 — Company Researcher (ReAct + tools) | ⏳ next |
| 3 — Other Specialists | F03 — Market Researcher · F04 — Founder Researcher | ⏳ |
| 4 — Orchestrator | F05 — Investment Lead (Agents-as-Tools) | ⏳ |
| 5 — Memo | F06 — Memo Writer (Structured Output) | ⏳ |
| 6 — Evaluation | F07 — Eval Harness · F08 — Prompt Iteration | ⏳ |
| 7 — Productionization | F09 — Modes Comparison · F10 — API + UI · F11 — Deploy | ⏳ |

---

## Phase 0 — Foundations (✅ done)

**F00 — Project Scaffolding & Gemini LLM Adapter**
The Python project, `.env` handling via Pydantic Settings, the LLM adapter that everything goes through, Gemini wired via OpenAI-compatible endpoint, Langfuse for observability, a smoke test that proves end-to-end.

✋ **Gate:** `uv run python -m dealscout.smoke` made one Gemini call and a Langfuse trace appeared.

**What this taught:** Singleton config + provider-agnostic adapter pattern. Why all LLM calls funnel through one wrapper. Why Pydantic Settings fails loudly instead of returning empty strings.

---

## Phase 1 — Intake (✅ done)

**F01 — Triage + URL Intake + PDF Intake**
Three agents and a `StartupBrief` Pydantic schema. Triage hands off to URLIntake or PDFIntake based on input type. Each Intake agent has its specialty tool (`fetch_url` or `parse_pdf`) and produces a typed `StartupBrief`.

✋ **Gate:** Given a URL or a PDF path, intake produced a valid `StartupBrief`.

**What this taught:** The handoff pattern. Structured output via Pydantic. Errors-as-data in tool returns. Narrow agents > polymorphic agents.

---

## Phase 2 — First Specialist (⏳ next)

**F02 — Company Researcher**
A single ReAct-style agent that takes a `StartupBrief` and produces free-form research notes about the company itself: product, customers, traction signals, recent news, mentioned competitors. Has two tools — `search_web` (Tavily) and `fetch_url` (from F01).

✋ **Gate:** Calling the Company Researcher in isolation on a known startup (e.g., Stripe) returns useful research notes. Langfuse trace shows the LLM reasoning across multiple tool calls. Cost stays under $0.05 per research run.

**What this will teach:** Writing prompts for *judgment* not extraction. Tool surface design — how the LLM picks the right tool at the right time. Bounding agent loops without hardcoding behavior. Starting an informal eval discipline.

---

## Phase 3 — Other Specialists (⏳)

**F03 — Market Researcher**
Same shape as F02 but focused on market sizing, industry trends, competitor landscape, and a Fermi-estimation reasoning approach for TAM. Tool surface: `search_web` plus a `tam_estimator` prompt-as-tool.

**F04 — Founder Researcher**
Same shape but focused on founder backgrounds and prior companies via search results. We deliberately don't scrape LinkedIn directly — too gnarly, too fragile. Search results give us what we need at this stage.

✋ **Gate:** All three researchers callable independently. Each has at least 2 eval cases with expected output dimensions defined.

**What this will teach:** How the *same* agent pattern (ReAct + tools + free-form output) yields different outcomes depending on prompt and tool design. The compounding payoff of having gotten F02 right.

---

## Phase 4 — Orchestrator (⏳)

**F05 — Investment Lead (the orchestrator)**
Wraps the three researchers via `.as_tool()` and coordinates them. Decides what to research first, calls specialists in parallel where possible (Gemini quirk — may run serially via the compatible endpoint; acceptable), synthesizes their outputs into a combined research picture. Uses `gemini-2.5-pro` because synthesis quality matters.

✋ **Gate:** End-to-end research pipeline working — give it a URL or PDF, get back synthesized research across all three angles. Still no memo. Cost under $0.20.

**What this will teach:** The agents-as-tools pattern in earnest. When to use `gpt-4o`-tier models for reasoning hubs vs. `flash`-tier for specialists. How to write an "orchestrator" system prompt that delegates well.

---

## Phase 5 — Memo (⏳)

**F06 — Memo Writer + PDF Renderer**
Pydantic `InvestmentMemo` schema with all the sections (one-liner, market, founder background, three strengths, three concerns, Pass/Track/Meet recommendation, sources). The Memo Writer is itself an agent-as-tool the Orchestrator calls — meaning the Orchestrator decides when the research is sufficient to write. A separate renderer turns the structured memo into a Markdown file and a styled PDF.

✋ **Gate:** Full end-to-end run produces a valid `InvestmentMemo` that renders to readable PDF. Visually polished enough to show someone.

**What this will teach:** Structured output at scale (much more complex schema than `StartupBrief`). Separation between LLM output and presentation. The point at which you have a *product*, not a demo.

---

## Phase 6 — Evaluation (⏳ the CV-worthy part)

**F07 — Eval Harness**
A fixed set of 10 curated startup inputs with known correct recommendations, structured into eval cases. A scoring rubric across multiple dimensions: schema validity, citation quality, recommendation reasonableness, latency, cost. A CLI command `uv run python -m dealscout.evals run` outputs a scorecard.

✋ **Gate:** Baseline pass rate ≥ 60% on the eval set. Scorecard reproducible.

**F08 — Prompt Iteration to 80%+**
Not really a "feature" — a *phase* of reading failing eval traces, hypothesizing root causes, bumping prompt versions (`company_researcher_v1.md` → `v2.md`), re-running evals, tracking pass rate per version.

✋ **Gate:** Eval pass rate ≥ 80%. Prompt versioning visible in git history. You can show on the README: "v1 = 62%, v2 = 71%, v3 = 84%."

**What this will teach:** The single most important AI-engineering discipline. Most "AI projects" on the internet have zero evals. Having them — and showing iteration — is what separates portfolio projects from impressive portfolio projects.

---

## Phase 7 — Productionization (⏳)

**F09 — Modes Comparison Toggle**
The CV-worthy showpiece. The same input runs three ways:
- (a) single LLM call, no tools — baseline
- (b) one ReAct agent with all tools — middle ground
- (c) full multi-agent orchestrator (the real DealScout) — production

Side-by-side cost, latency, quality comparison. This is the feature that signals senior judgment: *you understand that complexity is a cost and chose the multi-agent path deliberately.*

**F10 — FastAPI Service + Gradio UI**
Wraps the pipeline in an async HTTP service with a simple in-memory job queue (memo generation takes 2–5 min; can't be synchronous). Gradio UI on top — paste URL or upload PDF, see a progress indicator, get the PDF.

**F11 — Deployment**
Render or Fly.io. Public URL. Dockerfile. Cost limits set in the Gemini dashboard. README with screenshots, the live link, and the eval scorecard.

✋ **Phase gate:** Live, public, working URL on your LinkedIn post.

**What this will teach:** Job queues + agents (because agents are slow). Productionization of a Python service. Deploying without Kubernetes. How to *frame* the project for a recruiter audience.

---

## Milestone shipping plan (for LinkedIn / portfolio)

Don't wait until F11 to talk about this publicly. Ship the *story* along with the code.

- **End of Phase 2 (F02 done):** First LinkedIn post — "I built a tool-using agent in Python. Here's why I'm avoiding LangChain for now and what 'tool calling' actually means." Architectural post, no UI needed.
- **End of Phase 5 (F06 done):** Second post — show a real memo PDF. "Three minutes, $0.18, one PDF. Here's how the agent pipeline produces it."
- **End of Phase 6 (F08 done):** Third post — *the* post. "Most AI-agent demos have no evals. Here's mine, and how iteration moved pass rate from 62% to 84%." This is the post that gets you noticed.
- **End of Phase 7 (F11 done):** Final post — public link, screenshots, repo. "Try it: <URL>. Source: <github>. Built over N weeks while learning the OpenAI Agents SDK."

Each post is more impressive than the last *because* it builds on the previous. Recruiters seeing the third or fourth post will scroll back through the chain.

---

## What we explicitly defer (and why each rejection matters)

These tempt every learner. I'm calling them out so you don't get distracted.

- ❌ **Memory / RAG across sessions.** Each analysis is independent. Adding memory is a different project.
- ❌ **Multi-agent debate (Bull vs Bear).** Considered for the recommendation step. Rejected: doubles cost for marginal quality. The Orchestrator + 3 researchers is sufficient signal.
- ❌ **Human-in-the-loop.** No irreversible actions in DealScout (it's read-only research). HITL would be theater.
- ❌ **Vector store / knowledge base.** All retrieval is live web search per task. The corpus of "startups" is unbounded; a vector store would be maintenance burden with no payoff.
- ❌ **Fine-tuning Gemini.** Massive complexity, marginal benefit. Prompt engineering + evals (F08) will get you most of the way.
- ❌ **Multiple LLM providers in production.** The adapter supports it. We'll add a second provider only when there's a concrete reason (cost spike, capability gap, eval insight).

If you find yourself wanting to add any of these mid-build, write it on a *separate* file (`my_work/ideas.md`) and keep moving. Scope creep kills portfolio projects.

---

## Timeline reality check

Honest estimates per phase, assuming 4–6 focused hours per week:

| Phase | Calendar time |
|-------|---------------|
| 0 — Foundations | 1 week ✅ |
| 1 — Intake | 1 week ✅ |
| 2 — First Specialist | 1 week (you are here) |
| 3 — Other Specialists | 1 week |
| 4 — Orchestrator | 1–2 weeks |
| 5 — Memo | 1 week |
| 6 — Evaluation | 2 weeks (prompt iteration is slow) |
| 7 — Productionization | 1–2 weeks |
| **Total** | **9–11 weeks** |

If you blow past these by 50%, something is wrong (over-engineering, scope creep, or stuck on an SDK quirk). Stop and ask.

If you're under by 50%, you're probably skipping the *learnings* part. Each feature is supposed to teach you something durable — slow down enough to capture it.
