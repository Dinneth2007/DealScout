import type { components } from "@/types/api"
import { fetchWithWake, type WakeOptions } from "@/lib/wake"

export type Job = components["schemas"]["JobResponse"]
export type JobStatus = components["schemas"]["JobStatus"]

const API_BASE = (import.meta.env.VITE_API_BASE ?? "http://localhost:8000").replace(/\/$/, "")

export class ApiError extends Error {
  status: number
  rateLimited: boolean

  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.rateLimited = status === 429
  }
}

async function readError(resp: Response): Promise<string> {
  // FastAPI's HTTPException renders as { detail: "..." }; validation errors
  // come back as { detail: [{msg, loc, ...}] }. Handle both, fall back to text.
  try {
    const body = await resp.json()
    if (typeof body?.detail === "string") return body.detail
    if (Array.isArray(body?.detail) && body.detail[0]?.msg) return body.detail[0].msg
    return JSON.stringify(body)
  } catch {
    return resp.statusText || `Request failed (${resp.status})`
  }
}

export async function submitAnalysis(
  input: string,
  options?: WakeOptions,
): Promise<Job> {
  const resp = await fetchWithWake(
    `${API_BASE}/analyze`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input }),
    },
    options,
  )
  if (!resp.ok) throw new ApiError(await readError(resp), resp.status)
  return resp.json()
}

export async function getJob(id: string): Promise<Job> {
  const resp = await fetchWithWake(`${API_BASE}/jobs/${encodeURIComponent(id)}`)
  if (!resp.ok) throw new ApiError(await readError(resp), resp.status)
  return resp.json()
}

export async function getMemoMarkdown(id: string): Promise<string> {
  const resp = await fetch(`${API_BASE}/memos/${encodeURIComponent(id)}/markdown`)
  if (!resp.ok) throw new ApiError(await readError(resp), resp.status)
  return resp.text()
}

export function memoPdfUrl(id: string): string {
  return `${API_BASE}/memos/${encodeURIComponent(id)}/pdf`
}

export function memoMarkdownUrl(id: string): string {
  return `${API_BASE}/memos/${encodeURIComponent(id)}/markdown`
}
