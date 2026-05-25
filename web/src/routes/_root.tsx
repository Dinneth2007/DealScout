import { Outlet, ScrollRestoration } from "react-router"
import { Toaster } from "@/components/ui/sonner"
import { SiteNav } from "@/components/site-nav"
import { SiteFooter } from "@/components/site-footer"

export default function RootLayout() {
  return (
    <div className="relative flex min-h-svh flex-col bg-background bg-mesh">
      <SiteNav />
      <main className="flex-1">
        <Outlet />
      </main>
      <SiteFooter />
      <Toaster richColors closeButton />
      <ScrollRestoration />
    </div>
  )
}
