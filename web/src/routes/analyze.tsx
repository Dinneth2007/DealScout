import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router"
import { toast } from "sonner"
import { ArrowRight, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { submitAnalysis, ApiError } from "@/lib/api"

const EXAMPLES = [
  { label: "Stripe", url: "https://stripe.com" },
  { label: "Modal", url: "https://modal.com" },
  { label: "Anthropic", url: "https://anthropic.com" },
]

export default function AnalyzePage() {
  const navigate = useNavigate()
  const [input, setInput] = useState("")
  const [submitting, setSubmitting] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    const value = input.trim()
    if (!value) {
      toast.error("Paste a URL first.")
      return
    }

    setSubmitting(true)
    let wakingToastId: string | number | undefined
    try {
      const job = await submitAnalysis(value, {
        onWaking: (attempt) => {
          if (wakingToastId === undefined) {
            wakingToastId = toast.loading(
              "Waking the analysis server — this can take ~30s on the first request.",
            )
          } else {
            toast.loading(`Still waking… (attempt ${attempt})`, { id: wakingToastId })
          }
        },
      })
      if (wakingToastId !== undefined) toast.dismiss(wakingToastId)
      navigate(`/memo/${job.job_id}`)
    } catch (err) {
      if (wakingToastId !== undefined) toast.dismiss(wakingToastId)
      if (err instanceof ApiError && err.rateLimited) {
        toast.error(err.message, { duration: 8000 })
      } else if (err instanceof ApiError) {
        toast.error(err.message || `Submission failed (${err.status})`)
      } else {
        toast.error(
          err instanceof Error ? err.message : "Something went wrong submitting the job.",
        )
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="container max-w-2xl py-16 sm:py-24">
      <header className="mb-8 text-center">
        <h1 className="text-balance text-4xl font-semibold tracking-tight sm:text-5xl">
          Analyze a startup
        </h1>
        <p className="mt-3 text-muted-foreground">
          Paste a URL. A research pipeline of five agents produces a structured
          investment memo in about three minutes.
        </p>
      </header>

      <Card className="p-6">
        <form onSubmit={onSubmit} className="flex flex-col gap-3 sm:flex-row">
          <Input
            type="url"
            inputMode="url"
            autoComplete="off"
            placeholder="https://stripe.com"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={submitting}
            className="h-11 flex-1 text-base"
            autoFocus
          />
          <Button type="submit" size="lg" disabled={submitting} className="gap-2">
            {submitting ? (
              <>
                <Loader2 className="size-4 animate-spin" /> Submitting
              </>
            ) : (
              <>
                Generate memo <ArrowRight className="size-4" />
              </>
            )}
          </Button>
        </form>
        <p className="mt-3 text-xs text-muted-foreground">
          Demo limit: 3 runs per IP per 24h. Each run costs the API ~$0.05–$0.25.
        </p>
      </Card>

      <div className="mt-8">
        <div className="mb-3 text-xs font-medium uppercase tracking-widest text-muted-foreground">
          Try one of these
        </div>
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex.url}
              type="button"
              onClick={() => setInput(ex.url)}
              disabled={submitting}
              className="rounded-full border border-border bg-background/60 px-3 py-1 text-sm text-muted-foreground transition-colors hover:border-accent hover:text-foreground disabled:opacity-50"
            >
              {ex.label}
            </button>
          ))}
        </div>
      </div>
    </section>
  )
}
