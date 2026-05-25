import { Link } from "react-router"

export function SiteFooter() {
  return (
    <footer className="border-t border-border/60 bg-background/40">
      <div className="container flex flex-col items-center justify-between gap-2 py-6 text-xs text-muted-foreground sm:flex-row">
        <p>
          <span className="font-medium text-foreground">DealScout</span> · a research
          aid, not investment advice.
        </p>
        <nav className="flex items-center gap-4">
          <Link to="/about" className="hover:text-foreground">
            How it works
          </Link>
          <a
            href="https://github.com/Dinneth2007/DealScout"
            target="_blank"
            rel="noreferrer"
            className="hover:text-foreground"
          >
            Source
          </a>
        </nav>
      </div>
    </footer>
  )
}
