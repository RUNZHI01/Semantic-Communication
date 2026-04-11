import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { getBatchState } from '../api/client'

export function useBatchStatePoll() {
  const qc = useQueryClient()
  const lastStatusRef = useRef<string | null>(null)

  const query = useQuery({
    queryKey: ['batch-state'],
    queryFn: getBatchState,
    refetchInterval: 2000,
  })

  useEffect(() => {
    const status = query.data?.status ?? null
    if (status === 'done' && lastStatusRef.current !== 'done') {
      void qc.invalidateQueries({ queryKey: ['system-status'] })
      void qc.invalidateQueries({ queryKey: ['snapshot'] })
    }
    lastStatusRef.current = status
  }, [query.data?.status, qc])

  return query
}
