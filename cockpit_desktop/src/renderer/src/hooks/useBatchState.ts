import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import type { BatchStateResponse } from '../api/types/crypto'
import { getBatchState, getSystemStatus } from '../api/client'
import { useAppStore } from '../stores/appStore'
import { buildBatchCompletionToken, shouldHydrateRecentCurrentForBatch, shouldRefreshCompletedBatch } from './inferenceStateMachine'
import { getBatchStateRefetchInterval } from './pollingPolicy'

function recordCompletedBatchComparison(
  payload: BatchStateResponse,
  setComparisonResult: ReturnType<typeof useAppStore.getState>['setComparisonResult'],
) {
  if (payload.status !== 'done') {
    return
  }
  const engine = payload.engine === 'mnn' ? 'mnn' : 'tvm'
  const totalMetric = payload.benchmark?.total_ms
  const inferenceMetric = payload.benchmark?.inference_ms
  const reconstructionMs =
    totalMetric?.median_ms
    ?? totalMetric?.mean_ms
    ?? (engine === 'tvm' ? (inferenceMetric?.median_ms ?? inferenceMetric?.mean_ms) : undefined)
  if (reconstructionMs == null) {
    return
  }
  setComparisonResult(engine, {
    engine,
    label: engine === 'mnn' ? 'MNN重建' : 'TVM重建',
    reconstructionMs,
    runMs: inferenceMetric?.median_ms ?? inferenceMetric?.mean_ms,
    sampleCount: totalMetric?.n ?? inferenceMetric?.n ?? payload.completed,
    updatedAt: Date.now(),
  })
}

export function useBatchStatePoll() {
  const qc = useQueryClient()
  const setLastCompletedInference = useAppStore((s) => s.setLastCompletedInference)
  const lastSettledBatchToken = useAppStore((s) => s.lastSettledBatchToken)
  const setLastSettledBatchToken = useAppStore((s) => s.setLastSettledBatchToken)
  const pendingBatchJobId = useAppStore((s) => s.pendingBatchJobId)
  const setComparisonResult = useAppStore((s) => s.setComparisonResult)

  const query = useQuery({
    queryKey: ['batch-state'],
    queryFn: getBatchState,
    refetchInterval: (q) => getBatchStateRefetchInterval(q.state.data),
  })

  useEffect(() => {
    if (shouldRefreshCompletedBatch(lastSettledBatchToken, query.data)) {
      if (!query.data) {
        return
      }
      const completionToken = buildBatchCompletionToken(query.data)
      setLastSettledBatchToken(completionToken)
      const completedBatchJobId = query.data.batch_job_id ?? null
      const isCurrentSessionBatch = Boolean(pendingBatchJobId && pendingBatchJobId === completedBatchJobId)
      if (isCurrentSessionBatch) {
        recordCompletedBatchComparison(query.data, setComparisonResult)
        if (shouldHydrateRecentCurrentForBatch(query.data)) {
          void qc.fetchQuery({
            queryKey: ['system-status'],
            queryFn: getSystemStatus,
          }).then((payload) => {
            const current = payload?.recent_results?.current
            if (current?.execution_mode === 'live' && current?.status === 'success') {
              setLastCompletedInference(current)
            }
          }).catch(() => undefined)
        }
      }
      void qc.invalidateQueries({ queryKey: ['snapshot'] })
    }
  }, [
    query.data,
    qc,
    setLastCompletedInference,
    lastSettledBatchToken,
    setLastSettledBatchToken,
    pendingBatchJobId,
    setComparisonResult,
  ])

  return query
}
