import { useState, useEffect } from 'react'
import type { Holding, InvestFrequency } from '../types'
import { useBodyScrollLock } from '../hooks/useBodyScrollLock'

interface InvestDrawerProps {
  open: boolean
  holding: Holding | null
  onClose: () => void
  onSubmit: (fundCode: string, amount: number, frequency: InvestFrequency, day: number) => void
}

const QUICK_AMOUNTS = [200, 500, 1000, 2000]

function getDayOptions(freq: InvestFrequency) {
  if (freq === 'daily') return []
  if (freq === 'monthly') {
    return Array.from({ length: 28 }, (_, i) => ({
      value: i + 1,
      label: `${i + 1}号`,
    }))
  }
  // weekly / biweekly
  const days = ['周一', '周二', '周三', '周四', '周五']
  return days.map((d, i) => ({ value: i + 1, label: d }))
}

export default function InvestDrawer({
  open,
  holding,
  onClose,
  onSubmit,
}: InvestDrawerProps) {
  useBodyScrollLock(open)
  const [amount, setAmount] = useState('')
  const [frequency, setFrequency] = useState<InvestFrequency>('weekly')
  const [day, setDay] = useState(3)

  useEffect(() => {
    if (open) {
      setAmount('')
      setFrequency('weekly')
      setDay(3)
    }
  }, [open])

  if (!holding) return null

  const amountNum = parseFloat(amount) || 0
  const dayOptions = getDayOptions(frequency)

  const handleFreqChange = (f: InvestFrequency) => {
    setFrequency(f)
    if (f === 'monthly') setDay(15)
    else if (f !== 'daily') setDay(3)
  }

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
          <h3>设置定投 · {holding.fund_name || holding.fund_code}</h3>
          <button className="drawer-close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="drawer-body">
          <div className="trade-form">
            <div className="form-group">
              <label className="form-label">每期金额（元）</label>
              <input
                className="form-input"
                type="number"
                inputMode="decimal"
                placeholder="每期投入金额"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
              <div className="quick-amounts">
                {QUICK_AMOUNTS.map((v) => (
                  <span
                    key={v}
                    className={`quick-amount${amountNum === v ? ' active' : ''}`}
                    onClick={() => setAmount(String(v))}
                  >
                    {v}
                  </span>
                ))}
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">定投频率</label>
              <div className="freq-row">
                <select
                  className="freq-select"
                  value={frequency}
                  onChange={(e) => handleFreqChange(e.target.value as InvestFrequency)}
                >
                  <option value="daily">每天</option>
                  <option value="weekly">每周</option>
                  <option value="biweekly">每两周</option>
                  <option value="monthly">每月</option>
                </select>
                {dayOptions.length > 0 && (
                  <select
                    className="freq-select"
                    value={day}
                    onChange={(e) => setDay(parseInt(e.target.value))}
                  >
                    {dayOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            </div>
            <button
              className="trade-submit invest-btn"
              disabled={amountNum <= 0}
              onClick={() => {
                onSubmit(holding.fund_code, amountNum, frequency, day)
                onClose()
              }}
            >
              确认创建
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
