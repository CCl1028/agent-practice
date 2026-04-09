import { Calendar } from 'lucide-react'
import type { InvestPlan } from '../types'
import { formatFrequency } from '../utils'

interface InvestListProps {
  plans: InvestPlan[]
  onPause: (id: string) => void
  onResume: (id: string) => void
  onStop: (id: string) => void
}

export default function InvestList({
  plans,
  onPause,
  onResume,
  onStop,
}: InvestListProps) {
  const visiblePlans = plans.filter((p) => p.status !== 'stopped')

  if (visiblePlans.length === 0) return null

  return (
    <>
      <div className="section-title">
        <Calendar size={16} /> 我的定投
      </div>
      {visiblePlans.map((p) => {
        const totalAmount = p.total_executed * p.amount
        return (
          <div className="invest-card" key={p.id}>
            <div className="invest-card-header">
              <span className="invest-card-name">{p.fund_name}</span>
              <span className="invest-card-schedule">
                {formatFrequency(p)} ¥{p.amount}
              </span>
            </div>
            <div className="invest-card-status">
              <span
                className={`status-dot ${p.status === 'active' ? 'active' : 'paused'}`}
              />
              {p.status === 'active' ? '执行中' : '已暂停'} · 已执行
              {p.total_executed}次 · 累计¥{totalAmount.toLocaleString()}
            </div>
            <div className="invest-card-actions">
              {p.status === 'active' ? (
                <button onClick={() => onPause(p.id)}>暂停</button>
              ) : (
                <>
                  <button onClick={() => onResume(p.id)}>恢复</button>
                  <button className="stop-btn" onClick={() => onStop(p.id)}>
                    停止
                  </button>
                </>
              )}
            </div>
          </div>
        )
      })}
    </>
  )
}
