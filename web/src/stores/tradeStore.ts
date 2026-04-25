/**
 * 交易 & 定投 Store — Zustand
 */

import { create } from 'zustand'
import type { Transaction, InvestPlan, InvestFrequency, Holding } from '../types'

const TX_KEY = 'fund_assistant_transactions'
const INVEST_KEY = 'fund_assistant_auto_invest'

function loadTransactions(): Transaction[] {
  try { return JSON.parse(localStorage.getItem(TX_KEY) || '[]') } catch { return [] }
}

function saveTx(txs: Transaction[]) {
  localStorage.setItem(TX_KEY, JSON.stringify(txs))
}

function loadPlans(): InvestPlan[] {
  try { return JSON.parse(localStorage.getItem(INVEST_KEY) || '[]') } catch { return [] }
}

function savePlans(plans: InvestPlan[]) {
  localStorage.setItem(INVEST_KEY, JSON.stringify(plans))
}

/** 根据交易记录重算持仓 */
function recalcFromTx(fundCode: string, txs: Transaction[]): { total_shares: number; total_cost: number; avg_nav: number } {
  const fundTxs = txs.filter((t) => t.fund_code === fundCode)
  let shares = 0, cost = 0
  for (const t of fundTxs) {
    if (t.type === 'buy') {
      shares += t.shares
      cost += t.amount
    } else {
      if (shares > 0) {
        const costPerShare = cost / shares
        cost -= costPerShare * t.shares
        shares -= t.shares
      }
    }
  }
  shares = Math.max(0, shares)
  cost = Math.max(0, cost)
  return { total_shares: +shares.toFixed(2), total_cost: +cost.toFixed(2), avg_nav: shares > 0 ? +(cost / shares).toFixed(4) : 0 }
}

interface TradeStore {
  transactions: Transaction[]
  investPlans: InvestPlan[]

  // Drawers
  tradeOpen: boolean
  tradeType: 'buy' | 'sell'
  tradeHolding: Holding | null
  investOpen: boolean
  investHolding: Holding | null

  // Actions
  openTrade: (holding: Holding, type: 'buy' | 'sell') => void
  closeTrade: () => void
  submitTrade: (fundCode: string, type: 'buy' | 'sell', amount: number, nav: number, note: string) => { total_shares: number; total_cost: number; avg_nav: number }
  openInvest: (holding: Holding) => void
  closeInvest: () => void
  submitInvest: (fundCode: string, fundName: string, amount: number, frequency: InvestFrequency, day: number) => void
  pauseInvest: (id: string) => void
  resumeInvest: (id: string) => void
  stopInvest: (id: string) => void
  getTransactions: () => Transaction[]
}

export const useTradeStore = create<TradeStore>((set, get) => ({
  transactions: loadTransactions(),
  investPlans: loadPlans(),
  tradeOpen: false,
  tradeType: 'buy',
  tradeHolding: null,
  investOpen: false,
  investHolding: null,

  openTrade: (holding, type) => set({ tradeOpen: true, tradeHolding: holding, tradeType: type }),
  closeTrade: () => set({ tradeOpen: false, tradeHolding: null }),

  submitTrade: (fundCode, type, amount, nav, note) => {
    const tx: Transaction = {
      id: crypto.randomUUID?.() || Date.now().toString(36),
      fund_code: fundCode,
      type,
      amount: Math.round(amount * 100) / 100,
      nav: Math.round(nav * 10000) / 10000,
      shares: Math.round((amount / nav) * 100) / 100,
      source: 'manual',
      created_at: new Date().toISOString(),
      note,
    }
    const txs = [...get().transactions, tx]
    saveTx(txs)
    set({ transactions: txs, tradeOpen: false })
    return recalcFromTx(fundCode, txs)
  },

  openInvest: (holding) => set({ investOpen: true, investHolding: holding }),
  closeInvest: () => set({ investOpen: false, investHolding: null }),

  submitInvest: (fundCode, fundName, amount, frequency, day) => {
    const plan: InvestPlan = {
      id: crypto.randomUUID?.() || Date.now().toString(36),
      fund_code: fundCode,
      fund_name: fundName,
      amount, frequency, day,
      status: 'active',
      created_at: new Date().toISOString(),
      last_executed: '',
      total_executed: 0,
    }
    const plans = [...get().investPlans, plan]
    savePlans(plans)
    set({ investPlans: plans, investOpen: false })
  },

  pauseInvest: (id) => {
    const plans = get().investPlans.map((p) => p.id === id ? { ...p, status: 'paused' as const } : p)
    savePlans(plans)
    set({ investPlans: plans })
  },

  resumeInvest: (id) => {
    const plans = get().investPlans.map((p) => p.id === id ? { ...p, status: 'active' as const } : p)
    savePlans(plans)
    set({ investPlans: plans })
  },

  stopInvest: (id) => {
    const plans = get().investPlans.map((p) => p.id === id ? { ...p, status: 'stopped' as const } : p)
    savePlans(plans)
    set({ investPlans: plans })
  },

  getTransactions: () => get().transactions,
}))
