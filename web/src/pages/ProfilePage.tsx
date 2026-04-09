import { useState, useEffect } from 'react'
import {
  User,
  Key,
  Bell,
  HelpCircle,
  ChevronRight,
  Shield,
  Trash2,
  Download,
  Upload,
} from 'lucide-react'
import {
  getAIConfig,
  saveAIConfig,
  getPushConfig,
  savePushConfig,
  getLocalPortfolio,
  saveLocalPortfolio,
  getTransactions,
  getInvestPlans,
} from '../store'

interface ProfilePageProps {
  showToast: (msg: string, type: 'success' | 'error') => void
  onOpenSettings: () => void
}

export default function ProfilePage({ showToast, onOpenSettings }: ProfilePageProps) {
  const [aiConfig, setAiConfig] = useState({ apiKey: '', baseUrl: '' })
  const [pushConfig, setPushConfig] = useState({ serverChanKey: '', barkKey: '' })
  const [showApiKey, setShowApiKey] = useState(false)
  const [showPushKey, setShowPushKey] = useState(false)
  const [portfolioCount, setPortfolioCount] = useState(0)
  const [txCount, setTxCount] = useState(0)

  useEffect(() => {
    const ai = getAIConfig()
    setAiConfig({
      apiKey: ai.OPENAI_API_KEY || '',
      baseUrl: ai.OPENAI_BASE_URL || '',
    })
    const push = getPushConfig()
    setPushConfig({
      serverChanKey: push.SERVERCHAN_KEY || '',
      barkKey: push.BARK_URL || '',
    })
    setPortfolioCount(getLocalPortfolio().length)
    setTxCount(getTransactions().length)
  }, [])

  const handleSaveAIConfig = () => {
    saveAIConfig(aiConfig)
    showToast('AI 配置已保存', 'success')
  }

  const handleSavePushConfig = () => {
    savePushConfig(pushConfig)
    showToast('推送配置已保存', 'success')
  }

  const handleExportData = () => {
    const data = {
      portfolio: getLocalPortfolio(),
      transactions: getTransactions(),
      investPlans: getInvestPlans(),
      exportedAt: new Date().toISOString(),
    }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `fundpal-backup-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
    showToast('数据已导出', 'success')
  }

  const handleImportData = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json'
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return
      const reader = new FileReader()
      reader.onload = (ev) => {
        try {
          const data = JSON.parse(ev.target?.result as string)
          if (data.portfolio) {
            saveLocalPortfolio(data.portfolio)
          }
          showToast('数据已导入，请刷新页面', 'success')
        } catch {
          showToast('导入失败：文件格式错误', 'error')
        }
      }
      reader.readAsText(file)
    }
    input.click()
  }

  const handleClearData = () => {
    if (!confirm('确认清除所有数据？此操作不可恢复！')) return
    localStorage.clear()
    showToast('数据已清除，请刷新页面', 'success')
  }

  return (
    <div className="page-content profile-page">
      {/* User Info */}
      <div className="profile-header">
        <div className="avatar">
          <User size={32} />
        </div>
        <div className="user-info">
          <div className="user-name">FundPal 用户</div>
          <div className="user-stats">
            {portfolioCount} 只持仓 · {txCount} 条交易记录
          </div>
        </div>
      </div>

      {/* AI Config */}
      <div className="config-section">
        <div className="section-header" onClick={() => setShowApiKey(!showApiKey)}>
          <div className="section-title">
            <Key size={18} />
            <span>AI 配置</span>
          </div>
          <ChevronRight size={18} className={`chevron ${showApiKey ? 'open' : ''}`} />
        </div>
        {showApiKey && (
          <div className="section-content">
            <div className="config-item">
              <label>API Key</label>
              <input
                type="password"
                placeholder="输入 OpenAI/兼容 API Key"
                value={aiConfig.apiKey}
                onChange={(e) => setAiConfig({ ...aiConfig, apiKey: e.target.value })}
              />
            </div>
            <div className="config-item">
              <label>Base URL (可选)</label>
              <input
                type="text"
                placeholder="默认 OpenAI，可填代理地址"
                value={aiConfig.baseUrl}
                onChange={(e) => setAiConfig({ ...aiConfig, baseUrl: e.target.value })}
              />
            </div>
            <button className="save-btn" onClick={handleSaveAIConfig}>
              保存 AI 配置
            </button>
          </div>
        )}
      </div>

      {/* Push Config */}
      <div className="config-section">
        <div className="section-header" onClick={() => setShowPushKey(!showPushKey)}>
          <div className="section-title">
            <Bell size={18} />
            <span>推送配置</span>
          </div>
          <ChevronRight size={18} className={`chevron ${showPushKey ? 'open' : ''}`} />
        </div>
        {showPushKey && (
          <div className="section-content">
            <div className="config-item">
              <label>Server酱 Key</label>
              <input
                type="password"
                placeholder="输入 Server酱 SendKey"
                value={pushConfig.serverChanKey}
                onChange={(e) =>
                  setPushConfig({ ...pushConfig, serverChanKey: e.target.value })
                }
              />
            </div>
            <div className="config-item">
              <label>Bark Key</label>
              <input
                type="password"
                placeholder="输入 Bark Key"
                value={pushConfig.barkKey}
                onChange={(e) =>
                  setPushConfig({ ...pushConfig, barkKey: e.target.value })
                }
              />
            </div>
            <button className="save-btn" onClick={handleSavePushConfig}>
              保存推送配置
            </button>
          </div>
        )}
      </div>

      {/* Data Management */}
      <div className="config-section">
        <div className="section-header">
          <div className="section-title">
            <Shield size={18} />
            <span>数据管理</span>
          </div>
        </div>
        <div className="section-content data-actions">
          <button className="action-btn" onClick={handleExportData}>
            <Download size={16} />
            导出数据
          </button>
          <button className="action-btn" onClick={handleImportData}>
            <Upload size={16} />
            导入数据
          </button>
          <button className="action-btn danger" onClick={handleClearData}>
            <Trash2 size={16} />
            清除数据
          </button>
        </div>
      </div>

      {/* Help */}
      <div className="config-section">
        <div className="section-header" onClick={onOpenSettings}>
          <div className="section-title">
            <HelpCircle size={18} />
            <span>更多设置</span>
          </div>
          <ChevronRight size={18} />
        </div>
      </div>

      {/* Version */}
      <div className="version-info">
        <p>FundPal v1.0.0</p>
        <p className="copyright">智能基金投顾助手</p>
      </div>
    </div>
  )
}
