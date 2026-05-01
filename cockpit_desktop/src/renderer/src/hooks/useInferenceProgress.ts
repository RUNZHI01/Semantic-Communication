import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import type { RunInferenceResponse } from '../api/types'
import { getInferenceProgress } from '../api/client'
import { useAppStore } from '../stores/appStore'
import { shouldFinalizeInferenceJob } from './inferenceStateMachine'

function numericValue(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : undefined
  }
  return undefined
}

function recordComparisonResult(
  payload: RunInferenceResponse,
  setComparisonResult: ReturnType<typeof useAppStore.getState>['setComparisonResult'],
) {
  if (payload.status !== 'success' || payload.execution_mode !== 'live') {
    return
  }
  const reconstructionMs = payload.timings?.total_ms ?? payload.timings?.payload_ms
  if (reconstructionMs == null) {
    return
  }
  const engine = payload.variant === 'baseline' ? 'pytorch' : payload.variant === 'current' ? 'tvm' : null
  if (!engine) {
    return
  }
  setComparisonResult(engine, {
    engine,
    label: engine === 'pytorch' ? 'PyTorch参考' : 'TVM重建',
    reconstructionMs,
    runMs:
      numericValue(payload.runner_summary?.run_median_ms)
      ?? numericValue(payload.runner_summary?.run_mean_ms)
      ?? payload.timings?.payload_ms
      ?? undefined,
    sampleCount:
      numericValue(payload.runner_summary?.processed_count)
      ?? numericValue(payload.runner_summary?.input_count)
      ?? payload.live_progress?.completed_count,
    updatedAt: Date.now(),
    quality: payload.quality,
  })
}

export function useInferenceProgressPoll() {
  const activeJobId = useAppStore((s) => s.activeJobId)
  const setActiveJobId = useAppStore((s) => s.setActiveJobId)
  const setLastCompletedInference = useAppStore((s) => s.setLastCompletedInference)
  const setComparisonResult = useAppStore((s) => s.setComparisonResult)
  const qc = useQueryClient()

  const query = useQuery({
    queryKey: ['inference-progress', activeJobId],
    queryFn: () => (activeJobId ? getInferenceProgress(activeJobId) : Promise.resolve(null)),
    enabled: !!activeJobId,
    refetchInterval: 2000,
  })

  useEffect(() => {
    if (shouldFinalizeInferenceJob(query.data, activeJobId)) {
      const completedResult = query.data
      if (!completedResult) {
        return
      }
      // Save completed data before clearing active job
      setLastCompletedInference(completedResult)
      recordComparisonResult(completedResult, setComparisonResult)
      setActiveJobId(null)
      void qc.invalidateQueries({ queryKey: ['system-status'] })
      void qc.invalidateQueries({ queryKey: ['snapshot'] })
    }
  }, [query.data, activeJobId, setActiveJobId, setLastCompletedInference, setComparisonResult, qc])

  return query
}
