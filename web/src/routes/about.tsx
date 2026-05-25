import { Card } from "@/components/ui/card"
import { GithubIcon } from "@/components/icons"
import { Button } from "@/components/ui/button"

const AGENTS = [
  {
    name: "Triage",
    role: "Routes incoming input (URL or PDF) and hands off to the right intake.",
  },
  {
    name: "URL / PDF Intake",
    role: "Fetches the source, extracts text, produces a structured StartupBrief.",
  },
  {
    name: "Company Researcher",
    role: "Web-searches the product, customers, and traction signals.",
  },
  {
    name: "Market Researcher",
    role: "Sizes the segment, surfaces competitors, frames the why-now thesis.",
  },
  {
    name: "Founder Researcher",
    role: "Pulls founder backgrounds and founder-market-fit signals.",
  },
  {
    name: "Orchestrator",
    role: "Wraps the three specialists as tools and synthesizes a dossier.",
  },
  {
    name: "Memo Writer",
    role: "Pydantic-structured output: bull/bear, recommendation, references.",
  },
]

const DECISIONS = [
  {
    title: "Evals first",
    body: "A fixed 10-startup eval set with a scoring rubric runs against every change. A broken eval is a real signal, not something to silence.",
  },
  {
    title: "Single LLM adapter",
    body: "All provider calls go through one wrapper. Switching DeepSeek ↔ Gemini is an env var; tracing and retries come for free.",
  },
  {
    title: "Versioned prompts",
    body: "Prompts live in /prompts and are versioned like database migrations. Never rewritten in place; old versions kept for eval comparison.",
  },
  {
    title: "Cost & rate guards",
    body: "Per-IP rate limit, daily provider cap, monthly search cap. Three independent ceilings so a bug in one can't drain the account alone.",
  },
  {
    title: "Bounded agent loops",
    body: "Every agent has an explicit max_turns; every tool has a timeout. Infinite loops are the most common LLM-app failure mode.",
  },
  {
    title: "Tracing",
    body: "Langfuse on every run — full trace tree for tool calls, latencies, token counts. Investigations don't depend on log scraping.",
  },
]

export default function AboutPage() {
  return (
    <section className="container max-w-3xl py-16 space-y-14">
      <header>
        <h1 className="text-balance text-4xl font-semibold tracking-tight sm:text-5xl">
          How DealScout works
        </h1>
        <p className="mt-3 text-lg text-muted-foreground">
          An orchestrator-workers system with a handoff at the front. Built on the
          OpenAI Agents SDK in Python; the frontend is a Vite React SPA.
        </p>
      </header>

      <ArchitectureDiagram />

      <section>
        <h2 className="text-2xl font-semibold tracking-tight">The agents</h2>
        <p className="mt-2 text-muted-foreground">
          Each is its own prompt file with at least two eval cases.
        </p>
        <Card className="mt-4 divide-y divide-border/60 p-0">
          {AGENTS.map((a) => (
            <div key={a.name} className="grid grid-cols-[140px_1fr] gap-4 p-4 sm:p-5">
              <div className="text-sm font-semibold">{a.name}</div>
              <div className="text-sm text-muted-foreground">{a.role}</div>
            </div>
          ))}
        </Card>
      </section>

      <section>
        <h2 className="text-2xl font-semibold tracking-tight">Engineering decisions</h2>
        <p className="mt-2 text-muted-foreground">
          The non-obvious choices that make the system reliable rather than just
          impressive in a screenshot.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {DECISIONS.map((d) => (
            <Card key={d.title} className="p-5">
              <h3 className="font-semibold">{d.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{d.body}</p>
            </Card>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-2xl font-semibold tracking-tight">Read the code</h2>
        <p className="mt-2 text-muted-foreground">
          The interesting bits are small and worth a look.
        </p>
        <ul className="mt-4 space-y-2 text-sm">
          <li>
            <code className="rounded bg-muted px-1.5 py-0.5">src/dealscout/pipelines/</code>{" "}
            — analyze, intake, memo pipelines (the orchestration shape).
          </li>
          <li>
            <code className="rounded bg-muted px-1.5 py-0.5">src/dealscout/agents/</code>{" "}
            — agent definitions with their tools and structured outputs.
          </li>
          <li>
            <code className="rounded bg-muted px-1.5 py-0.5">prompts/</code> —
            versioned prompts; nothing important is hidden in code strings.
          </li>
          <li>
            <code className="rounded bg-muted px-1.5 py-0.5">tests/eval/</code> —
            the eval harness and the rubric.
          </li>
        </ul>
        <div className="mt-6">
          <Button asChild variant="outline" className="gap-2">
            <a
              href="https://github.com/Dinneth2007/DealScout"
              target="_blank"
              rel="noreferrer"
            >
              <GithubIcon className="size-4" />
              View source on GitHub
            </a>
          </Button>
        </div>
      </section>
    </section>
  )
}

function ArchitectureDiagram() {
  return (
    <figure>
      <div className="overflow-x-auto rounded-xl border border-border/60 bg-card/40 p-6">
        <svg
          viewBox="0 0 820 280"
          xmlns="http://www.w3.org/2000/svg"
          className="mx-auto block h-auto w-full max-w-[820px] text-foreground"
        >
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 z" fill="currentColor" opacity="0.55" />
            </marker>
          </defs>
          {/* Input */}
          <g>
            <rect x="20" y="120" width="120" height="40" rx="8" fill="hsl(var(--muted))" stroke="hsl(var(--border))" />
            <text x="80" y="145" textAnchor="middle" fontSize="13" fill="currentColor">URL / PDF</text>
          </g>

          {/* Triage */}
          <g>
            <rect x="180" y="120" width="120" height="40" rx="8" fill="hsl(var(--accent) / 0.08)" stroke="hsl(var(--accent))" />
            <text x="240" y="145" textAnchor="middle" fontSize="13" fontWeight="500" fill="currentColor">Triage</text>
          </g>

          {/* Intake */}
          <g>
            <rect x="340" y="120" width="120" height="40" rx="8" fill="hsl(var(--accent) / 0.08)" stroke="hsl(var(--accent))" />
            <text x="400" y="145" textAnchor="middle" fontSize="13" fontWeight="500" fill="currentColor">Intake</text>
          </g>

          {/* Orchestrator */}
          <g>
            <rect x="500" y="120" width="140" height="40" rx="8" fill="hsl(var(--accent) / 0.08)" stroke="hsl(var(--accent))" />
            <text x="570" y="145" textAnchor="middle" fontSize="13" fontWeight="500" fill="currentColor">Orchestrator</text>
          </g>

          {/* Specialists (3 in parallel, top) */}
          <g>
            <rect x="680" y="40" width="120" height="32" rx="6" fill="hsl(var(--card))" stroke="hsl(var(--border))" />
            <text x="740" y="60" textAnchor="middle" fontSize="11" fill="currentColor">Company</text>
            <rect x="680" y="80" width="120" height="32" rx="6" fill="hsl(var(--card))" stroke="hsl(var(--border))" />
            <text x="740" y="100" textAnchor="middle" fontSize="11" fill="currentColor">Market</text>
            <rect x="680" y="120" width="120" height="32" rx="6" fill="hsl(var(--card))" stroke="hsl(var(--border))" />
            <text x="740" y="140" textAnchor="middle" fontSize="11" fill="currentColor">Founder</text>
          </g>

          {/* Memo Writer */}
          <g>
            <rect x="500" y="210" width="140" height="40" rx="8" fill="hsl(var(--rec-meet) / 0.12)" stroke="hsl(var(--rec-meet))" />
            <text x="570" y="235" textAnchor="middle" fontSize="13" fontWeight="500" fill="currentColor">Memo Writer</text>
          </g>

          {/* Arrows: horizontal pipeline */}
          <line x1="140" y1="140" x2="180" y2="140" stroke="currentColor" strokeOpacity="0.55" markerEnd="url(#arrow)" />
          <line x1="300" y1="140" x2="340" y2="140" stroke="currentColor" strokeOpacity="0.55" markerEnd="url(#arrow)" />
          <line x1="460" y1="140" x2="500" y2="140" stroke="currentColor" strokeOpacity="0.55" markerEnd="url(#arrow)" />

          {/* Orchestrator -> 3 specialists (fan out) */}
          <line x1="640" y1="135" x2="680" y2="56" stroke="currentColor" strokeOpacity="0.55" strokeDasharray="3 3" markerEnd="url(#arrow)" />
          <line x1="640" y1="140" x2="680" y2="96" stroke="currentColor" strokeOpacity="0.55" strokeDasharray="3 3" markerEnd="url(#arrow)" />
          <line x1="640" y1="145" x2="680" y2="136" stroke="currentColor" strokeOpacity="0.55" strokeDasharray="3 3" markerEnd="url(#arrow)" />

          {/* Orchestrator -> Memo Writer */}
          <line x1="570" y1="160" x2="570" y2="210" stroke="currentColor" strokeOpacity="0.55" markerEnd="url(#arrow)" />
        </svg>
      </div>
      <figcaption className="mt-3 text-center text-xs text-muted-foreground">
        Solid arrows are sequential; dashed arrows are parallel agent-as-tool calls.
      </figcaption>
    </figure>
  )
}
