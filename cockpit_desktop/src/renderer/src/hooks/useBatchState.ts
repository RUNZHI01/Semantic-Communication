import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { getBatchState, getSystemStatus } from '../api/client'
import { useAppStore } from '../stores/appStore'
import { buildBatchCompletionToken, shouldRefreshCompletedBatch } from './inferenceStateMachine'
import { getBatchStateRefetchInterval } from './pollingPolicy'

export function useBatchStatePoll() {
  const qc = useQueryClient()
  const setLastCompletedInference = useAppStore((s) => s.setLastCompletedInference)
  const lastSettledBatchToken = useAppStore((s) => s.lastSettledBatchToken)
  const setLastSettledBatchToken = useAppStore((s) => s.setLastSettledBatchToken)

  const query = useQuery({
    queryKey: ['batch-state'],
    queryFn: getBatchState,
    refetchInterval: (q) => getBatchStateRefetchInterval(q.state.data),
  })

  useEffect(() => {
    if (shouldRefreshCompletedBatch(lastSettledBatchToken, query.data)) {
      const completionToken = buildBatchCompletionToken(query.data)
      setLastSettledBatchToken(completionToken)
      void qc.fetchQuery({
        queryKey: ['system-status'],
        queryFn: getSystemStatus,
      }).then((payload) => {
        const current = payload?.recent_results?.current
        if (current?.execution_mode === 'live' && current?.status === 'success') {
          setLastCompletedInference(current)
        }
      }).catch(() => undefined)
      void qc.invalidateQueries({ queryKey: ['snapshot'] })
    }
  }, [query.data, qc, setLastCompletedInference, lastSettledBatchToken, setLastSettledBatchToken])

  return query
}
