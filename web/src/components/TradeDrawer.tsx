import { useState, useEffect } from 'react'
import type { Holding } from '../types'
import { refreshPortfolioNav } from '../api'

interface TradeDrawerProps {
  open: boolean
  type: 'buy' | 'sell'
  holding: Holding | null
  onClose: () => void
  onSubmit: (fundCode: string, type: 'buy' | 'sell', amount: number, nav: number, note: string) => void
}

const QUICK_AMOUNTS = [500, 1000, 2000, 5000]

export default function TradeDrawer({
  open,
  type,
  holding,
  onClose,
  onSubmit,
}: TradeDrawerProps) {
  const [amount, setAmount] = useState('')
  const [note, setNote] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [nav, setNav] = useState(0)

  useEffect(() => {
    if (open && holding) {
      setAmount('')
      setNote('')
      setError('')
      setNav(holding.current_nav || 0)
      // Try to get latest nav if missing
      if (!holding.current_nav) {
        refreshPortfolioNav([{ fund_code: holding.fund_code, fund_name: holding.fund_name }])
          .then((data) => {
            if (data.holdings?.[0]?.current_nav) {
              setNav(data.holdings[0].current_nav)
            }
          })
          .catch(() => setNav(1))
      }
    }
  }, [open, holding])

  if (!holding) return null

  const amountNum = parseFloat(amount) || 0
  const totalShares = holding.total_shares || 0
  const marketValue = holding.market_value || holding.cost || 0

  const validate = () => {
    if (amountNum <= 0) return false
    if (type === 'sell') {
      if (totalShares <= 0) {
        setError('当前无持仓可减')
        return false
      }
      const sellShares = nav > 0 ? amountNum / nav : 0
      if (sellShares > totalShares) {
        setError(`赎回份额 ${sellShares.toFixed(2)} 超过持有 ${totalShares.toFixed(2)} 份`)
        return false
      }
      if (marketValue > 0 && amountNum > marketValue) {
        setError('金额不能超过当前市值 ¥' + marketValue.toLocaleString())
        return false
      }
    }
    setError('')
    return true
  }

  const handleAmountChange = (val: string) => {
    setAmount(val)
    setError('')
  }

  const handleSubmit = async () => {
    if (!validate()) return
    setSubmitting(true)
    try {
      let finalNav = nav
      if (!finalNav || finalNav <= 0) {
        try {
          const data = await refreshPortfolioNav([{ fund_code: holding.fund_code, fund_name: holding.fund_name }])
          if (data.holdings?.[0]?.current_nav) {
            finalNav = data.holdings[0].current_nav
          } else {
            finalNav = 1
          }
        } catch {
          finalNav = 1
        }
      }
      onSubmit(holding.fund_code, type, amountNum, finalNav, note)
      onClose()
    } finally {
      setSubmitting(false)
    }
  }

  const shares = nav > 0 && amountNum > 0 ? amountNum / nav : 0

  return (
    <>
      <div
        className={`drawer-overlay trade-drawer-overlay${open ? ' open' : ''}`}
        onClick={onClose}
      />
      <div className={`drawer trade-drawer${open ? ' open' : ''}`}>
        <div className="drawer-handle">
          <div className="drawer-handle-bar" />
        </div>
        <div className="drawer-header">
          <h3>
            {type === 'buy' ? '加仓' : '减仓'} · {holding.fund_name || holding.fund_code}
          </h3>
          <button className="drawer-close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="drawer-body">
          <div className="trade-form">
            <div className="form-group">
              <label className="form-label">金额（元）</label>
              <input
                className="form-input"
                type="number"
                inputMode="decimal"
                placeholder="输入金额"
                value={amount}
                onChange={(e) => handleAmountChange(e.target.value)}
              />
              <div className="quick-amounts">
                {QUICK_AMOUNTS.map((v) => (
                  <span
                    key={v}
                    className={`quick-amount${amountNum === v ? ' active' : ''}`}
                    onClick={() => handleAmountChange(String(v))}
                  >
                    {v}
                  </span>
                ))}
              </div>
              {error && <div className="form-error">{error}</div>}
            </div>
            <div className="form-group">
              <label className="form-label">备注（可选）</label>
              <input
                className="form-input"
                type="text"
                placeholder="备注信息"
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            </div>
            <div className="trade-info">
              成交净值：<strong>{nav ? nav.toFixed(4) : '获取中...'}</strong>（最新净值）
              <br />
              {nav > 0 && amountNum > 0 && (
                <>预估份额：<strong>{shares.toFixed(2)}</strong> 份</>
              )}
              {type === 'sell' && (
                <>
                  <br />
                  当前持有：<strong>{totalShares.toFixed(2)}</strong> 份
                  <br />
                  当前市值：<strong>¥{marketValue.toLocaleString()}</strong>
                  {nav > 0 && amountNum > 0 && (
                    <>
                      <br />
                      赎回后剩余：<strong>{Math.max(0, totalShares - shares).toFixed(2)}</strong> 份
                    </>
                  )}
                </>
              )}
            </div>
            <button
              className={`trade-submit ${type === 'buy' ? 'buy-btn' : 'sell-btn'}`}
              disabled={amountNum <= 0 || !!error || submitting}
              onClick={handleSubmit}
            >
              {submitting ? '处理中...' : type === 'buy' ? '确认加仓' : '确认减仓'}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
