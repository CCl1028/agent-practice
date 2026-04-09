import { useState } from 'react'
import { CheckCircle, Image } from 'lucide-react'
import type { Holding } from '../types'

interface ConfirmDrawerProps {
  open: boolean
  holdings: Holding[]
  source: 'screenshot' | 'text' | ''
  onClose: () => void
  onSave: (holdings: Holding[]) => void
}

export default function ConfirmDrawer({
  open,
  holdings: initialHoldings,
  source,
  onClose,
  onSave,
}: ConfirmDrawerProps) {
  const [items, setItems] = useState<Holding[]>([])

  // Sync when opened with new data
  if (open && items.length === 0 && initialHoldings.length > 0) {
    setItems(initialHoldings.map((h) => ({ ...h })))
  }

  const handleClose = () => {
    setItems([])
    onClose()
  }

  const handleRemove = (index: number) => {
    setItems((prev) => prev.filter((_, i) => i !== index))
  }

  const handleFieldChange = (index: number, field: keyof Holding, value: string | number) => {
    setItems((prev) =>
      prev.map((item, i) =>
        i === index ? { ...item, [field]: value } : item,
      ),
    )
  }

  const handleSave = () => {
    if (items.length === 0) {
      handleClose()
      return
    }
    onSave(items)
    setItems([])
    onClose()
  }

  const typeLabel = source === 'screenshot' ? '截图识别' : '文本识别'
  const screenshotType = items[0]?.screenshot_type
  const stLabel =
    screenshotType === 'detail'
      ? '详情页截图'
      : screenshotType === 'list'
        ? '列表页截图'
        : '截图'

  return (
    <>
      <div
        className={`drawer-overlay confirm-drawer-overlay${open ? ' open' : ''}`}
        onClick={handleClose}
      />
      <div className={`drawer confirm-drawer${open ? ' open' : ''}`}>
        <div className="drawer-handle">
          <div className="drawer-handle-bar" />
        </div>
        <div className="drawer-header">
          <h3>
            <CheckCircle
              size={18}
              style={{ verticalAlign: '-3px', color: 'var(--accent)' }}
            />{' '}
            {typeLabel}结果（{items.length}只）
          </h3>
          <button className="drawer-close" onClick={handleClose}>
            ✕
          </button>
        </div>
        <div className="drawer-body">
          {screenshotType && (
            <div style={{ marginBottom: 12 }}>
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                  fontSize: 12,
                  padding: '3px 10px',
                  borderRadius: 10,
                  background: 'rgba(184,78,74,0.08)',
                  color: 'var(--accent)',
                }}
              >
                <Image size={12} /> {stLabel}
              </span>
            </div>
          )}
          <div className="confirm-list">
            {items.length === 0 ? (
              <div className="confirm-empty">没有待确认的基金</div>
            ) : (
              items.map((h, i) => (
                <div className="confirm-item" key={i}>
                  <div className="confirm-item-header">
                    <span className="confirm-item-title">
                      {h.fund_name || '未知基金'}
                    </span>
                    <span className="confirm-item-code">{h.fund_code || ''}</span>
                    <button
                      className="confirm-item-remove"
                      onClick={() => handleRemove(i)}
                      title="删除"
                    >
                      ✕
                    </button>
                  </div>
                  <div className="confirm-fields">
                    {[
                      { label: '基金名称', field: 'fund_name' as const, type: 'text' },
                      { label: '基金代码', field: 'fund_code' as const, type: 'text' },
                      { label: '持仓金额', field: 'cost' as const, type: 'number' },
                      { label: '成本净值', field: 'cost_nav' as const, type: 'number' },
                      { label: '收益率(%)', field: 'profit_ratio' as const, type: 'number' },
                      { label: '持有份额', field: 'shares' as const, type: 'number' },
                      { label: '收益金额', field: 'profit_amount' as const, type: 'number' },
                      { label: '最新净值', field: 'current_nav' as const, type: 'number' },
                    ].map(({ label, field, type }) => (
                      <div className="confirm-field" key={field}>
                        <label>{label}</label>
                        <input
                          type={type}
                          step={type === 'number' ? '0.0001' : undefined}
                          value={h[field] ?? ''}
                          onChange={(e) =>
                            handleFieldChange(
                              i,
                              field,
                              type === 'number'
                                ? parseFloat(e.target.value) || 0
                                : e.target.value,
                            )
                          }
                        />
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
          <div className="confirm-actions">
            <button className="confirm-cancel-btn" onClick={handleClose}>
              取消
            </button>
            <button
              className="confirm-save-btn"
              disabled={items.length === 0}
              onClick={handleSave}
            >
              确认保存
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
