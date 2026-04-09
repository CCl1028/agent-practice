/**
 * localStorage helpers — portfolio, config, transactions, invest plans
 */

import type { Holding, Transaction, InvestPlan } from './types'

const PORTFOLIO_KEY = 'fund_assistant_portfolio'
const CONFIG_KEY = 'fund_assistant_config'
const TX_KEY = 'fund_assistant_transactions'
const INVEST_KEY = 'fund_assistant_auto_invest'

// ---- Config ----

export function getLocalConfig(): Record<string, string> {
  try {
    const data = localStorage.getItem(CONFIG_KEY)
    return data ? JSON.parse(data) : {}
  } catch {
    return {}
  }
}

export function saveLocalConfig(config: Record<string, string>): void {
  try {
    localStorage.setItem(CONFIG_KEY, JSON.stringify(config))
  } catch (e) {
    console.error('Failed to save config:', e)
  }
}

export function getConfigValue(key: string): string {
  return getLocalConfig()[key] || ''
}

export function setConfigValue(key: string, value: string): void {
  const config = getLocalConfig()
  if (value) {
    config[key] = value
  } else {
    delete config[key]
  }
  saveLocalConfig(config)
}

export function getPushConfig(): Record<string, string> {
  const cfg = getLocalConfig()
  const push: Record<string, string> = {}
  if (cfg.BARK_URL) push.BARK_URL = cfg.BARK_URL
  if (cfg.SERVERCHAN_KEY) push.SERVERCHAN_KEY = cfg.SERVERCHAN_KEY
  if (cfg.WECOM_WEBHOOK_URL) push.WECOM_WEBHOOK_URL = cfg.WECOM_WEBHOOK_URL
  return push
}

export function getAIConfig(): Record<string, string> {
  const cfg = getLocalConfig()
  const ai: Record<string, string> = {}
  if (cfg.OPENAI_API_KEY) ai.OPENAI_API_KEY = cfg.OPENAI_API_KEY
  if (cfg.OPENAI_BASE_URL) ai.OPENAI_BASE_URL = cfg.OPENAI_BASE_URL
  return ai
}

export function saveAIConfig(aiConfig: { apiKey: string; baseUrl: string }): void {
  const cfg = getLocalConfig()
  if (aiConfig.apiKey) {
    cfg.OPENAI_API_KEY = aiConfig.apiKey
  } else {
    delete cfg.OPENAI_API_KEY
  }
  if (aiConfig.baseUrl) {
    cfg.OPENAI_BASE_URL = aiConfig.baseUrl
  } else {
    delete cfg.OPENAI_BASE_URL
  }
  saveLocalConfig(cfg)
}

export function savePushConfig(pushConfig: { serverChanKey: string; barkKey: string }): void {
  const cfg = getLocalConfig()
  if (pushConfig.serverChanKey) {
    cfg.SERVERCHAN_KEY = pushConfig.serverChanKey
  } else {
    delete cfg.SERVERCHAN_KEY
  }
  if (pushConfig.barkKey) {
    cfg.BARK_URL = pushConfig.barkKey
  } else {
    delete cfg.BARK_URL
  }
  saveLocalConfig(cfg)
}

// ---- Portfolio ----

export function getLocalPortfolio(): Holding[] {
  try {
    const data = localStorage.getItem(PORTFOLIO_KEY)
    return data ? JSON.parse(data) : []
  } catch (e) {
    console.error('Failed to read portfolio:', e)
    return []
  }
}

export function saveLocalPortfolio(holdings: Holding[]): void {
  try {
    localStorage.setItem(PORTFOLIO_KEY, JSON.stringify(holdings))
  } catch (e) {
    console.error('Failed to save portfolio:', e)
  }
}

// ---- Transactions ----

export function getTransactions(): Transaction[] {
  try {
    return JSON.parse(localStorage.getItem(TX_KEY) || '[]')
  } catch {
    return []
  }
}

export function saveTransactions(txs: Transaction[]): void {
  localStorage.setItem(TX_KEY, JSON.stringify(txs))
}

export function addTransaction(tx: Transaction): void {
  const txs = getTransactions()
  txs.unshift(tx) // newest first
  saveTransactions(txs)
}

// ---- Invest Plans ----

export function getInvestPlans(): InvestPlan[] {
  try {
    return JSON.parse(localStorage.getItem(INVEST_KEY) || '[]')
  } catch {
    return []
  }
}

export function saveInvestPlans(plans: InvestPlan[]): void {
  localStorage.setItem(INVEST_KEY, JSON.stringify(plans))
}

// ---- Recalculate holding from transactions ----

export function recalcHolding(
  fundCode: string,
): { totalShares: number; totalCost: number; avgNav: number } {
  const txs = getTransactions().filter((t) => t.fund_code === fundCode)
  let totalShares = 0
  let totalCost = 0

  // Process in chronological order
  const sorted = [...txs].reverse()
  for (const t of sorted) {
    if (t.type === 'buy') {
      totalShares += t.shares || 0
      totalCost += t.amount || 0
    } else if (t.type === 'sell') {
      const sellShares = t.shares || 0
      if (totalShares > 0) {
        const costPerShare = totalCost / totalShares
        totalCost -= costPerShare * sellShares
        totalShares -= sellShares
      }
    }
  }
  totalShares = Math.max(0, totalShares)
  totalCost = Math.max(0, totalCost)
  const avgNav = totalShares > 0 ? totalCost / totalShares : 0

  // Update holding in localStorage
  const holdings = getLocalPortfolio()
  const h = holdings.find((x) => x.fund_code === fundCode)
  if (h) {
    h.total_shares = Math.round(totalShares * 100) / 100
    h.total_cost = Math.round(totalCost * 100) / 100
    h.avg_nav = Math.round(avgNav * 10000) / 10000
    h.cost = h.total_cost
    h.cost_nav = h.avg_nav
    h.transaction_count = txs.length
    saveLocalPortfolio(holdings)
  }
  return { totalShares, totalCost, avgNav }
}
