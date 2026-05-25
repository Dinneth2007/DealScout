import { useParams } from "react-router"

export default function MemoPage() {
  const { id } = useParams()
  return (
    <section className="container max-w-3xl py-16">
      <h1 className="text-3xl font-semibold tracking-tight">Memo</h1>
      <p className="mt-3 text-muted-foreground">
        Memo viewer for job <code className="rounded bg-muted px-1.5 py-0.5">{id}</code>{" "}
        ships in Phase B.
      </p>
    </section>
  )
}
