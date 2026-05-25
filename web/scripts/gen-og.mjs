// One-off generator for the social link-preview image.
// Run: `node scripts/gen-og.mjs`
// Output: public/og.png (1200x630, ~30-60 KB).
//
// Static SVG → PNG via resvg-js so we don't ship a runtime image service.
// Re-run only when the branding changes.

import { Resvg } from "@resvg/resvg-js"
import { writeFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, resolve } from "node:path"

const here = dirname(fileURLToPath(import.meta.url))
const out = resolve(here, "../public/og.png")

const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0b1220"/>
      <stop offset="100%" stop-color="#1e293b"/>
    </linearGradient>
    <radialGradient id="glow" cx="20%" cy="30%" r="60%">
      <stop offset="0%" stop-color="hsl(217, 91%, 60%)" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="hsl(217, 91%, 60%)" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glow2" cx="85%" cy="80%" r="50%">
      <stop offset="0%" stop-color="hsl(142, 60%, 50%)" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="hsl(142, 60%, 50%)" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <rect width="1200" height="630" fill="url(#bg)"/>
  <rect width="1200" height="630" fill="url(#glow)"/>
  <rect width="1200" height="630" fill="url(#glow2)"/>

  <g transform="translate(80, 80)">
    <rect width="56" height="56" rx="14" fill="hsl(217, 91%, 60%)"/>
    <text x="28" y="38" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
      font-weight="700" font-size="26" fill="white" letter-spacing="-1">DS</text>
    <text x="76" y="38" font-family="Inter, system-ui, sans-serif"
      font-weight="600" font-size="24" fill="#cbd5e1" letter-spacing="-0.5">DealScout</text>
  </g>

  <g transform="translate(80, 230)">
    <text font-family="Inter, system-ui, sans-serif" font-weight="600" font-size="68"
      fill="white" letter-spacing="-2.5">
      <tspan x="0" y="0">VC-grade memos</tspan>
      <tspan x="0" y="86">in three minutes.</tspan>
    </text>
    <text x="0" y="170" font-family="Inter, system-ui, sans-serif" font-weight="400"
      font-size="26" fill="#94a3b8" letter-spacing="-0.3">
      Multi-agent investment analyst on the OpenAI Agents SDK.
    </text>
  </g>

  <g transform="translate(80, 540)">
    <rect width="10" height="10" rx="5" fill="hsl(142, 60%, 50%)"/>
    <text x="22" y="10" font-family="Inter, system-ui, sans-serif" font-weight="500"
      font-size="18" fill="#cbd5e1" letter-spacing="0.2">
      Pass &#x2022; Track &#x2022; Meet &#x2014; structured + cited &#x2014; ~$0.25 per memo
    </text>
  </g>
</svg>
`

const resvg = new Resvg(svg, {
  fitTo: { mode: "width", value: 1200 },
  font: { loadSystemFonts: true },
})
const png = resvg.render().asPng()
writeFileSync(out, png)
console.log(`wrote ${out} (${png.length} bytes)`)
