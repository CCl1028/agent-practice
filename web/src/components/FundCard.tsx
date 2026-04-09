import { useState } from 'react'
import type { Holding, FundEstimation, Transaction, InvestPlan } from '../types'
import { getTransactions } from '../store'
import { formatFrequency } from '../utils'

interface FundCardProps {
  holding: Holding
  estimation?: FundEstimation
  transactions: Transaction[]
  investPlan?: InvestPlan
  onBuy: (code: string) => void
  onSell: (code: string) => void
  onInvest: (code: string) => void
  onDelete: (code: string) => void
}

export default function FundCard({
  holding: h,
  estimation,
  transactions,
  investPlan,
  onBuy,
  onSell,
  onInvest,
  onDelete,
}: FundCardProps) {
  const [selected, setSelected] = useState(false)
  const [txExpanded, setTxExpanded] = useState(false)
  const [txShowAll, setTxShowAll] = useState(false)

  const cost = h.total_cost || h.cost || 0
  const mv = h.market_value || cost
  const ratio = h.profit_ratio || 0
  const shares = h.total_shares || 0
  const avgNav = h.avg_nav || 0
  const profit = mv - cost
  const profitSign = profit >= 0 ? '+' : ''
  const ratioSign = ratio >= 0 ? '+' : ''
  const profitColor =
    profit > 0
      ? 'var(--red)'
      : profit < 0
        ? 'var(--green)'
        : 'var(--text-secondary)'
  const hasProfit = ratio || (profit && cost)

  const txCount =
    h.transaction_count || transactions.length

  // Estimation rendering
  const renderEstimation = () => {
    if (!estimation || estimation.est_change === null || estimation.est_change === undefined) return null
    if (estimation.est_time === '暂无数据') {
      return (
        <span className="fund-est flat">
          <span className="fund-est-label">暂无估值数据</span>
        </span>
      )
    }
    const cls =
      estimation.est_change > 0.05
        ? 'up'
        : estimation.est_change < -0.05
          ? 'down'
          : 'flat'
    const sign = estimation.est_change > 0 ? '+' : ''

    if (estimation.is_live) {
      return (
        <span className={`fund-est ${cls}`}>
          <span className="fund-est-label">盘中估值</span>{' '}
          {sign}{estimation.est_change.toFixed(2)}%
          {estimation.est_time && (
            <span className="fund-est-time">{estimation.est_time}</span>
          )}
        </span>
      )
    }
    return (
      <span className={`fund-est ${cls}`}>
        <span className="fund-est-label">
          {estimation.est_time || '上日收盘'}
        </span>{' '}
        {sign}{estimation.est_change.toFixed(2)}%
      </span>
    )
  }

  // Transaction list
  const txList = transactions
  const displayTx = txShowAll ? txList : txList.slice(0, 5)

  const renderTxItem = (t: Transaction) => {
    const d = new Date(t.created_at)
    const dateStr =
      (d.getMonth() + 1).toString().padStart(2, '0') +
      '-' +
      d.getDate().toString().padStart(2, '0')
    const srcLabel = t.source === 'auto_invest' ? '定投' : '手动'
    const typeCls = t.type === 'buy' ? 'tx-type-buy' : 'tx-type-sell'
    const typeLabel = t.type === 'buy' ? '买入' : '卖出'

    return (
      <div className="tx-item" key={t.id}>
        <span className="tx-date">{dateStr}</span>
        <span className="tx-source" style={{ fontSize: 10, padding: '1px 5px', borderRadius: 4, background: 'var(--bg)' }}>{srcLabel}</span>
        <span className={typeCls}>
          {typeLabel} ¥{t.amount}
        </span>
        <span style={{ color: 'var(--text-secondary)' }}>
          {t.nav ? t.nav.toFixed(4) : '-'}
        </span>
      </div>
    )
  }

  return (
    <div
      className={`fund-card${selected ? ' selected' : ''}`}
      onClick={() => setSelected(!selected)}
    >
      <div className="fund-card-left">
        <div className="fund-header">
          <div>
            <span className="fund-name">{h.fund_name || '未知'}</span>{' '}
            <span className="fund-code">{h.fund_code || ''}</span>
          </div>
        </div>
        <div className="fund-reason">
          {cost ? `投入 ¥${cost.toLocaleString()}` : ''}
          {mv !== cost ? ` → 市值 ¥${mv.toLocaleString()}` : ''}
        </div>
        {shares > 0 && (
          <div className="fund-reason" style={{ marginTop: 2 }}>
            持有 {shares.toFixed(2)} 份 · 均价 {avgNav.toFixed(4)}
          </div>
        )}
        <div>{renderEstimation()}</div>
        {investPlan && (
          <div className="fund-invest-tag">
            定投中 · {formatFrequency(investPlan)} ¥{investPlan.amount}
          </div>
        )}
        <div className="fund-actions">
          <button
            className="fund-action-btn buy"
            onClick={(e) => {
              e.stopPropagation()
              onBuy(h.fund_code)
            }}
          >
            加仓
          </button>
          <button
            className="fund-action-btn sell"
            onClick={(e) => {
              e.stopPropagation()
              onSell(h.fund_code)
            }}
          >
            减仓
          </button>
          <button
            className="fund-action-btn invest"
            onClick={(e) => {
              e.stopPropagation()
              onInvest(h.fund_code)
            }}
          >
            定投
          </button>
          <button
            className="fund-action-btn delete"
            onClick={(e) => {
              e.stopPropagation()
              onDelete(h.fund_code)
            }}
          >
            删除
          </button>
        </div>
        {txCount > 0 && (
          <span
            className="tx-toggle"
            onClick={(e) => {
              e.stopPropagation()
              setTxExpanded(!txExpanded)
              setTxShowAll(false)
            }}
          >
            {txExpanded ? '收起记录' : `交易记录 ${txCount}笔`}
          </span>
        )}
        {txExpanded && (
          <div className="tx-list">
            {displayTx.map(renderTxItem)}
            {txList.length > 5 && !txShowAll && (
              <div style={{ textAlign: 'center', marginTop: 6 }}>
                <span
                  className="tx-toggle"
                  onClick={(e) => {
                    e.stopPropagation()
                    setTxShowAll(true)
                  }}
                >
                  查看全部 {txList.length} 笔
                </span>
              </div>
            )}
          </div>
        )}
      </div>
      {hasProfit ? (
        <div className="fund-card-right">
          {ratio ? (
            <div className="fund-profit-ratio" style={{ color: profitColor }}>
              {ratioSign}
              {ratio}%
            </div>
          ) : null}
          {profit && cost ? (
            <div className="fund-profit-amount" style={{ color: profitColor }}>
              {profitSign}
              {profit.toFixed(2)}元
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
