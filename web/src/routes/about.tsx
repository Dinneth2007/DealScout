export default function AboutPage() {
  return (
    <section className="container max-w-3xl py-16 space-y-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">How it works</h1>
        <p className="mt-2 text-muted-foreground">
          DealScout is an orchestrator-workers system built on the OpenAI Agents
          SDK.
        </p>
      </header>
      <ol className="space-y-4 text-sm leading-relaxed">
        <li>
          <strong className="text-foreground">Triage agent</strong> routes input
          (URL or PDF) to the right intake pipeline and produces a structured
          StartupBrief.
        </li>
        <li>
          <strong className="text-foreground">Orchestrator</strong> invokes three
          specialist researchers in parallel — Company, Market, and Founder —
          each with web search and structured-output tools.
        </li>
        <li>
          <strong className="text-foreground">Memo writer</strong> synthesizes
          the dossier into a Pydantic-typed InvestmentMemo with a Pass / Track /
          Meet recommendation.
        </li>
      </ol>
      <p className="text-sm text-muted-foreground">
        Every run is traced with Langfuse, evaluated against a fixed 10-startup
        eval set, and capped by per-IP rate limits and provider cost budgets.
      </p>
    </section>
  )
}
