import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { getInferenceProgress } from '../api/client'
import { useAppStore } from '../stores/appStore'

export function useInferenceProgressPoll() {
  const activeJobId = useAppStore((s) => s.activeJobId)
  const setActiveJobId = useAppStore((s) => s.setActiveJobId)
  const setLastCompletedInference = useAppStore((s) => s.setLastCompletedInference)
  const qc = useQueryClient()

  const query = useQuery({
    queryKey: ['inference-progress', activeJobId],
    queryFn: () => (activeJobId ? getInferenceProgress(activeJobId) : Promise.resolve(null)),
    enabled: !!activeJobId,
    refetchInterval: 2000,
  })

  useEffect(() => {
    if (query.data && query.data.request_state !== 'running' && activeJobId) {
      // Save completed data before clearing active job
      setLastCompletedInference(query.data)
      setActiveJobId(null)
      void qc.invalidateQueries({ queryKey: ['system-status'] })
      void qc.invalidateQueries({ queryKey: ['snapshot'] })
    }
  }, [query.data, activeJobId, setActiveJobId, setLastCompletedInference, qc])

  return query
}
