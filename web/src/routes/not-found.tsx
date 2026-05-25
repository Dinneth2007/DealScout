import { Link } from "react-router"
import { Button } from "@/components/ui/button"

export default function NotFoundPage() {
  return (
    <section className="container max-w-xl py-24 text-center">
      <p className="text-sm font-medium uppercase tracking-widest text-muted-foreground">
        404
      </p>
      <h1 className="mt-3 text-balance text-4xl font-semibold tracking-tight">
        That page isn't part of the deck.
      </h1>
      <p className="mt-3 text-muted-foreground">
        The URL doesn't match any route. Memos expire when the API dyno
        restarts — if you got here from an old link, that's likely why.
      </p>
      <div className="mt-8 flex justify-center gap-2">
        <Button asChild>
          <Link to="/analyze">Generate a memo</Link>
        </Button>
        <Button asChild variant="outline">
          <Link to="/">Back to home</Link>
        </Button>
      </div>
    </section>
  )
}
