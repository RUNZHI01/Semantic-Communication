import { create } from 'zustand'
import type { RunInferenceResponse } from '../api/types'

type AppState = {
  appTitle: string
  activeJobId: string | null
  /** Last completed inference result — persists until next run or manual clear */
  lastCompletedInference: RunInferenceResponse | null
  chinaTheater: boolean
}

type AppActions = {
  setActiveJobId: (id: string | null) => void
  setLastCompletedInference: (data: RunInferenceResponse | null) => void
  setChinaTheater: (v: boolean) => void
}

export const useAppStore = create<AppState & AppActions>()((set) => ({
  appTitle: '飞腾多核弱网安全语义视觉回传 · 座舱演示',
  activeJobId: null,
  lastCompletedInference: null,
  chinaTheater: false,
  setActiveJobId: (id) => set({ activeJobId: id }),
  setLastCompletedInference: (data) => set({ lastCompletedInference: data }),
  setChinaTheater: (v) => set({ chinaTheater: v }),
}))
