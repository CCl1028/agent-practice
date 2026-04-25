/**
 * 简报 Store — Zustand
 * Phase C: 推送配置已迁移到服务端 .env，前端不再传 pushConfig
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

  generate: () => Promise<void>
  togglePush: () => void
  reset: () => void
}

export const useBriefingStore = create<BriefingStore>((set, get) => ({
  briefing: null,
  loading: false,
  error: null,
  pushEnabled: true,

  generate: async () => {
    const holdings = usePortfolioStore.getState().holdings
    if (holdings.length === 0) return

    set({ loading: true, error: null })
    try {
      const { pushEnabled } = get()
      // 推送配置已在服务端 .env，不需要前端传
      const data = await api.fetchBriefing(holdings, pushEnabled)
      set({ briefing: data.raw })
    } catch (e: unknown) {
      set({ error: e instanceof Error ? e.message : String(e) })
    } finally {
      set({ loading: false })
    }
  },

  togglePush: () => set((s) => ({ pushEnabled: !s.pushEnabled })),
  reset: () => set({ briefing: null, error: null }),
}))
