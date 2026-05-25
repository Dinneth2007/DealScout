import { cn } from "@/lib/utils"

export type Recommendation = "MEET" | "TRACK" | "PASS"

const STYLES: Record<Recommendation, string> = {
  MEET: "bg-rec-meet",
  TRACK: "bg-rec-track",
  PASS: "bg-rec-pass",
}

export function RecommendationPill({
  rec,
  size = "sm",
}: {
  rec: Recommendation
  size?: "sm" | "lg"
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-semibold uppercase tracking-wide text-white",
        STYLES[rec],
        size === "lg" ? "px-3 py-1 text-sm" : "px-2.5 py-0.5 text-xs",
      )}
    >
      {rec}
    </span>
  )
}

export function isRecommendation(v: unknown): v is Recommendation {
  return v === "MEET" || v === "TRACK" || v === "PASS"
}
