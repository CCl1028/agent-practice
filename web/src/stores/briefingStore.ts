/**
 * 简报 Store — Zustand
 * 支持 SSE 流式生成（显示进度）和传统一次性生成
 */

import { create } from 'zustand'
import type { Briefing } from '../types'
import * as api from '../api'
import { usePortfolioStore } from './portfolioStore'

interface BriefingStore {
  briefing: Briefing | null
  loading: boolean
  error: string | null
  pushEnabled: boolean
  progress: string | null  // SSE 进度消息

  generate: () => Promise<void>
  generateStream: () => Promise<void>
  togglePush: () => void
  reset: () => void
}

export const useBriefingStore = create<BriefingStore>((set, get) => ({
  briefing: null,
  loading: false,
  error: null,
  pushEnabled: true,
  progress: null,

  generate: async () => {
    const holdings = usePortfolioStore.getState().holdings
    if (holdings.length === 0) return

    set({ loading: true, error: null, progress: null })
    try {
      const { pushEnabled } = get()
      const data = await api.fetchBriefing(holdings, pushEnabled)
      set({ briefing: data.raw })
    } catch (e: unknown) {
      set({ error: e instanceof Error ? e.message : String(e) })
    } finally {
      set({ loading: false, progress: null })
    }
  },

  generateStream: async () => {
    const holdings = usePortfolioStore.getState().holdings
    if (holdings.length === 0) return

    set({ loading: true, error: null, progress: '准备中...' })
    try {
      await api.streamBriefing(
        holdings,
        (event) => set({ progress: event.message }),
        (data) => set({ briefing: data.raw, loading: false, progress: null }),
        (errMsg) => set({ error: errMsg, loading: false, progress: null }),
      )
    } catch (e: unknown) {
      set({ error: e instanceof Error ? e.message : String(e), loading: false, progress: null })
    }
  },

  togglePush: () => set((s) => ({ pushEnabled: !s.pushEnabled })),
  reset: () => set({ briefing: null, error: null, progress: null }),
}))
