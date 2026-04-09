import {
  Lightbulb,
  ArrowUpCircle,
  ArrowDownCircle,
  PauseCircle,
  Target,
  AlertCircle,
  Sparkles,
} from 'lucide-react'
import type { Briefing, BriefingDetail } from '../types'

interface BriefingAreaProps {
  briefing: Briefing | null
  loading: boolean
  error: string | null
}

function BriefingDetailCard({ detail }: { detail: BriefingDetail }) {
  const cls =
    detail.action === '加仓'
      ? 'action-buy'
      : detail.action === '减仓'
        ? 'action-sell'
        : 'action-hold'

  const Icon =
    detail.action === '加仓'
      ? ArrowUpCircle
      : detail.action === '减仓'
        ? ArrowDownCircle
        : PauseCircle

  return (
    <div className="fund-card" style={{ cursor: 'default' }}>
      <div className="fund-card-left">
        <div className="fund-header">
          <div>
            <div className="fund-name">{detail.fund_name}</div>
          </div>
          <div className={`fund-action ${cls}`}>
            <Icon size={14} /> {detail.action}
          </div>
        </div>
        <div className="fund-reason">{detail.reason || ''}</div>
      </div>
    </div>
  )
}

export default function BriefingArea({
  briefing,
  loading,
  error,
}: BriefingAreaProps) {
  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
        Agent 正在分析...
      </div>
    )
  }

  if (error) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">
          <AlertCircle size={48} color="var(--red)" />
        </div>
        <div className="empty-state-text">生成失败，请重试</div>
      </div>
    )
  }

  if (!briefing) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">
          <Target size={48} color="var(--accent)" />
        </div>
        <div className="empty-state-text">
          点击下方按钮
          <br />
          生成今日操作建议
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="briefing-card">
        <div className="briefing-summary">
          <Lightbulb
            size={20}
            style={{ verticalAlign: '-3px', color: 'var(--accent)' }}
          />{' '}
          {briefing.summary || '暂无建议'}
        </div>
        <div className="briefing-market">{briefing.market_note || ''}</div>
      </div>
      {(briefing.details || []).map((d, i) => (
        <BriefingDetailCard key={i} detail={d} />
      ))}
    </>
  )
}

// ---- Generate Button ----

interface GenerateButtonProps {
  loading: boolean
  pushEnabled: boolean
  onTogglePush: () => void
  onGenerate: () => void
}

export function GenerateButton({
  loading,
  pushEnabled,
  onTogglePush,
  onGenerate,
}: GenerateButtonProps) {
  return (
    <div className="generate-area-bottom">
      <div className="generate-row">
        <button
          className="generate-btn"
          disabled={loading}
          onClick={onGenerate}
        >
          <span className="btn-icon">
            <Sparkles size={20} />
          </span>
          {loading
            ? pushEnabled
              ? '生成并推送中...'
              : '分析中...（约10秒）'
            : '生成今日简报'}
        </button>
        <div className="push-toggle-inline">
          <label>
            <input
              type="checkbox"
              className="toggle-switch"
              checked={pushEnabled}
              onChange={onTogglePush}
            />
            <span>推送</span>
          </label>
        </div>
      </div>
    </div>
  )
}
