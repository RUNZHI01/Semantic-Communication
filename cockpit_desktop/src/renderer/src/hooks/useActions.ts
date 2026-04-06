import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  postProbeBoard,
  postRunInference,
  postRunBaseline,
  postInjectFault,
  postRecover,
  postLinkDirectorProfile,
  postBoardAccess,
  postJobManifestGatePreview,
  postRunInferenceBatch,
} from '../api/client'
import { useAppStore } from '../stores/appStore'

function useInvalidateOnSuccess() {
  const qc = useQueryClient()
  return () => {
    void qc.invalidateQueries({ queryKey: ['system-status'] })
    void qc.invalidateQueries({ queryKey: ['snapshot'] })
    void qc.invalidateQueries({ queryKey: ['aircraft-position'] })
  }
}

export function useProbeBoard() {
  const inv = useInvalidateOnSuccess()
  return useMutation({ mutationFn: postProbeBoard, onSuccess: inv })
}

export function useRunInference() {
  const inv = useInvalidateOnSuccess()
  const setActiveJobId = useAppStore((s) => s.setActiveJobId)
  const setLastCompletedInference = useAppStore((s) => s.setLastCompletedInference)
  return useMutation({
    mutationFn: ({ imageIndex, variant }: { imageIndex?: number; variant?: string }) =>
      postRunInference(imageIndex, variant),
    onSuccess: (data) => {
      inv()
      // ML-KEM 同步完成时 request_state=completed，直接持久化结果
      if (data.request_state === 'completed') {
        setLastCompletedInference(data)
      }
      if (data.job_id) setActiveJobId(data.job_id)
    },
  })
}

export function useRunBaseline() {
  const inv = useInvalidateOnSuccess()
  const setActiveJobId = useAppStore((s) => s.setActiveJobId)
  return useMutation({
    mutationFn: ({ imageIndex }: { imageIndex?: number }) => postRunBaseline(imageIndex),
    onSuccess: (data) => {
      inv()
      if (data.job_id) setActiveJobId(data.job_id)
    },
  })
}

export function useInjectFault() {
  const inv = useInvalidateOnSuccess()
  return useMutation({
    mutationFn: (faultType: string) => postInjectFault(faultType),
    onSuccess: inv,
  })
}

export function useRecover() {
  const inv = useInvalidateOnSuccess()
  return useMutation({ mutationFn: postRecover, onSuccess: inv })
}

export function useSwitchLinkProfile() {
  const inv = useInvalidateOnSuccess()
  return useMutation({
    mutationFn: (profileId: string) => postLinkDirectorProfile(profileId),
    onSuccess: inv,
  })
}

export function useSetBoardAccess() {
  const inv = useInvalidateOnSuccess()
  return useMutation({
    mutationFn: postBoardAccess,
    onSuccess: inv,
  })
}

export function useGatePreview() {
  const inv = useInvalidateOnSuccess()
  return useMutation({
    mutationFn: (variant: string) => postJobManifestGatePreview(variant),
    onSuccess: inv,
  })
}

export function useRunInferenceBatch() {
  const inv = useInvalidateOnSuccess()
  return useMutation({
    mutationFn: ({ count }: { count?: number } = {}) => postRunInferenceBatch(count ?? 300),
    onSuccess: inv,
  })
}
