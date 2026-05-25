import { Link, useParams } from "react-router"
import { useQuery } from "@tanstack/react-query"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import {
  AlertTriangle,
  ArrowLeft,
  Download,
  FileDown,
  Loader2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { useJobPolling } from "@/lib/poll"
import {
  getMemoMarkdown,
  memoMarkdownUrl,
  memoPdfUrl,
  type Job,
} from "@/lib/api"
import {
  RecommendationPill,
  isRecommendation,
} from "@/components/recommendation-pill"

export default function MemoPage() {
  const { id } = useParams<{ id: string }>()
  const job = useJobPolling(id)

  if (!id) return <NotFound />

  if (job.isLoading) return <Loading />
  if (job.error) return <FetchError message={(job.error as Error).message} />
  if (!job.data) return <Loading />

  const data = job.data
  if (data.status === "failed") return <Failed job={data} />
  if (data.status !== "complete") return <Running job={data} />
  return <Complete job={data} id={id} />
}

function Loading() {
  return (
    <section className="container max-w-3xl py-16">
      <Skeleton className="h-8 w-2/3" />
      <Skeleton className="mt-4 h-4 w-1/3" />
      <Skeleton className="mt-10 h-40 w-full" />
    </section>
  )
}

function NotFound() {
  return (
    <section className="container max-w-3xl py-16">
      <h1 className="text-2xl font-semibold">Memo not found</h1>
      <Button asChild variant="link" className="mt-2 px-0">
        <Link to="/analyze">Start a new analysis</Link>
      </Button>
    </section>
  )
}

function FetchError({ message }: { message: string }) {
  return (
    <section className="container max-w-2xl py-16">
      <Card className="p-6">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 size-5 text-destructive" />
          <div>
            <h2 className="text-lg font-semibold">Couldn't load this memo</h2>
            <p className="mt-1 text-sm text-muted-foreground">{message}</p>
            <Button asChild variant="link" className="mt-2 px-0">
              <Link to="/analyze">Start a new analysis</Link>
            </Button>
          </div>
        </div>
      </Card>
    </section>
  )
}

const RESEARCHERS = ["Company", "Market", "Founder"]

function Running({ job }: { job: Job }) {
  const message = job.progress_message || "Initialising…"
  const isResearching = /research/i.test(message)

  return (
    <section className="container max-w-2xl py-16">
      <header className="mb-6 text-center">
        <h1 className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
          Generating memo
        </h1>
        <p className="mt-2 text-muted-foreground">
          Typical runtime: 2–4 minutes. Feel free to leave the tab open.
        </p>
      </header>
      <Card className="p-6">
        <div className="flex items-center gap-3 text-sm">
          <Loader2 className="size-4 animate-spin text-accent" />
          <span className="font-medium">{message}</span>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          {RESEARCHERS.map((r) => (
            <div
              key={r}
              className={
                "rounded-lg border border-border/60 p-4 text-center text-sm transition-opacity " +
                (isResearching ? "animate-pulse-slow" : "opacity-60")
              }
            >
              <div className="font-medium">{r}</div>
              <div className="text-xs text-muted-foreground">researcher</div>
            </div>
          ))}
        </div>
        <p className="mt-6 text-xs text-muted-foreground">
          Job ID: <code className="rounded bg-muted px-1.5 py-0.5">{job.job_id}</code>
        </p>
      </Card>
    </section>
  )
}

function Failed({ job }: { job: Job }) {
  return (
    <section className="container max-w-2xl py-16">
      <Card className="p-6">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 size-5 text-destructive" />
          <div className="flex-1">
            <h2 className="text-lg font-semibold">This analysis failed</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {job.error_message ?? "The pipeline returned an unknown error."}
            </p>
            <div className="mt-4 flex gap-2">
              <Button asChild>
                <Link to="/analyze">Try again</Link>
              </Button>
              <Button asChild variant="outline">
                <Link to="/">Back to home</Link>
              </Button>
            </div>
          </div>
        </div>
      </Card>
    </section>
  )
}

function Complete({ job, id }: { job: Job; id: string }) {
  const memo = useQuery({
    queryKey: ["memo-markdown", id],
    queryFn: () => getMemoMarkdown(id),
    staleTime: Infinity,
  })

  const recRaw = (job.recommendation ?? "").toUpperCase()
  const rec = isRecommendation(recRaw) ? recRaw : null

  return (
    <section className="container max-w-3xl py-12">
      <div className="mb-6">
        <Button asChild variant="link" className="px-0 text-muted-foreground">
          <Link to="/analyze">
            <ArrowLeft className="size-3.5" /> Analyze another
          </Link>
        </Button>
      </div>

      <Card className="p-6 sm:p-8">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
              {job.company_name ?? "Investment memo"}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Generated in {Math.round(job.latency_seconds ?? 0)}s · estimated cost $
              {(job.cost_usd_estimate ?? 0).toFixed(2)}
            </p>
          </div>
          {rec && <RecommendationPill rec={rec} size="lg" />}
        </header>

        <div className="mt-6 flex flex-wrap gap-2">
          <Button asChild size="sm" variant="outline" className="gap-1.5">
            <a href={memoPdfUrl(id)} target="_blank" rel="noreferrer">
              <FileDown className="size-3.5" /> Download PDF
            </a>
          </Button>
          <Button asChild size="sm" variant="outline" className="gap-1.5">
            <a href={memoMarkdownUrl(id)} target="_blank" rel="noreferrer">
              <Download className="size-3.5" /> Markdown
            </a>
          </Button>
        </div>

        <article className="prose prose-slate mt-8 max-w-none dark:prose-invert prose-headings:font-semibold prose-h1:hidden prose-h2:mt-8 prose-h2:text-xl prose-h3:text-base prose-p:text-foreground/90 prose-li:text-foreground/90">
          {memo.isLoading && (
            <div className="space-y-2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
            </div>
          )}
          {memo.error && (
            <p className="text-sm text-destructive">
              Failed to load the memo body: {(memo.error as Error).message}
            </p>
          )}
          {memo.data && (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{memo.data}</ReactMarkdown>
          )}
        </article>
      </Card>
    </section>
  )
}
