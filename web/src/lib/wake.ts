// The DealScout API is on Render's free tier. After ~15 min idle it sleeps,
// and a request landing during the 90-150s boot gets a fast 502/503/504
// from the edge proxy. A scheduled GH Actions ping keeps it hot in normal
// use; this retry is the backstop for cases where the ping has been
// delayed or the dyno was just restarted.

const COLD_START_STATUSES = new Set([502, 503, 504])
const WAKE_BUDGET_MS = 180_000
const WAKE_RETRY_MS = 5_000

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms))

export interface WakeOptions {
  onWaking?: (attempt: number) => void
}

export async function fetchWithWake(
  input: RequestInfo | URL,
  init?: RequestInit,
  options?: WakeOptions,
): Promise<Response> {
  const deadline = Date.now() + WAKE_BUDGET_MS
  let attempt = 0

  while (true) {
    attempt += 1
    let response: Response | null = null
    try {
      response = await fetch(input, init)
      if (!COLD_START_STATUSES.has(response.status)) return response
    } catch (err) {
      // Network/connect errors during cold boot — treat as transient.
      if (Date.now() >= deadline) throw err
    }

    if (Date.now() >= deadline) {
      // Out of budget — return the last 502/503/504 so the caller can surface it.
      if (response) return response
      throw new Error("API did not wake within budget")
    }

    if (attempt >= 2) options?.onWaking?.(attempt)
    await sleep(WAKE_RETRY_MS)
  }
}
