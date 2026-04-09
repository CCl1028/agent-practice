import { useState, useEffect } from 'react'
import { Settings, FlaskConical, FileText, RefreshCw, Trash2, Clock } from 'lucide-react'
import type { ConfigGroup } from '../types'
import { getLocalConfig, setConfigValue, getPushConfig } from '../store'
import { maskValue } from '../utils'
import * as api from '../api'

const CONFIG_FIELDS: ConfigGroup[] = [
  {
    group: '推送渠道',
    items: [
      { key: 'BARK_URL', label: 'Bark', placeholder: 'https://api.day.app/你的key', hint: 'iPhone 通知推送', sensitive: false },
      { key: 'SERVERCHAN_KEY', label: 'Server酱', placeholder: 'SCTxxx', hint: '微信推送', sensitive: true },
      { key: 'WECOM_WEBHOOK_URL', label: '企业微信', placeholder: 'https://qyapi.weixin.qq.com/...', hint: '企微群推送', sensitive: false },
    ],
  },
  {
    group: 'AI 模型',
    items: [
      { key: 'OPENAI_API_KEY', label: 'API Key', placeholder: 'sk-xxx', hint: '不填则用规则引擎', sensitive: true },
      { key: 'OPENAI_BASE_URL', label: '接口地址', placeholder: 'https://api.deepseek.com', hint: '默认 DeepSeek', sensitive: false },
    ],
  },
]

interface SettingsDrawerProps {
  open: boolean
  onClose: () => void
  showToast: (msg: string, type: 'success' | 'error' | '') => void
}

export default function SettingsDrawer({ open, onClose, showToast }: SettingsDrawerProps) {
  const [config, setConfig] = useState<Record<string, string>>({})
  const [editValues, setEditValues] = useState<Record<string, string>>({})
  const [pushResult, setPushResult] = useState('')
  const [pushTesting, setPushTesting] = useState(false)
  const [logsVisible, setLogsVisible] = useState(false)
  const [logs, setLogs] = useState<{ ts: string; level: string; msg: string }[]>([])
  const [logsTotal, setLogsTotal] = useState(0)
  const [logLevel, setLogLevel] = useState('ERROR')
  const [versionText, setVersionText] = useState('加载版本信息...')

  useEffect(() => {
    if (open) {
      const cfg = getLocalConfig()
      setConfig(cfg)
      setEditValues({})
      loadVersion()
    }
  }, [open])

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
      setVersionText(parts.length > 0 ? parts.join(' · ') : '开发版本')
    } catch {
      setVersionText('版本信息不可用')
    }
  }

  const handleSave = (key: string) => {
    const value = editValues[key]
    if (!value || value.includes('****')) {
      showToast('请输入新值', 'error')
      return
    }
    setConfigValue(key, value)
    setConfig({ ...getLocalConfig() })
    setEditValues((prev) => {
      const next = { ...prev }
      delete next[key]
      return next
    })
    showToast(`${key} 已保存`, 'success')
  }

  const handleTestPush = async () => {
    setPushTesting(true)
    setPushResult('')
    try {
      const data = await api.testPush(getPushConfig())
      const parts: string[] = []
      if (data.push_results.bark === true) parts.push('Bark(成功)')
      else if (data.push_results.bark === false) parts.push('Bark(失败)')
      if (data.push_results.serverchan === true) parts.push('Server酱(成功)')
      else if (data.push_results.serverchan === false) parts.push('Server酱(失败)')
      if (data.push_results.wecom === true) parts.push('企业微信(成功)')
      else if (data.push_results.wecom === false) parts.push('企业微信(失败)')
      if (parts.length > 0) {
        setPushResult('测试结果：' + parts.join('、'))
        showToast('测试推送已发送', 'success')
      } else {
        setPushResult('没有已配置的推送渠道')
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
    const next = !logsVisible
    setLogsVisible(next)
    if (next) handleFetchLogs()
  }

  return (
    <>
      <div
        className={`drawer-overlay${open ? ' open' : ''}`}
        onClick={onClose}
      />
      <div className={`drawer${open ? ' open' : ''}`}>
        <div className="drawer-handle">
          <div className="drawer-handle-bar" />
        </div>
        <div className="drawer-header">
          <h3>
            <Settings size={18} style={{ verticalAlign: '-3px' }} /> 设置
          </h3>
          <button className="drawer-close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="drawer-body">
          {/* Config Fields */}
          {CONFIG_FIELDS.map((group) => (
            <div className="config-group" key={group.group}>
              <div className="config-group-title">{group.group}</div>
              {group.items.map((f) => {
                const value = config[f.key] || ''
                const hasValue = !!value
                const editVal = editValues[f.key]
                const displayVal =
                  editVal !== undefined
                    ? editVal
                    : f.sensitive && hasValue
                      ? maskValue(value)
                      : value
                const isDirty =
                  editVal !== undefined &&
                  editVal !== (f.sensitive && hasValue ? maskValue(value) : value)

                return (
                  <div className="config-item" key={f.key}>
                    <div className="config-label">
                      <span className="config-label-text">
                        {f.label}{' '}
                        <span className="config-label-hint">{f.hint}</span>
                      </span>
                      <span className={`config-status ${hasValue ? 'on' : 'off'}`}>
                        {hasValue ? '已配置' : '未配置'}
                      </span>
                    </div>
                    <div className="config-input-row">
                      <input
                        className="config-input"
                        type={f.sensitive && editVal === undefined ? 'password' : 'text'}
                        placeholder={f.placeholder}
                        value={displayVal}
                        onFocus={() => {
                          if (f.sensitive && displayVal.includes('*')) {
                            setEditValues((prev) => ({ ...prev, [f.key]: '' }))
                          }
                        }}
                        onChange={(e) =>
                          setEditValues((prev) => ({
                            ...prev,
                            [f.key]: e.target.value,
                          }))
                        }
                      />
                      <button
                        className="config-save-btn"
                        disabled={!isDirty}
                        onClick={() => handleSave(f.key)}
                      >
                        保存
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          ))}

          <hr className="divider" />

          {/* Push Time (disabled) */}
          <div
            className="config-group"
            style={{ opacity: 0.45, pointerEvents: 'none' }}
          >
            <div className="config-group-title">
              <Clock size={14} style={{ verticalAlign: '-2px' }} /> 定时推送
            </div>
            <div className="config-label">
              <span className="config-label-text">每日推送时间</span>
              <span className="config-status off">未开放</span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 6 }}>
              该功能正在开发中
            </div>
          </div>

          <hr className="divider" />

          {/* Push Test */}
          <button
            className="push-test-btn"
            onClick={handleTestPush}
            disabled={pushTesting}
          >
            <FlaskConical size={14} style={{ verticalAlign: '-2px' }} />{' '}
            {pushTesting ? '发送中...' : '发送测试推送'}
          </button>
          {pushResult && (
            <div style={{ marginTop: 8, fontSize: 13, color: 'var(--text-secondary)' }}>
              {pushResult}
            </div>
          )}

          <hr className="divider" />

          {/* Logs */}
          <button className="push-test-btn" onClick={toggleLogs}>
            <FileText size={14} style={{ verticalAlign: '-2px' }} />{' '}
            {logsVisible ? '收起日志' : '查看错误日志'}
          </button>
          {logsVisible && (
            <div style={{ marginTop: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <select
                  value={logLevel}
                  onChange={(e) => {
                    setLogLevel(e.target.value)
                    setTimeout(handleFetchLogs, 0)
                  }}
                  style={{
                    background: 'var(--bg)',
                    border: '1px solid var(--border)',
                    borderRadius: 6,
                    padding: '4px 8px',
                    fontSize: 12,
                    color: 'var(--text)',
                  }}
                >
                  <option value="">全部级别</option>
                  <option value="ERROR">ERROR</option>
                  <option value="WARNING">WARNING</option>
                  <option value="INFO">INFO</option>
                </select>
                <button
                  onClick={handleFetchLogs}
                  style={{
                    background: 'none',
                    border: '1px solid var(--border)',
                    borderRadius: 6,
                    padding: '4px 8px',
                    fontSize: 12,
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 3,
                  }}
                >
                  <RefreshCw size={12} /> 刷新
                </button>
                <button
                  onClick={handleClearLogs}
                  style={{
                    background: 'none',
                    border: '1px solid var(--border)',
                    borderRadius: 6,
                    padding: '4px 8px',
                    fontSize: 12,
                    color: 'var(--red)',
                    cursor: 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 3,
                  }}
                >
                  <Trash2 size={12} /> 清空
                </button>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--border)',
                  borderRadius: 8,
                  padding: 10,
                  maxHeight: 300,
                  overflowY: 'auto',
                  fontFamily: "'SF Mono','Menlo',monospace",
                  fontSize: 11,
                  lineHeight: 1.6,
                  color: 'var(--text)',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                }}
              >
                {logs.length === 0 ? (
                  <span style={{ color: 'var(--text-secondary)' }}>暂无日志</span>
                ) : (
                  logs.map((l, i) => {
                    const color =
                      l.level === 'ERROR'
                        ? 'var(--red)'
                        : l.level === 'WARNING'
                          ? 'var(--yellow)'
                          : 'var(--text-secondary)'
                    return (
                      <div key={i} style={{ marginBottom: 4 }}>
                        <span style={{ color, fontWeight: 600 }}>[{l.level}]</span>{' '}
                        <span style={{ color: 'var(--text-secondary)' }}>{l.ts}</span>
                        {'\n'}
                        {l.msg}
                      </div>
                    )
                  })
                )}
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: 'var(--text-secondary)',
                  marginTop: 4,
                  textAlign: 'right',
                }}
              >
                显示 {logs.length} 条 / 缓冲区共 {logsTotal} 条
              </div>
            </div>
          )}

          <hr className="divider" />

          {/* Version */}
          <div
            style={{
              fontSize: 11,
              color: 'var(--text-secondary)',
              textAlign: 'center',
              padding: '4px 0 8px',
            }}
          >
            {versionText}
          </div>
        </div>
      </div>
    </>
  )
}
