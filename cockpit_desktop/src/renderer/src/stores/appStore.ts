import { create } from 'zustand'

type AppState = {
  appTitle: string
  activeJobId: string | null
  chinaTheater: boolean
}

type AppActions = {
  setActiveJobId: (id: string | null) => void
  setChinaTheater: (v: boolean) => void
}

export const useAppStore = create<AppState & AppActions>()((set) => ({
  appTitle: '飞腾多核弱网安全语义视觉回传 · 座舱演示',
  activeJobId: null,
  chinaTheater: false,
  setActiveJobId: (id) => set({ activeJobId: id }),
  setChinaTheater: (v) => set({ chinaTheater: v }),
}))
