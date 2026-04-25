import { useEffect, useState } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import type { Holding } from './types'
import * as api from './api'
import { usePortfolioStore } from './stores/portfolioStore'
import { useBriefingStore } from './stores/briefingStore'
import { useTradeStore } from './stores/tradeStore'
import { useToast } from './hooks/useToast'
import { formatPushResults } from './utils'

import Header from './components/Header'
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
  const location = useLocation()
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [confirmHoldings, setConfirmHoldings] = useState<Holding[]>([])
  const [confirmSource, setConfirmSource] = useState<'screenshot' | 'text' | ''>('')
  const [imageAnalyzing, setImageAnalyzing] = useState(false)
  const [imageProgress, setImageProgress] = useState({ current: 0, total: 0 })
  const [inputDisabled, setInputDisabled] = useState(false)

  const { toast, showToast } = useToast()

  // Zustand stores
  const portfolio = usePortfolioStore()
  const briefing = useBriefingStore()
  const trade = useTradeStore()

  // Load on mount
  useEffect(() => {
    portfolio.loadPortfolio().then(() => portfolio.loadEstimation())
  }, [])

  // ---- Input handlers ----
  const handleSendFile = async (files: File[]) => {
    setInputDisabled(true)
    setImageAnalyzing(true)
    setImageProgress({ current: 0, total: files.length })

    const allParsed: Holding[] = []
    let hasError = false

    try {
      const aiConfig = {} // 后端从 .env 读取 AI 配置
      for (let i = 0; i < files.length; i++) {
        setImageProgress({ current: i + 1, total: files.length })
        try {
          const data = await api.parseScreenshot(files[i], aiConfig)
          if (data.parsed?.length > 0) allParsed.push(...data.parsed)
        } catch { hasError = true }
      }

      if (allParsed.length > 0) {
        const seen = new Set<string>()
        const deduped = allParsed.filter((h) => {
          const key = h.fund_code || h.fund_name || ''
          if (key && !seen.has(key)) { seen.add(key); return true }
          return false
        })
        setConfirmHoldings(deduped)
        setConfirmSource('screenshot')
        setConfirmOpen(true)
      } else {
        showToast(hasError ? '识别失败，请检查网络后重试' : '未识别到基金信息', 'error')
      }
    } finally {
      setInputDisabled(false)
      setImageAnalyzing(false)
      setImageProgress({ current: 0, total: 0 })
    }
  }

  const handleAddHoldings = (newHoldings: Holding[]) => {
    if (!newHoldings.length) return
    const map: Record<string, Holding> = {}
    for (const h of portfolio.holdings) map[h.fund_code || h.fund_name] = h
    for (const h of newHoldings) map[h.fund_code || h.fund_name] = h
    portfolio.saveAndSync(Object.values(map))
    showToast(`已添加 ${newHoldings.length} 只基金`, 'success')
    portfolio.loadEstimation(newHoldings)
  }

  const handleConfirmSave = (items: Holding[]) => {
    handleAddHoldings(items)
    setConfirmOpen(false)
    setConfirmHoldings([])
  }

  const handleGenerateBriefing = async () => {
    if (portfolio.holdings.length === 0) { showToast('请先添加持仓', 'error'); return }
    setInputDisabled(true)
    await briefing.generateStream()
    setInputDisabled(false)
    if (briefing.error) {
      showToast('生成失败: ' + briefing.error, 'error')
    } else {
      showToast('简报已生成', 'success')
    }
  }

  const handleTradeSubmit = (fundCode: string, type: 'buy' | 'sell', amount: number, nav: number, note: string) => {
    if (type === 'sell') {
      const h = portfolio.holdings.find((x) => x.fund_code === fundCode)
      const held = h?.total_shares || 0
      if (held <= 0) { showToast('当前无持仓可减', 'error'); return }
      if (amount / nav > held) { showToast('赎回份额超过持有', 'error'); return }
    }
    const result = trade.submitTrade(fundCode, type, amount, nav, note)
    const updated = portfolio.holdings.map((h) =>
      h.fund_code === fundCode ? { ...h, total_shares: result.total_shares, total_cost: result.total_cost, avg_nav: result.avg_nav } : h,
    )
    portfolio.saveAndSync(updated)
    showToast(`${type === 'buy' ? '加仓' : '减仓'}成功`, 'success')
  }

  const handleDelete = (code: string) => {
    const h = portfolio.holdings.find((x) => x.fund_code === code)
    if (!confirm(`确认删除「${h?.fund_name || code}」？`)) return
    portfolio.deleteHolding(code)
    showToast('已删除', 'success')
  }

  const isPortfolioPage = location.pathname === '/' || location.pathname === ''

  // ---- Render ----
  return (
    <>
      <Header />
      <main className="page-wrapper">
        <Routes>
          <Route
            path="/"
            element={
              <PortfolioPage
                holdings={portfolio.holdings}
                sortKey={portfolio.sortKey}
                sortDir={portfolio.sortDir}
                estimationCache={portfolio.estimationCache}
                investPlans={trade.investPlans}
                transactions={trade.transactions}
                onSort={portfolio.setSort}
                onBuy={(code) => { const h = portfolio.holdings.find((x) => x.fund_code === code); if (h) trade.openTrade(h, 'buy') }}
                onSell={(code) => { const h = portfolio.holdings.find((x) => x.fund_code === code); if (h) trade.openTrade(h, 'sell') }}
                onInvest={(code) => {
                  const h = portfolio.holdings.find((x) => x.fund_code === code)
                  if (!h) return
                  if (trade.investPlans.some((p) => p.fund_code === code && p.status === 'active')) {
                    showToast('该基金已有定投计划', 'error'); return
                  }
                  trade.openInvest(h)
                }}
                onDelete={handleDelete}
                onPauseInvest={trade.pauseInvest}
                onResumeInvest={trade.resumeInvest}
                onStopInvest={trade.stopInvest}
              />
            }
          />
          <Route
            path="/briefing"
            element={
              <BriefingPage
                briefing={briefing.briefing}
                loading={briefing.loading}
                error={briefing.error}
                pushEnabled={briefing.pushEnabled}
                hasHoldings={portfolio.holdings.length > 0}
                progress={briefing.progress}
                onTogglePush={briefing.togglePush}
                onGenerate={handleGenerateBriefing}
              />
            }
          />
          <Route path="/diagnosis" element={<DiagnosisPage />} />
          <Route path="/profile" element={<ProfilePage showToast={showToast} />} />
        </Routes>
      </main>

      {isPortfolioPage && (
        <BottomInputBar disabled={inputDisabled} onSendFile={handleSendFile} onAddHoldings={handleAddHoldings} />
      )}

      <TradeDrawer
        open={trade.tradeOpen} type={trade.tradeType} holding={trade.tradeHolding}
        onClose={trade.closeTrade} onSubmit={handleTradeSubmit}
      />
      <InvestDrawer
        open={trade.investOpen} holding={trade.investHolding}
        onClose={trade.closeInvest}
        onSubmit={(code, amt, freq, day) => {
          const h = portfolio.holdings.find((x) => x.fund_code === code)
          trade.submitInvest(code, h?.fund_name || code, amt, freq, day)
          showToast('定投计划已创建', 'success')
        }}
      />
      <ConfirmDrawer
        open={confirmOpen} holdings={confirmHoldings} source={confirmSource}
        onClose={() => { setConfirmOpen(false); setConfirmHoldings([]) }}
        onSave={handleConfirmSave}
      />

      {imageAnalyzing && (
        <div className="loading-overlay">
          <div className="loading-content">
            <div className="loading-spinner" />
            <div className="loading-text">
              {imageProgress.total > 1 ? `正在分析图片 (${imageProgress.current}/${imageProgress.total})...` : '正在分析图片...'}
            </div>
            {imageProgress.total > 1 && (
              <div className="loading-progress-bar">
                <div className="loading-progress-fill" style={{ width: `${(imageProgress.current / imageProgress.total) * 100}%` }} />
              </div>
            )}
          </div>
        </div>
      )}

      <Toast message={toast.message} type={toast.type} visible={toast.visible} />
    </>
  )
}
