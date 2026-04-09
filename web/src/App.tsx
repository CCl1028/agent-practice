import { useState, useEffect, useCallback } from 'react'
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

// import Header from './components/Header' // 暂时禁用
import TabBar, { type TabKey } from './components/TabBar'
import BottomInputBar from './components/BottomInputBar'
import TradeDrawer from './components/TradeDrawer'
import InvestDrawer from './components/InvestDrawer'
import ConfirmDrawer from './components/ConfirmDrawer'
import Toast from './components/Toast'

import PortfolioPage from './pages/PortfolioPage'
import BriefingPage from './pages/BriefingPage'
import DiagnosisPage from './pages/DiagnosisPage'
import ProfilePage from './pages/ProfilePage'

export default function App() {
  // ---- State ----
  const [activeTab, setActiveTab] = useState<TabKey>('portfolio')
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
  const [tradeOpen, setTradeOpen] = useState(false)
  const [tradeType, setTradeType] = useState<'buy' | 'sell'>('buy')
  const [tradeHolding, setTradeHolding] = useState<Holding | null>(null)
  const [investOpen, setInvestOpen] = useState(false)
  const [investHolding, setInvestHolding] = useState<Holding | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [confirmHoldings, setConfirmHoldings] = useState<Holding[]>([])
  const [confirmSource, setConfirmSource] = useState<'screenshot' | 'text' | ''>('')
  const [imageAnalyzing, setImageAnalyzing] = useState(false)

  const { toast, showToast } = useToast()

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
  const handleSendFile = async (file: File) => {
    setInputDisabled(true)
    setImageAnalyzing(true)
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
      setImageAnalyzing(false)
    }
  }

  // 手动添加持仓
  const handleAddHoldings = (newHoldings: Holding[]) => {
    if (newHoldings.length === 0) return
    
    const existing = getLocalPortfolio()
    const existingMap: Record<string, Holding> = {}
    for (const f of existing) {
      const key = f.fund_code || f.fund_name || ''
      if (key) existingMap[key] = f
    }
    for (const h of newHoldings) {
      const key = h.fund_code || h.fund_name || ''
      if (key) existingMap[key] = h
    }
    const merged = Object.values(existingMap)
    saveLocalPortfolio(merged)

    showToast(`已添加 ${newHoldings.length} 只基金`, 'success')
    loadPortfolio(true)
    
    // 刷新新基金的估值
    const newCodes = newHoldings.map((h) => h.fund_code).filter(Boolean)
    if (newCodes.length > 0) {
      const newItems = newCodes.map((c) => ({ fund_code: c, fund_name: '' }))
      loadEstimation(newItems)
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

  // ---- All transactions ----
  const allTransactions = getTransactions()

  // ---- Render Page Content ----
  const renderPageContent = () => {
    switch (activeTab) {
      case 'portfolio':
        return (
          <PortfolioPage
            holdings={holdings}
            sortKey={sortKey}
            sortDir={sortDir}
            estimationCache={estimationCache}
            investPlans={investPlans}
            transactions={allTransactions}
            onSort={handleSort}
            onBuy={(code) => openTrade(code, 'buy')}
            onSell={(code) => openTrade(code, 'sell')}
            onInvest={openInvest}
            onDelete={handleDelete}
            onPauseInvest={handlePauseInvest}
            onResumeInvest={handleResumeInvest}
            onStopInvest={handleStopInvest}
          />
        )
      case 'briefing':
        return (
          <BriefingPage
            briefing={briefing}
            loading={briefingLoading}
            error={briefingError}
            pushEnabled={pushEnabled}
            hasHoldings={holdings.length > 0}
            onTogglePush={() => setPushEnabled(!pushEnabled)}
            onGenerate={handleGenerateBriefing}
          />
        )
      case 'diagnosis':
        return <DiagnosisPage />
      case 'profile':
        return (
          <ProfilePage
            showToast={showToast}
          />
        )
      default:
        return null
    }
  }

  return (
    <>
      <div className="app-container">
        {/* Header - 暂时禁用，等后续迭代 */}
        {/* <Header /> */}

        {/* Page Content */}
        <div className="page-wrapper">
          {renderPageContent()}
        </div>
      </div>

      {/* Bottom Input - only show on portfolio page */}
      {activeTab === 'portfolio' && (
        <BottomInputBar
          disabled={inputDisabled}
          onSendFile={handleSendFile}
          onAddHoldings={handleAddHoldings}
        />
      )}

      {/* Tab Bar */}
      <TabBar active={activeTab} onChange={setActiveTab} />

      {/* Drawers */}
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

      {/* Image Analyzing Loading */}
      {imageAnalyzing && (
        <div className="loading-overlay">
          <div className="loading-content">
            <div className="loading-spinner" />
            <div className="loading-text">正在分析图片...</div>
          </div>
        </div>
      )}

      {/* Toast */}
      <Toast
        message={toast.message}
        type={toast.type}
        visible={toast.visible}
      />
    </>
  )
}
