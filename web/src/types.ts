// ---- Holding / Portfolio ----

export interface Holding {
  fund_code: string
  fund_name: string
  cost?: number
  cost_nav?: number
  current_nav?: number
  market_value?: number
  profit_ratio?: number
  profit_amount?: number
  shares?: number
  total_shares?: number
  total_cost?: number
  avg_nav?: number
  trend_5d?: number[]
  transaction_count?: number
  screenshot_type?: string
  intent?: 'buy' | 'sell' | 'add'
  amount?: number
}

// ---- Briefing ----

export interface BriefingDetail {
  fund_name: string
  fund_code?: string
  action: '加仓' | '减仓' | '观望'
  reason: string
  confidence?: string
}

export interface Briefing {
  summary: string
  details: BriefingDetail[]
  market_note: string
}

export interface BriefingResponse {
  notification: string
  card: string
  report: string
  raw: Briefing
  push_results?: Record<string, boolean | null>
}

// ---- Estimation ----

export interface FundEstimation {
  fund_code: string
  fund_name: string
  est_change: number | null
  est_nav: number | null
  est_time: string | null
  is_live: boolean | null
}

export interface EstimationResponse {
  trading_hours: boolean
  funds: FundEstimation[]
}

// ---- Transaction ----

export interface Transaction {
  id: string
  fund_code: string
  type: 'buy' | 'sell'
  amount: number
  nav: number
  shares: number
  source: 'manual' | 'auto_invest'
  created_at: string
  note?: string
}

// ---- Invest Plan ----

export type InvestFrequency = 'daily' | 'weekly' | 'biweekly' | 'monthly'

export interface InvestPlan {
  id: string
  fund_code: string
  fund_name: string
  amount: number
  frequency: InvestFrequency
  day: number
  status: 'active' | 'paused' | 'stopped'
  created_at: string
  last_executed: string
  total_executed: number
}

// ---- Config ----

export interface ConfigField {
  key: string
  label: string
  placeholder: string
  hint: string
  sensitive: boolean
}

export interface ConfigGroup {
  group: string
  items: ConfigField[]
}

// ---- Sort ----

export type SortKey = 'time' | 'cost' | 'profit_ratio' | 'profit' | 'today'
export type SortDir = 'asc' | 'desc'

// ---- Version ----

export interface VersionInfo {
  version: string
  codename?: string
  build_time?: string
  git_commit?: string
}

// ---- Push ----

export interface PushResults {
  bark?: boolean | null
  serverchan?: boolean | null
  wecom?: boolean | null
}

// ---- Log ----

export interface LogEntry {
  ts: string
  level: string
  msg: string
}
