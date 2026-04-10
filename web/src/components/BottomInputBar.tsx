import { useRef, useState } from 'react'
import { Camera, Plus, Trash2, X } from 'lucide-react'
import type { Holding } from '../types'

interface ManualHolding {
  fund_code: string
  fund_name: string
  cost: string
  shares: string
  profit: string // 持有收益
  profitRate: string // 持有收益率
}

const emptyHolding = (): ManualHolding => ({
  fund_code: '',
  fund_name: '',
  cost: '',
  shares: '',
  profit: '',
  profitRate: '',
})

interface BottomInputBarProps {
  disabled: boolean
  onSendFile: (files: File[]) => Promise<void>
  onAddHoldings: (holdings: Holding[]) => void
}

export default function BottomInputBar({
  disabled,
  onSendFile,
  onAddHoldings,
}: BottomInputBarProps) {
  const [mode, setMode] = useState<'idle' | 'form'>('idle')
  const [pendingFile, setPendingFile] = useState<File | null>(null)
  const [sending, setSending] = useState(false)
  const [holdings, setHoldings] = useState<ManualHolding[]>([emptyHolding()])
  const fileRef = useRef<HTMLInputElement>(null)

  // 检查表单是否有效（至少有一个有效的基金代码）
  const hasValidHolding = holdings.some((h) => h.fund_code.trim() !== '')
  // 检查是否所有填写了内容的行都有基金代码
  const hasIncompleteRow = holdings.some(
    (h) =>
      (h.fund_name.trim() || h.cost.trim() || h.shares.trim() || h.profit.trim() || h.profitRate.trim()) &&
      !h.fund_code.trim()
  )

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files
    if (!fileList || fileList.length === 0) return

    // Limit to 9 files max
    const files = Array.from(fileList).slice(0, 9)

    setSending(true)
    setPendingFile(files[0]) // Show first file as indicator
    try {
      await onSendFile(files)
    } finally {
      setSending(false)
      setPendingFile(null)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const handleAddRow = () => {
    setHoldings((prev) => [...prev, emptyHolding()])
  }

  const handleRemoveRow = (index: number) => {
    if (holdings.length <= 1) {
      // 如果只剩一行，清空它而不是删除
      setHoldings([emptyHolding()])
    } else {
      setHoldings((prev) => prev.filter((_, i) => i !== index))
    }
  }

  const handleFieldChange = (
    index: number,
    field: keyof ManualHolding,
    value: string
  ) => {
    setHoldings((prev) =>
      prev.map((h, i) => (i === index ? { ...h, [field]: value } : h))
    )
  }

  const handleSubmit = () => {
    if (!hasValidHolding || hasIncompleteRow) return

    const validHoldings: Holding[] = holdings
      .filter((h) => h.fund_code.trim())
      .map((h) => ({
        fund_code: h.fund_code.trim(),
        fund_name: h.fund_name.trim() || h.fund_code.trim(),
        cost: h.cost ? parseFloat(h.cost) || 0 : undefined,
        shares: h.shares ? parseFloat(h.shares) || 0 : undefined,
        profit_amount: h.profit ? parseFloat(h.profit) : undefined,
        profit_ratio: h.profitRate ? parseFloat(h.profitRate) / 100 : undefined, // 转换为小数
      }))

    if (validHoldings.length > 0) {
      onAddHoldings(validHoldings)
      setHoldings([emptyHolding()])
      setMode('idle')
    }
  }

  const handleCancel = () => {
    setHoldings([emptyHolding()])
    setMode('idle')
  }

  const [fabOpen, setFabOpen] = useState(false)

  const openForm = () => {
    setFabOpen(false)
    setMode('form')
  }

  const handleUploadClick = () => {
    setFabOpen(false)
    fileRef.current?.click()
  }

  const toggleFab = () => {
    setFabOpen((prev) => !prev)
  }

  // 表单模式
  if (mode === 'form') {
    return (
      <>
        <div className="form-drawer-overlay" onClick={handleCancel} />
        <div className="form-drawer">
          <div className="drawer-handle">
            <div className="drawer-handle-bar" />
          </div>
          <div className="drawer-header">
            <h3>添加持仓基金</h3>
            <button className="drawer-close" onClick={handleCancel}>
              <X size={20} />
            </button>
          </div>
          <div className="drawer-body">
            <div className="form-hint">
              <span className="required-mark">*</span> 基金代码为必填项，其他信息选填
            </div>
            <div className="form-body">
              {holdings.map((h, index) => (
                <div className="form-row" key={index}>
                  <div className="form-row-fields">
                    <input
                      type="text"
                      placeholder="基金代码"
                      value={h.fund_code}
                      onChange={(e) =>
                        handleFieldChange(index, 'fund_code', e.target.value)
                      }
                      className={`form-input code-input required-field${
                        !h.fund_code.trim() &&
                        (h.fund_name.trim() || h.cost.trim() || h.shares.trim() || h.profit.trim() || h.profitRate.trim())
                          ? ' error'
                          : ''
                      }`}
                    />
                    <input
                      type="text"
                      placeholder="基金名称"
                      value={h.fund_name}
                      onChange={(e) =>
                        handleFieldChange(index, 'fund_name', e.target.value)
                      }
                      className="form-input name-input"
                    />
                    <input
                      type="number"
                      placeholder="持仓金额"
                      value={h.cost}
                      onChange={(e) =>
                        handleFieldChange(index, 'cost', e.target.value)
                      }
                      className="form-input cost-input"
                    />
                    <input
                      type="number"
                      placeholder="持有份额"
                      value={h.shares}
                      onChange={(e) =>
                        handleFieldChange(index, 'shares', e.target.value)
                      }
                      className="form-input shares-input"
                    />
                    <input
                      type="number"
                      placeholder="持有收益(元)"
                      value={h.profit}
                      onChange={(e) =>
                        handleFieldChange(index, 'profit', e.target.value)
                      }
                      className="form-input profit-input"
                    />
                    <input
                      type="number"
                      placeholder="收益率(%)"
                      value={h.profitRate}
                      onChange={(e) =>
                        handleFieldChange(index, 'profitRate', e.target.value)
                      }
                      className="form-input profit-rate-input"
                    />
                  </div>
                  <button
                    className="form-row-remove"
                    onClick={() => handleRemoveRow(index)}
                    title="删除此行"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
              <button className="form-add-row" onClick={handleAddRow}>
                <Plus size={14} /> 添加更多
              </button>
            </div>
            {hasIncompleteRow && (
              <div className="form-error">请为所有行填写基金代码</div>
            )}
            <div className="form-actions">
              <button className="form-cancel-btn" onClick={handleCancel}>
                取消
              </button>
              <button
                className="form-submit-btn"
                disabled={!hasValidHolding || hasIncompleteRow}
                onClick={handleSubmit}
              >
                确认添加
              </button>
            </div>
          </div>
        </div>
      </>
    )
  }

  // 默认模式：悬浮按钮
  return (
    <>
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        multiple
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />
      
      {/* FAB 遮罩层 */}
      {fabOpen && (
        <div className="fab-overlay" onClick={() => setFabOpen(false)} />
      )}
      
      {/* FAB 展开菜单 */}
      <div className={`fab-menu ${fabOpen ? 'open' : ''}`}>
        <button
          className="fab-menu-item"
          onClick={handleUploadClick}
          disabled={sending || disabled}
        >
          <Camera size={18} />
          <span>{pendingFile ? '分析中...' : '上传截图'}</span>
        </button>
        <button
          className="fab-menu-item"
          onClick={openForm}
          disabled={sending || disabled}
        >
          <Plus size={18} />
          <span>手动添加</span>
        </button>
      </div>
      
      {/* 悬浮按钮 */}
      <button
        className={`fab-button ${fabOpen ? 'active' : ''}`}
        onClick={toggleFab}
        disabled={sending || disabled}
      >
        <Plus size={24} className="fab-icon" />
      </button>
    </>
  )
}
