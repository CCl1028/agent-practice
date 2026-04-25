import { useState, useEffect } from 'react'
import {
  User,
  Key,
  Bell,
  Shield,
  Trash2,
  Download,
  Upload,
  ChevronRight,
  FlaskConical,
  FileText,
  RefreshCw,
} from 'lucide-react'
import {
  getLocalPortfolio,
  saveLocalPortfolio,
  getTransactions,
  getInvestPlans,
} from '../store'
import * as api from '../api'
import type { ConfigEntry } from '../api'

interface ProfilePageProps {
  showToast: (msg: string, type: 'success' | 'error') => void
}

interface ConfigItem {
  key: string
  label: string
  placeholder: string
  hint: string
  sensitive: boolean
}

const AI_CONFIG_ITEMS: ConfigItem[] = [
  { key: 'OPENAI_API_KEY', label: 'API Key', placeholder: 'sk-xxx', hint: '截图识别已内置，无需配置', sensitive: true },
  { key: 'OPENAI_BASE_URL', label: '接口地址', placeholder: 'https://api.deepseek.com/v1', hint: '默认 DeepSeek', sensitive: false },
]

const PUSH_CONFIG_ITEMS: ConfigItem[] = [
  { key: 'BARK_URL', label: 'Bark', placeholder: 'https://api.day.app/你的key', hint: 'iPhone 通知推送', sensitive: false },
  { key: 'SERVERCHAN_KEY', label: 'Server酱', placeholder: 'SCTxxx', hint: '微信推送', sensitive: true },
  { key: 'WECOM_WEBHOOK_URL', label: '企业微信', placeholder: 'https://qyapi.weixin.qq.com/...', hint: '企微群推送', sensitive: false },
]

export default function ProfilePage({ showToast }: ProfilePageProps) {
  const [serverConfig, setServerConfig] = useState<Record<string, ConfigEntry>>({})
  const [editValues, setEditValues] = useState<Record<string, string>>({})
  const [showAIConfig, setShowAIConfig] = useState(false)
  const [showPushConfig, setShowPushConfig] = useState(false)
  const [showLogs, setShowLogs] = useState(false)
  const [portfolioCount, setPortfolioCount] = useState(0)
  const [txCount, setTxCount] = useState(0)
  const [pushTesting, setPushTesting] = useState(false)
  const [pushResult, setPushResult] = useState('')
  const [logs, setLogs] = useState<{ ts: string; level: string; msg: string }[]>([])
  const [logsTotal, setLogsTotal] = useState(0)
  const [logLevel, setLogLevel] = useState('ERROR')
  const [versionText, setVersionText] = useState('')
  const [savingKey, setSavingKey] = useState('')

  useEffect(() => {
    loadConfig()
    setPortfolioCount(getLocalPortfolio().length)
    setTxCount(getTransactions().length)
    loadVersion()
  }, [])

  const loadConfig = async () => {
    try {
      const cfg = await api.fetchConfig()
      setServerConfig(cfg)
    } catch {
      // Fallback: 后端不可用时不 crash
    }
  }

  const loadVersion = async () => {
    try {
      const v = await api.fetchVersion()
      const parts: string[] = []
      if (v.version && v.version !== 'dev') parts.push('v' + v.version)
      if (v.codename) parts.push(v.codename)
      if (v.build_time && v.build_time !== 'unknown') parts.push(v.build_time)
      if (v.git_commit && v.git_commit !== 'unknown' && v.git_commit !== 'local') {
        parts.push(v.git_commit.substring(0, 7))
      }
      setVersionText(parts.length > 0 ? parts.join(' · ') : 'v1.0.0')
    } catch {
      setVersionText('v1.0.0')
    }
  }

  const handleSave = async (key: string) => {
    const value = editValues[key]
    if (!value || value.includes('****')) {
      showToast('请输入新值', 'error')
      return
    }
    setSavingKey(key)
    try {
      await api.updateConfig(key, value)
      await loadConfig() // 刷新服务端配置
      setEditValues((prev) => {
        const next = { ...prev }
        delete next[key]
        return next
      })
      showToast('配置已保存到服务端', 'success')
    } catch {
      showToast('保存失败，请检查网络', 'error')
    } finally {
      setSavingKey('')
    }
  }

  const renderConfigItem = (item: ConfigItem) => {
    const entry = serverConfig[item.key]
    const hasValue = entry?.has_value || false
    const serverValue = entry?.value || ''
    const editVal = editValues[item.key]
    const displayVal =
      editVal !== undefined
        ? editVal
        : serverValue
    const isDirty =
      editVal !== undefined && editVal !== serverValue

    return (
      <div className="config-item" key={item.key}>
        <div className="config-label-row">
          <span className="config-field-label">
            {item.label}
            <span className="config-hint">{item.hint}</span>
          </span>
          <span className={`config-status ${hasValue ? 'on' : 'off'}`}>
            {hasValue ? '已配置' : '未配置'}
          </span>
        </div>
        <div className="config-input-row">
          <input
            type={item.sensitive && editVal === undefined ? 'password' : 'text'}
            placeholder={item.placeholder}
            value={displayVal}
            onFocus={() => {
              if (item.sensitive && displayVal.includes('*')) {
                setEditValues((prev) => ({ ...prev, [item.key]: '' }))
              }
            }}
            onChange={(e) =>
              setEditValues((prev) => ({
                ...prev,
                [item.key]: e.target.value,
              }))
            }
          />
          <button
            className="save-btn small"
            disabled={!isDirty || savingKey === item.key}
            onClick={() => handleSave(item.key)}
          >
            {savingKey === item.key ? '...' : '保存'}
          </button>
        </div>
      </div>
    )
  }

  const handleTestPush = async () => {
    setPushTesting(true)
    setPushResult('')
    try {
      const data = await api.testPush({}) // 后端自己读 .env 的推送配置
      const parts: string[] = []
      if (data.push_results.bark === true) parts.push('Bark ✓')
      else if (data.push_results.bark === false) parts.push('Bark ✗')
      if (data.push_results.serverchan === true) parts.push('Server酱 ✓')
      else if (data.push_results.serverchan === false) parts.push('Server酱 ✗')
      if (data.push_results.wecom === true) parts.push('企微 ✓')
      else if (data.push_results.wecom === false) parts.push('企微 ✗')
      if (parts.length > 0) {
        setPushResult(parts.join('  '))
        showToast('测试推送已发送', 'success')
      } else {
        setPushResult('未配置推送渠道')
        showToast('请先配置推送渠道', 'error')
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      setPushResult('测试失败: ' + msg)
      showToast('测试失败', 'error')
    } finally {
      setPushTesting(false)
    }
  }

  const handleFetchLogs = async () => {
    try {
      const data = await api.fetchLogs(200, logLevel || undefined)
      setLogs(data.logs)
      setLogsTotal(data.total)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      setLogs([{ ts: '', level: 'ERROR', msg: '加载失败: ' + msg }])
    }
  }

  const handleClearLogs = async () => {
    try {
      await api.clearLogs()
      showToast('日志已清空', 'success')
      handleFetchLogs()
    } catch {
      showToast('清空失败', 'error')
    }
  }

  const toggleLogs = () => {
    const next = !showLogs
    setShowLogs(next)
    if (next) handleFetchLogs()
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
    if (!confirm('确认清除所有本地数据？此操作不可恢复！')) return
    localStorage.clear()
    showToast('本地数据已清除，请刷新页面', 'success')
  }

  return (
    <div className="page-content profile-page">
      <div className="page-content-body">
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
        <div className="section-header" onClick={() => setShowAIConfig(!showAIConfig)}>
          <div className="section-title">
            <Key size={18} />
            <span>AI 配置</span>
          </div>
          <ChevronRight size={18} className={`chevron ${showAIConfig ? 'open' : ''}`} />
        </div>
        {showAIConfig && (
          <div className="section-content">
            <p className="section-desc">配置 AI 模型用于文本解析和简报生成</p>
            {AI_CONFIG_ITEMS.map(renderConfigItem)}
          </div>
        )}
      </div>

      {/* Push Config */}
      <div className="config-section">
        <div className="section-header" onClick={() => setShowPushConfig(!showPushConfig)}>
          <div className="section-title">
            <Bell size={18} />
            <span>推送配置</span>
          </div>
          <ChevronRight size={18} className={`chevron ${showPushConfig ? 'open' : ''}`} />
        </div>
        {showPushConfig && (
          <div className="section-content">
            <p className="section-desc">配置推送渠道，简报生成后自动推送</p>
            {PUSH_CONFIG_ITEMS.map(renderConfigItem)}
            <button
              className="test-push-btn"
              onClick={handleTestPush}
              disabled={pushTesting}
            >
              <FlaskConical size={14} />
              {pushTesting ? '发送中...' : '发送测试推送'}
            </button>
            {pushResult && <p className="push-result">{pushResult}</p>}
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

      {/* Logs */}
      <div className="config-section">
        <div className="section-header" onClick={toggleLogs}>
          <div className="section-title">
            <FileText size={18} />
            <span>错误日志</span>
          </div>
          <ChevronRight size={18} className={`chevron ${showLogs ? 'open' : ''}`} />
        </div>
        {showLogs && (
          <div className="section-content">
            <div className="logs-toolbar">
              <select
                value={logLevel}
                onChange={(e) => {
                  setLogLevel(e.target.value)
                  setTimeout(handleFetchLogs, 0)
                }}
              >
                <option value="">全部级别</option>
                <option value="ERROR">ERROR</option>
                <option value="WARNING">WARNING</option>
                <option value="INFO">INFO</option>
              </select>
              <button className="logs-action-btn" onClick={handleFetchLogs}>
                <RefreshCw size={12} /> 刷新
              </button>
              <button className="logs-action-btn danger" onClick={handleClearLogs}>
                <Trash2 size={12} /> 清空
              </button>
            </div>
            <div className="logs-container">
              {logs.length === 0 ? (
                <span className="logs-empty">暂无日志</span>
              ) : (
                logs.map((l, i) => {
                  const color =
                    l.level === 'ERROR'
                      ? 'var(--red)'
                      : l.level === 'WARNING'
                        ? 'var(--yellow)'
                        : 'var(--text-secondary)'
                  return (
                    <div key={i} className="log-entry">
                      <span style={{ color, fontWeight: 600 }}>[{l.level}]</span>{' '}
                      <span className="log-time">{l.ts}</span>
                      <br />
                      {l.msg}
                    </div>
                  )
                })
              )}
            </div>
            <p className="logs-count">
              显示 {logs.length} 条 / 缓冲区共 {logsTotal} 条
            </p>
          </div>
        )}
      </div>

      {/* Version */}
      <div className="version-info">
        <p>FundPal {versionText}</p>
        <p className="copyright">智能基金投顾助手</p>
      </div>
      </div>
    </div>
  )
}
