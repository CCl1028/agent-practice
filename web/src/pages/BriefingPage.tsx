import {
  Lightbulb,
  ArrowUpCircle,
  ArrowDownCircle,
  PauseCircle,
  Target,
  AlertCircle,
  Sparkles,
  RefreshCw,
  Clock,
} from 'lucide-react'
import type { Briefing, BriefingDetail } from '../types'

interface BriefingPageProps {
  briefing: Briefing | null
  loading: boolean
  error: string | null
  pushEnabled: boolean
  hasHoldings: boolean
  onTogglePush: () => void
  onGenerate: () => void
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
    <div className="briefing-detail-card">
      <div className="detail-header">
        <div className="detail-fund-name">{detail.fund_name}</div>
        <div className={`detail-action ${cls}`}>
          <Icon size={14} /> {detail.action}
        </div>
      </div>
      <div className="detail-reason">{detail.reason || ''}</div>
    </div>
  )
}

export default function BriefingPage({
  briefing,
  loading,
  error,
  pushEnabled,
  hasHoldings,
  onTogglePush,
  onGenerate,
}: BriefingPageProps) {
  return (
    <div className="page-content briefing-page">
      {/* Simple Header */}
      <div className="simple-page-header">
        <h1>今日简报</h1>
      </div>

      {/* Content Area */}
      <div className="briefing-content-area">
        {loading && (
          <div className="briefing-loading">
            <div className="loading-animation">
              <div className="pulse-ring"></div>
              <Sparkles size={32} className="pulse-icon" />
            </div>
            <div className="loading-text">Agent 正在分析您的持仓...</div>
            <div className="loading-hint">预计需要 10-15 秒</div>
          </div>
        )}

        {!loading && error && (
          <div className="briefing-error">
            <AlertCircle size={48} />
            <div className="error-title">生成失败</div>
            <div className="error-message">{error}</div>
            <button className="retry-btn" onClick={onGenerate}>
              重试
            </button>
          </div>
        )}

        {!loading && !error && !briefing && (
          <div className="briefing-empty">
            <Target size={64} className="empty-icon" />
            <div className="empty-title">
              {hasHoldings ? '暂无简报' : '请先添加持仓'}
            </div>
            <div className="empty-hint">
              {hasHoldings
                ? '点击下方按钮，AI 将根据市场动态和您的持仓情况，生成个性化投资建议'
                : '在「持仓」页面添加基金后，即可生成投资简报'}
            </div>
          </div>
        )}

        {!loading && !error && briefing && (
          <div className="briefing-result">
            {/* Summary Card */}
            <div className="briefing-summary-card">
              <div className="summary-header">
                <Lightbulb size={22} />
                <span>核心建议</span>
              </div>
              <div className="summary-content">
                {briefing.summary || '暂无建议'}
              </div>
            </div>

            {/* Market Note */}
            {briefing.market_note && (
              <div className="briefing-market-card">
                <div className="market-header">
                  <Clock size={16} />
                  <span>市场观察</span>
                </div>
                <div className="market-content">{briefing.market_note}</div>
              </div>
            )}

            {/* Details */}
            {briefing.details && briefing.details.length > 0 && (
              <div className="briefing-details">
                <div className="details-header">
                  <span>个股建议</span>
                  <span className="details-count">{briefing.details.length} 只基金</span>
                </div>
                {briefing.details.map((d, i) => (
                  <BriefingDetailCard key={i} detail={d} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Bottom Generate Button Area */}
      <div className="briefing-bottom-bar">
        <div className="briefing-options">
          <label className="push-option">
            <input
              type="checkbox"
              className="toggle-switch"
              checked={pushEnabled}
              onChange={onTogglePush}
            />
            <span>同时推送通知</span>
          </label>
        </div>
        <button
          className="briefing-generate-btn"
          disabled={loading || !hasHoldings}
          onClick={onGenerate}
        >
          {loading ? (
            <>
              <RefreshCw size={20} className="spinning" />
              {pushEnabled ? '生成并推送中...' : '分析中...'}
            </>
          ) : (
            <>
              <Sparkles size={20} />
              {briefing ? '重新生成简报' : '生成今日简报'}
            </>
          )}
        </button>
      </div>
    </div>
  )
}
