import type { Holding, FundEstimation, SortKey, SortDir, InvestPlan, Transaction } from '../types'
import SortBar from '../components/SortBar'
import FundCard from '../components/FundCard'
import InvestList from '../components/InvestList'

interface PortfolioPageProps {
  holdings: Holding[]
  sortKey: SortKey
  sortDir: SortDir
  estimationCache: Record<string, FundEstimation>
  investPlans: InvestPlan[]
  transactions: Transaction[]
  onSort: (key: SortKey) => void
  onBuy: (code: string) => void
  onSell: (code: string) => void
  onInvest: (code: string) => void
  onDelete: (code: string) => void
  onPauseInvest: (id: string) => void
  onResumeInvest: (id: string) => void
  onStopInvest: (id: string) => void
}

export default function PortfolioPage({
  holdings,
  sortKey,
  sortDir,
  estimationCache,
  investPlans,
  transactions,
  onSort,
  onBuy,
  onSell,
  onInvest,
  onDelete,
  onPauseInvest,
  onResumeInvest,
  onStopInvest,
}: PortfolioPageProps) {
  // 排序逻辑
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

  if (holdings.length === 0) {
    return (
      <div className="page-content">
        <div className="simple-page-header">
          <h1>我的持仓</h1>
        </div>
        <div className="empty-state">
          <div className="empty-state-icon">📊</div>
          <div className="empty-state-text">
            暂无持仓
            <br />
            点击下方添加基金
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="page-content">
      <div className="simple-page-header">
        <h1>我的持仓</h1>
      </div>

      {/* Portfolio Summary */}
      <div className="portfolio-summary">
        <div className="summary-item">
          <div className="summary-label">持仓数量</div>
          <div className="summary-value">{holdings.length}</div>
        </div>
        <div className="summary-item">
          <div className="summary-label">总成本</div>
          <div className="summary-value">
            ¥{holdings.reduce((sum, h) => sum + (h.total_cost || h.cost || 0), 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>
        <div className="summary-item">
          <div className="summary-label">总市值</div>
          <div className="summary-value">
            ¥{holdings.reduce((sum, h) => sum + (h.market_value || h.total_cost || h.cost || 0), 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>
      </div>

      {/* Sort Bar */}
      {holdings.length > 1 && (
        <SortBar sortKey={sortKey} sortDir={sortDir} onSort={onSort} />
      )}

      {/* Fund Cards */}
      {sortedHoldings.map((h) => (
        <FundCard
          key={h.fund_code}
          holding={h}
          estimation={estimationCache[h.fund_code]}
          transactions={transactions.filter((t) => t.fund_code === h.fund_code)}
          investPlan={investPlans.find(
            (p) => p.fund_code === h.fund_code && p.status === 'active'
          )}
          onBuy={onBuy}
          onSell={onSell}
          onInvest={onInvest}
          onDelete={onDelete}
        />
      ))}

      {/* Invest Plans */}
      <InvestList
        plans={investPlans}
        onPause={onPauseInvest}
        onResume={onResumeInvest}
        onStop={onStopInvest}
      />
    </div>
  )
}
