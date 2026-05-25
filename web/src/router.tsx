import { createBrowserRouter } from "react-router"
import RootLayout from "@/routes/_root"
import LandingPage from "@/routes/index"
import AnalyzePage from "@/routes/analyze"
import MemoPage from "@/routes/memo.$id"
import AboutPage from "@/routes/about"

export const router = createBrowserRouter([
  {
    path: "/",
    Component: RootLayout,
    children: [
      { index: true, Component: LandingPage },
      { path: "analyze", Component: AnalyzePage },
      { path: "memo/:id", Component: MemoPage },
      { path: "about", Component: AboutPage },
    ],
  },
])
