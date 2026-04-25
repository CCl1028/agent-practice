/**
 * 简报 Store — Zustand
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
      const pushConfig = pushEnabled ? getPushConfig() : undefined
      const data = await api.fetchBriefing(holdings, pushEnabled, pushConfig)
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

/** 从 localStorage 读取推送配置 */
function getPushConfig(): Record<string, string> {
  try {
    const cfg = JSON.parse(localStorage.getItem('fund_assistant_config') || '{}')
    const push: Record<string, string> = {}
    for (const [k, v] of Object.entries(cfg)) {
      if (typeof v === 'string' && (k.includes('BARK') || k.includes('SERVERCHAN') || k.includes('WECOM'))) {
        push[k] = v
      }
    }
    return push
  } catch {
    return {}
  }
}
