import { useState, useEffect, useCallback, useRef } from 'react'
import type {
  Holding,
  Briefing,
  FundEstimation,
  SortKey,
  SortDir,
  InvestPlan,
  InvestFrequency,
} from './types'
import * as api from './api'
import {
  getLocalPortfolio,
  saveLocalPortfolio,
  getLocalConfig,
  getPushConfig,
  getAIConfig,
  getTransactions,
  addTransaction,
  getInvestPlans,
  saveInvestPlans,
  recalcHolding,
} from './store'
import { generateId, formatPushResults } from './utils'
import { useToast } from './hooks/useToast'

import Header from './components/Header'
import BriefingArea, { GenerateButton } from './components/BriefingArea'
import SortBar from './components/SortBar'
import FundCard from './components/FundCard'
import BottomInputBar from './components/BottomInputBar'
import SettingsDrawer from './components/SettingsDrawer'
import TradeDrawer from './components/TradeDrawer'
import InvestDrawer from './components/InvestDrawer'
import ConfirmDrawer from './components/ConfirmDrawer'
import InvestList from './components/InvestList'
import Toast from './components/Toast'

export default function App() {
  // ---- State ----
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [briefing, setBriefing] = useState<Briefing | null>(null)
  const [briefingLoading, setBriefingLoading] = useState(false)
  const [briefingError, setBriefingError] = useState<string | null>(null)
  const [pushEnabled, setPushEnabled] = useState(true)
  const [estimationCache, setEstimationCache] = useState<Record<string, FundEstimation>>({})
  const [sortKey, setSortKey] = useState<SortKey>('time')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [inputDisabled, setInputDisabled] = useState(false)
  const [investPlans, setInvestPlans] = useState<InvestPlan[]>([])

  // Drawers
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [tradeOpen, setTradeOpen] = useState(false)
  const [tradeType, setTradeType] = useState<'buy' | 'sell'>('buy')
  const [tradeHolding, setTradeHolding] = useState<Holding | null>(null)
  const [investOpen, setInvestOpen] = useState(false)
  const [investHolding, setInvestHolding] = useState<Holding | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [confirmHoldings, setConfirmHoldings] = useState<Holding[]>([])
  const [confirmSource, setConfirmSource] = useState<'screenshot' | 'text' | ''>('')

  const { toast, showToast } = useToast()
  const scrollRef = useRef<HTMLDivElement>(null)

  // ---- Load data on mount ----
  useEffect(() => {
    loadPortfolio()
    setInvestPlans(getInvestPlans())
  }, [])

  // ---- Portfolio loading ----
  const loadPortfolio = useCallback(
    async (skipEstimation = false) => {
      const h = getLocalPortfolio()
      setHoldings(h)
      if (h.length > 0) {
        refreshNav(h)
        if (!skipEstimation) {
          loadEstimation(h)
        }
      }
    },
    [],
  )

  const refreshNav = async (h: Holding[]) => {
    try {
      const data = await api.refreshPortfolioNav(h)
      if (data.holdings?.length > 0) {
        const localMap: Record<string, Holding> = {}
        for (const item of getLocalPortfolio()) {
          localMap[item.fund_code] = item
        }
        for (const item of data.holdings) {
          if (item.fund_code && localMap[item.fund_code]) {
            localMap[item.fund_code].current_nav = item.current_nav
            localMap[item.fund_code].profit_ratio = item.profit_ratio
            localMap[item.fund_code].market_value = item.market_value
            localMap[item.fund_code].trend_5d = item.trend_5d
          }
        }
        const updated = Object.values(localMap)
        saveLocalPortfolio(updated)
        setHoldings([...updated])
      }
    } catch {
      // silent
    }
  }

  const loadEstimation = async (h: Holding[]) => {
    if (!h.length) return
    try {
      const data = await api.fetchEstimation(h)
      const cache: Record<string, FundEstimation> = {}
      for (const f of data.funds) {
        cache[f.fund_code] = f
      }
      setEstimationCache((prev) => ({ ...prev, ...cache }))
    } catch {
      // silent
    }
  }

  // ---- Sorting ----
  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const sortedHoldings = (() => {
    if (!holdings.length) return holdings
    if (sortKey === 'time') {
      return sortDir === 'asc' ? [...holdings] : [...holdings].reverse()
    }
    const sorted = [...holdings]
    sorted.sort((a, b) => {
      let va = 0,
        vb = 0
      if (sortKey === 'cost') {
        va = a.total_cost || a.cost || 0
        vb = b.total_cost || b.cost || 0
      } else if (sortKey === 'profit_ratio') {
        va = a.profit_ratio || 0
        vb = b.profit_ratio || 0
      } else if (sortKey === 'profit') {
        const costA = a.total_cost || a.cost || 0
        const mvA = a.market_value || costA
        va = mvA - costA
        const costB = b.total_cost || b.cost || 0
        const mvB = b.market_value || costB
        vb = mvB - costB
      } else if (sortKey === 'today') {
        const eA = estimationCache[a.fund_code]
        const eB = estimationCache[b.fund_code]
        va = eA?.est_change != null ? eA.est_change : -9999
        vb = eB?.est_change != null ? eB.est_change : -9999
      }
      return sortDir === 'desc' ? vb - va : va - vb
    })
    return sorted
  })()

  // ---- Briefing ----
  const handleGenerateBriefing = async () => {
    const localHoldings = getLocalPortfolio()
    if (localHoldings.length === 0) {
      showToast('请先添加持仓', 'error')
      return
    }

    setBriefingLoading(true)
    setBriefingError(null)
    setInputDisabled(true)

    try {
      const data = await api.fetchBriefing(
        localHoldings,
        pushEnabled,
        pushEnabled ? getPushConfig() : undefined,
      )
      setBriefing(data.raw)
      if (pushEnabled && data.push_results) {
        const pushMsg = formatPushResults(data.push_results)
        showToast('简报已生成 ' + pushMsg, 'success')
      } else {
        showToast('简报已生成', 'success')
      }
    } catch (e: unknown) {
      setBriefingError(e instanceof Error ? e.message : String(e))
      showToast('生成失败: ' + (e instanceof Error ? e.message : String(e)), 'error')
    } finally {
      setBriefingLoading(false)
      setInputDisabled(false)
    }
  }

  // ---- Input handlers ----
  const handleSendText = async (text: string) => {
    setInputDisabled(true)
    try {
      const config = getLocalConfig()
      const data = await api.parseText(text, config)
      if (data.parsed?.length > 0) {
        let tradeDone = false
        const newHoldings: Holding[] = []

        for (const h of data.parsed) {
          if (h.intent === 'buy' || h.intent === 'sell') {
            const existing = getLocalPortfolio()
            const fund = existing.find(
              (f) => f.fund_code === h.fund_code || f.fund_name === h.fund_name,
            )
            if (fund) {
              let nav = fund.current_nav || 0
              if (!nav) {
                try {
                  const rr = await api.refreshPortfolioNav([
                    { fund_code: fund.fund_code, fund_name: fund.fund_name },
                  ])
                  if (rr.holdings?.[0]) nav = rr.holdings[0].current_nav || 1
                } catch {
                  nav = 1
                }
              }
              const amount = h.amount || h.cost || 0
              if (amount > 0) {
                const tx = {
                  id: generateId(),
                  fund_code: fund.fund_code,
                  type: h.intent as 'buy' | 'sell',
                  amount,
                  nav: Math.round(nav * 10000) / 10000,
                  shares: Math.round((amount / nav) * 100) / 100,
                  source: 'manual' as const,
                  created_at: new Date().toISOString(),
                  note: '自然语言录入',
                }
                addTransaction(tx)
                recalcHolding(fund.fund_code)
                tradeDone = true
              }
            } else {
              showToast(`未找到持仓: ${h.fund_name || h.fund_code}，请先添加`, 'error')
            }
          } else {
            newHoldings.push(h)
          }
        }

        if (tradeDone) {
          showToast('交易操作已完成', 'success')
          loadPortfolio(true)
        }

        if (newHoldings.length > 0) {
          setConfirmHoldings(newHoldings)
          setConfirmSource('text')
          setConfirmOpen(true)
        }
      } else {
        showToast('未识别到基金信息，换个描述试试', 'error')
      }
    } catch (e: unknown) {
      showToast('识别失败: ' + (e instanceof Error ? e.message : String(e)), 'error')
    } finally {
      setInputDisabled(false)
    }
  }

  const handleSendFile = async (file: File) => {
    setInputDisabled(true)
    try {
      const data = await api.parseScreenshot(file, getAIConfig())
      if (data.parsed?.length > 0) {
        setConfirmHoldings(data.parsed)
        setConfirmSource('screenshot')
        setConfirmOpen(true)
      } else {
        showToast('未识别到基金信息，换张截图试试', 'error')
      }
    } catch (e: unknown) {
      showToast('识别失败: ' + (e instanceof Error ? e.message : String(e)), 'error')
    } finally {
      setInputDisabled(false)
    }
  }

  // ---- Confirm save ----
  const handleConfirmSave = (items: Holding[]) => {
    const existing = getLocalPortfolio()
    const existingMap: Record<string, Holding> = {}
    for (const f of existing) {
      const key = f.fund_code || f.fund_name || ''
      if (key) existingMap[key] = f
    }
    for (const h of items) {
      const key = h.fund_code || h.fund_name || ''
      if (key) existingMap[key] = h
    }
    const merged = Object.values(existingMap)
    saveLocalPortfolio(merged)

    const newCodes = items.map((h) => h.fund_code).filter(Boolean)
    showToast(`已保存 ${items.length} 只基金`, 'success')
    loadPortfolio(true)
    // Load estimation for new funds
    if (newCodes.length > 0) {
      const newHoldings = newCodes.map((c) => ({ fund_code: c, fund_name: '' }))
      loadEstimation(newHoldings)
    }
  }

  // ---- Trade ----
  const openTrade = (code: string, type: 'buy' | 'sell') => {
    const h = holdings.find((x) => x.fund_code === code)
    if (!h) return
    setTradeHolding(h)
    setTradeType(type)
    setTradeOpen(true)
  }

  const handleTradeSubmit = (
    fundCode: string,
    type: 'buy' | 'sell',
    amount: number,
    nav: number,
    note: string,
  ) => {
    // Validate sell
    if (type === 'sell') {
      const h = holdings.find((x) => x.fund_code === fundCode)
      const holdShares = h?.total_shares || 0
      if (holdShares <= 0) {
        showToast('当前无持仓可减', 'error')
        return
      }
      const sellShares = amount / nav
      if (sellShares > holdShares) {
        showToast(`赎回份额 ${sellShares.toFixed(2)} 超过持有 ${holdShares.toFixed(2)} 份`, 'error')
        return
      }
    }

    const tx = {
      id: generateId(),
      fund_code: fundCode,
      type,
      amount: Math.round(amount * 100) / 100,
      nav: Math.round(nav * 10000) / 10000,
      shares: Math.round((amount / nav) * 100) / 100,
      source: 'manual' as const,
      created_at: new Date().toISOString(),
      note,
    }
    addTransaction(tx)
    recalcHolding(fundCode)
    showToast(
      `${type === 'buy' ? '加仓' : '减仓'}成功 ${type === 'buy' ? '+' : '-'}¥${amount}`,
      'success',
    )
    loadPortfolio(true)
  }

  // ---- Delete ----
  const handleDelete = (code: string) => {
    const h = holdings.find((x) => x.fund_code === code)
    const name = h ? h.fund_name || code : code
    if (!confirm(`确认删除「${name}」？删除后持仓和交易记录将保留。`)) return
    const filtered = getLocalPortfolio().filter((x) => x.fund_code !== code)
    saveLocalPortfolio(filtered)
    showToast('已删除', 'success')
    loadPortfolio(true)
  }

  // ---- Invest ----
  const openInvest = (code: string) => {
    const h = holdings.find((x) => x.fund_code === code)
    if (!h) return
    const existing = getInvestPlans().find(
      (p) => p.fund_code === code && p.status === 'active',
    )
    if (existing) {
      showToast('该基金已有定投计划，请先暂停或停止现有计划', 'error')
      return
    }
    setInvestHolding(h)
    setInvestOpen(true)
  }

  const handleInvestSubmit = (
    fundCode: string,
    amount: number,
    frequency: InvestFrequency,
    day: number,
  ) => {
    const h = holdings.find((x) => x.fund_code === fundCode)
    const plan: InvestPlan = {
      id: generateId(),
      fund_code: fundCode,
      fund_name: h?.fund_name || fundCode,
      amount,
      frequency,
      day,
      status: 'active',
      created_at: new Date().toISOString(),
      last_executed: '',
      total_executed: 0,
    }
    const plans = getInvestPlans()
    plans.push(plan)
    saveInvestPlans(plans)
    setInvestPlans([...plans])
    showToast('定投计划已创建', 'success')
    loadPortfolio(true)
  }

  const handlePauseInvest = (id: string) => {
    const plans = getInvestPlans()
    const p = plans.find((x) => x.id === id)
    if (p) {
      p.status = 'paused'
      saveInvestPlans(plans)
      setInvestPlans([...plans])
    }
    showToast('定投已暂停', 'success')
    loadPortfolio(true)
  }

  const handleResumeInvest = (id: string) => {
    const plans = getInvestPlans()
    const p = plans.find((x) => x.id === id)
    if (p) {
      p.status = 'active'
      saveInvestPlans(plans)
      setInvestPlans([...plans])
    }
    showToast('定投已恢复', 'success')
    loadPortfolio(true)
  }

  const handleStopInvest = (id: string) => {
    const plans = getInvestPlans()
    const p = plans.find((x) => x.id === id)
    if (p) {
      p.status = 'stopped'
      saveInvestPlans(plans)
      setInvestPlans([...plans])
    }
    showToast('定投已停止', 'success')
    loadPortfolio(true)
  }

  // ---- All transactions for fund cards ----
  const allTransactions = getTransactions()

  return (
    <>
      <div className="scroll-wrapper" ref={scrollRef}>
        <div className="container">
          <Header onOpenSettings={() => setSettingsOpen(true)} />

          {/* Briefing */}
          <div>
            <BriefingArea
              briefing={briefing}
              loading={briefingLoading}
              error={briefingError}
            />
          </div>

          {/* Generate Button */}
          <GenerateButton
            loading={briefingLoading}
            pushEnabled={pushEnabled}
            onTogglePush={() => setPushEnabled(!pushEnabled)}
            onGenerate={handleGenerateBriefing}
          />

          {/* Portfolio */}
          {holdings.length > 0 && (
            <>
              <div className="section-title">我的持仓</div>
              {holdings.length > 1 && (
                <SortBar
                  sortKey={sortKey}
                  sortDir={sortDir}
                  onSort={handleSort}
                />
              )}
              {sortedHoldings.map((h) => (
                <FundCard
                  key={h.fund_code}
                  holding={h}
                  estimation={estimationCache[h.fund_code]}
                  transactions={allTransactions.filter(
                    (t) => t.fund_code === h.fund_code,
                  )}
                  investPlan={investPlans.find(
                    (p) =>
                      p.fund_code === h.fund_code && p.status === 'active',
                  )}
                  onBuy={(code) => openTrade(code, 'buy')}
                  onSell={(code) => openTrade(code, 'sell')}
                  onInvest={openInvest}
                  onDelete={handleDelete}
                />
              ))}
            </>
          )}

          {/* Invest Plans */}
          <InvestList
            plans={investPlans}
            onPause={handlePauseInvest}
            onResume={handleResumeInvest}
            onStop={handleStopInvest}
          />
        </div>
      </div>

      {/* Bottom Input */}
      <BottomInputBar
        disabled={inputDisabled}
        onSendText={handleSendText}
        onSendFile={handleSendFile}
      />

      {/* Drawers */}
      <SettingsDrawer
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        showToast={showToast}
      />

      <TradeDrawer
        open={tradeOpen}
        type={tradeType}
        holding={tradeHolding}
        onClose={() => setTradeOpen(false)}
        onSubmit={handleTradeSubmit}
      />

      <InvestDrawer
        open={investOpen}
        holding={investHolding}
        onClose={() => setInvestOpen(false)}
        onSubmit={handleInvestSubmit}
      />

      <ConfirmDrawer
        open={confirmOpen}
        holdings={confirmHoldings}
        source={confirmSource}
        onClose={() => {
          setConfirmOpen(false)
          setConfirmHoldings([])
        }}
        onSave={handleConfirmSave}
      />

      {/* Toast */}
      <Toast
        message={toast.message}
        type={toast.type}
        visible={toast.visible}
      />
    </>
  )
}
