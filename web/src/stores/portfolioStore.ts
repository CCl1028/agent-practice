/**
 * 持仓 Store — Zustand
 *
 * API-first: 优先从后端 API 获取数据
 * localStorage: 作为本地缓存和离线降级
 */

import { create } from 'zustand'
import type { Holding, FundEstimation, SortKey, SortDir } from '../types'
import * as api from '../api'

const PORTFOLIO_KEY = 'fund_assistant_portfolio'

function getLocalCache(): Holding[] {
  try {
    return JSON.parse(localStorage.getItem(PORTFOLIO_KEY) || '[]')
  } catch {
    return []
  }
}

function saveLocalCache(holdings: Holding[]) {
  localStorage.setItem(PORTFOLIO_KEY, JSON.stringify(holdings))
}

interface PortfolioStore {
  holdings: Holding[]
  estimationCache: Record<string, FundEstimation>
  sortKey: SortKey
  sortDir: SortDir
  loading: boolean

  // Actions
  loadPortfolio: () => Promise<void>
  refreshNav: (holdings?: Holding[]) => Promise<void>
  loadEstimation: (holdings?: Holding[]) => Promise<void>
  setHoldings: (holdings: Holding[]) => void
  saveAndSync: (holdings: Holding[]) => void
  deleteHolding: (fundCode: string) => Promise<void>
  setSort: (key: SortKey) => void
}

export const usePortfolioStore = create<PortfolioStore>((set, get) => ({
  holdings: [],
  estimationCache: {},
  sortKey: 'time',
  sortDir: 'desc',
  loading: false,

  loadPortfolio: async () => {
    // 先用 localStorage 快速渲染
    const cached = getLocalCache()
    if (cached.length > 0) {
      set({ holdings: cached })
    }

    // 然后从 API 获取最新
    try {
      const data = await api.refreshPortfolioNav(cached.length > 0 ? cached : getLocalCache())
      if (data.holdings?.length > 0) {
        set({ holdings: data.holdings })
        saveLocalCache(data.holdings)
      }
    } catch {
      // API 失败，使用 localStorage 缓存
    }
  },

  refreshNav: async (h?: Holding[]) => {
    const holdings = h || get().holdings
    if (holdings.length === 0) return
    try {
      const data = await api.refreshPortfolioNav(holdings)
      if (data.holdings?.length > 0) {
        // 合并更新
        const localMap: Record<string, Holding> = {}
        for (const item of get().holdings) localMap[item.fund_code] = item
        for (const item of data.holdings) {
          if (item.fund_code && localMap[item.fund_code]) {
            localMap[item.fund_code] = { ...localMap[item.fund_code], ...item }
          }
        }
        const updated = Object.values(localMap)
        set({ holdings: updated })
        saveLocalCache(updated)
      }
    } catch {
      // silent
    }
  },

  loadEstimation: async (h?: Holding[]) => {
    const holdings = h || get().holdings
    if (holdings.length === 0) return
    try {
      const data = await api.fetchEstimation(holdings)
      const cache: Record<string, FundEstimation> = {}
      for (const f of data.funds) cache[f.fund_code] = f
      set((s) => ({ estimationCache: { ...s.estimationCache, ...cache } }))
    } catch {
      // silent
    }
  },

  setHoldings: (holdings) => {
    set({ holdings })
    saveLocalCache(holdings)
  },

  saveAndSync: (holdings) => {
    set({ holdings })
    saveLocalCache(holdings)
  },

  deleteHolding: async (fundCode) => {
    const filtered = get().holdings.filter((h) => h.fund_code !== fundCode)
    set({ holdings: filtered })
    saveLocalCache(filtered)
    try {
      await fetch(`/api/portfolio/${fundCode}`, {
        method: 'DELETE',
        headers: api.getApiToken() ? { Authorization: `Bearer ${api.getApiToken()}` } : {},
      })
    } catch {
      // silent — local state already updated
    }
  },

  setSort: (key) => {
    const { sortKey, sortDir } = get()
    if (sortKey === key) {
      set({ sortDir: sortDir === 'desc' ? 'asc' : 'desc' })
    } else {
      set({ sortKey: key, sortDir: 'desc' })
    }
  },
}))
