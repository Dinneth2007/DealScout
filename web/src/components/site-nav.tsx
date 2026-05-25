import { Link, NavLink } from "react-router"
import { ThemeToggle } from "@/components/theme-toggle"
import { GithubIcon } from "@/components/icons"
import { cn } from "@/lib/utils"

const NAV_ITEMS = [
  { to: "/analyze", label: "Analyze" },
  { to: "/about", label: "How it works" },
]

export function SiteNav() {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-border/60 bg-background/70 backdrop-blur">
      <div className="container flex h-14 items-center justify-between">
        <Link to="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <span className="inline-flex size-7 items-center justify-center rounded-md bg-accent text-accent-foreground text-sm font-bold">
            DS
          </span>
          <span>DealScout</span>
        </Link>
        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground",
                  isActive && "text-foreground",
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
          <a
            href="https://github.com/Dinneth2007/DealScout"
            target="_blank"
            rel="noreferrer"
            aria-label="GitHub repository"
            className="rounded-md p-2 text-muted-foreground transition-colors hover:text-foreground"
          >
            <GithubIcon className="size-4" />
          </a>
          <ThemeToggle />
        </nav>
      </div>
    </header>
  )
}
