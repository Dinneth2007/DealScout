import { Link } from "react-router"
import { ArrowRight, Network, FileText, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { GithubIcon } from "@/components/icons"
import { cn } from "@/lib/utils"

type Rec = "MEET" | "TRACK" | "PASS"

const EXAMPLES: Array<{
  company: string
  recommendation: Rec
  oneLiner: string
  segment: string
}> = [
  {
    company: "Stripe",
    recommendation: "MEET",
    oneLiner: "Payments infrastructure for the internet.",
    segment: "Fintech · Payments",
  },
  {
    company: "Modal",
    recommendation: "TRACK",
    oneLiner: "Serverless compute for AI and data teams.",
    segment: "Infra · Compute",
  },
  {
    company: "Anthropic",
    recommendation: "MEET",
    oneLiner: "AI safety research lab building Claude.",
    segment: "AI · Foundation models",
  },
]

const STEPS = [
  {
    icon: Network,
    title: "Triage & intake",
    body: "URL or PDF in → a StartupBrief out. A Triage agent hands off to URL or PDF intake.",
  },
  {
    icon: Sparkles,
    title: "Parallel research",
    body: "Three specialist agents (Company, Market, Founder) run in parallel with web search and structured outputs.",
  },
  {
    icon: FileText,
    title: "Investment memo",
    body: "A Memo Writer agent synthesizes the dossier into a Pydantic-typed memo with Pass / Track / Meet.",
  },
]

const BUILT_ON = [
  "OpenAI Agents SDK",
  "FastAPI",
  "DeepSeek",
  "Tavily Search",
  "Langfuse",
  "Pydantic",
]

export default function LandingPage() {
  return (
    <>
      <Hero />
      <HowItWorks />
      <Examples />
      <BuiltOn />
      <BottomCta />
    </>
  )
}

function Hero() {
  return (
    <section className="container max-w-5xl pt-20 pb-16 sm:pt-28 sm:pb-24">
      <div className="flex flex-col items-center text-center">
        <span className="inline-flex items-center gap-2 rounded-full border border-border bg-background/60 px-3 py-1 text-xs text-muted-foreground backdrop-blur">
          <span className="inline-block size-1.5 rounded-full bg-rec-meet" />
          Multi-agent investment analyst
        </span>
        <h1 className="mt-6 text-balance text-5xl font-semibold tracking-tight sm:text-6xl">
          VC-grade memos in{" "}
          <span className="bg-gradient-to-r from-accent to-rec-meet bg-clip-text text-transparent">
            three minutes
          </span>
          .
        </h1>
        <p className="mt-5 max-w-2xl text-pretty text-lg text-muted-foreground">
          Paste a startup URL. Five specialist agents research the company,
          market, and founders in parallel, then write a structured investment
          memo with a Pass / Track / Meet recommendation.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Button asChild size="lg" className="gap-2">
            <Link to="/analyze">
              Generate a memo <ArrowRight className="size-4" />
            </Link>
          </Button>
          <Button asChild size="lg" variant="outline" className="gap-2">
            <a
              href="https://github.com/Dinneth2007/DealScout"
              target="_blank"
              rel="noreferrer"
            >
              <GithubIcon className="size-4" /> View source
            </a>
          </Button>
        </div>
        <p className="mt-5 text-xs text-muted-foreground">
          ~3 minutes per memo · under $0.25 in API costs · 10-startup eval set
        </p>
      </div>
    </section>
  )
}

function HowItWorks() {
  return (
    <section className="container max-w-5xl py-16">
      <div className="mb-10 text-center">
        <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          How it works
        </h2>
        <p className="mt-3 text-muted-foreground">
          An orchestrator-workers topology with a handoff at the front.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        {STEPS.map((step, idx) => (
          <Card
            key={step.title}
            className="relative p-6 transition-shadow hover:shadow-lg"
          >
            <div className="mb-4 inline-flex size-10 items-center justify-center rounded-lg bg-accent/10 text-accent">
              <step.icon className="size-5" />
            </div>
            <div className="mb-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Step {idx + 1}
            </div>
            <h3 className="text-lg font-semibold">{step.title}</h3>
            <p className="mt-2 text-sm text-muted-foreground">{step.body}</p>
          </Card>
        ))}
      </div>
    </section>
  )
}

function Examples() {
  return (
    <section className="container max-w-5xl py-16">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Sample memos
          </h2>
          <p className="mt-2 text-muted-foreground">
            What a finished memo looks like.
          </p>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        {EXAMPLES.map((memo) => (
          <Card key={memo.company} className="p-6 transition-shadow hover:shadow-lg">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-lg font-semibold">{memo.company}</h3>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {memo.segment}
                </p>
              </div>
              <RecommendationPill rec={memo.recommendation} />
            </div>
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              {memo.oneLiner}
            </p>
          </Card>
        ))}
      </div>
    </section>
  )
}

function BuiltOn() {
  return (
    <section className="container max-w-4xl py-16">
      <div className="text-center text-xs font-medium uppercase tracking-widest text-muted-foreground">
        Built on
      </div>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-sm text-muted-foreground">
        {BUILT_ON.map((name) => (
          <span key={name} className="font-medium">
            {name}
          </span>
        ))}
      </div>
    </section>
  )
}

function BottomCta() {
  return (
    <section className="container max-w-3xl py-20">
      <Card className="overflow-hidden p-10 text-center">
        <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          Try it on a startup you've been tracking.
        </h2>
        <p className="mx-auto mt-3 max-w-lg text-muted-foreground">
          Paste any URL, brew a coffee, come back to a memo.
        </p>
        <Button asChild size="lg" className="mt-6 gap-2">
          <Link to="/analyze">
            Generate a memo <ArrowRight className="size-4" />
          </Link>
        </Button>
      </Card>
    </section>
  )
}

function RecommendationPill({ rec }: { rec: Rec }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide text-white",
        rec === "MEET" && "bg-rec-meet",
        rec === "TRACK" && "bg-rec-track",
        rec === "PASS" && "bg-rec-pass",
      )}
    >
      {rec}
    </span>
  )
}
