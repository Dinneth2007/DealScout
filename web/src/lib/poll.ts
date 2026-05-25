import { useQuery } from "@tanstack/react-query"
import { getJob, type Job } from "@/lib/api"

const POLL_INTERVAL_MS = 5_000

export function useJobPolling(jobId: string | undefined) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data as Job | undefined
      if (!data) return POLL_INTERVAL_MS
      if (data.status === "complete" || data.status === "failed") return false
      return POLL_INTERVAL_MS
    },
    refetchIntervalInBackground: true,
    // The job lifecycle is server-driven — stale-while-revalidate would just
    // race with the next poll, so disable cache freshness gating here.
    staleTime: 0,
    gcTime: 60_000,
  })
}
