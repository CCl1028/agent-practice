/**
 * API service layer — all fetch calls to FastAPI backend
 */

import type {
  Holding,
  BriefingResponse,
  EstimationResponse,
  PushResults,
  VersionInfo,
  LogEntry,
} from './types'

const API = '' // same-origin, no prefix needed

// ---- Auth Token 管理 ----

const TOKEN_KEY = 'fundpal_api_token'

export function getApiToken(): string {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setApiToken(token: string): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
}

/** 构建带认证的请求头 */
function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { ...extra }
  const token = getApiToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

// ---- Briefing ----

export async function fetchBriefing(
  holdings: Holding[],
  withPush: boolean,
  pushConfig?: Record<string, string>,
): Promise<BriefingResponse> {
  const endpoint = withPush ? '/api/briefing-and-push' : '/api/briefing'
  const body: Record<string, unknown> = { holdings }
  if (withPush && pushConfig) body.config = pushConfig

  const res = await fetch(API + endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error('Server returned ' + res.status)
  return res.json()
}

// ---- Portfolio ----

export async function refreshPortfolioNav(
  holdings: Holding[],
): Promise<{ holdings: Holding[] }> {
  const res = await fetch(API + '/api/portfolio/refresh', {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ holdings }),
  })
  if (!res.ok) throw new Error('Refresh failed')
  return res.json()
}

export async function parseText(
  text: string,
  config: Record<string, string>,
): Promise<{ parsed: Holding[] }> {
  const res = await fetch(API + '/api/portfolio/parse-text', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, config }),
  })
  if (!res.ok) {
    const errText = await res.text()
    let msg = 'Server returned ' + res.status
    if (res.status === 504 || errText.includes('Gateway Time-out')) {
      msg = '服务器处理超时，请稍后重试'
    } else if (res.status === 502 || errText.includes('Bad Gateway')) {
      msg = '服务暂时不可用，请稍后重试'
    } else if (errText && !errText.startsWith('<')) {
      msg = errText
    }
    throw new Error(msg)
  }
  return res.json()
}

export async function parseScreenshot(
  file: File,
  config?: Record<string, string>,
): Promise<{ parsed: Holding[] }> {
  const form = new FormData()
  form.append('file', file)
  if (config && Object.keys(config).length > 0) {
    form.append('config', JSON.stringify(config))
  }
  const res = await fetch(API + '/api/portfolio/parse-screenshot', {
    method: 'POST',
    body: form,
  })
  if (!res.ok) {
    const errText = await res.text()
    let msg = 'Server returned ' + res.status
    if (res.status === 504 || errText.includes('Gateway Time-out')) {
      msg = '服务器处理超时，请稍后重试'
    } else if (res.status === 502 || errText.includes('Bad Gateway')) {
      msg = '服务暂时不可用，请稍后重试'
    } else if (errText && !errText.startsWith('<')) {
      // 尝试解析 JSON 错误信息
      try {
        const errJson = JSON.parse(errText)
        if (errJson.error) msg = errJson.error
      } catch {
        msg = errText
      }
    }
    throw new Error(msg)
  }
  return res.json()
}

// ---- Estimation ----

export async function fetchEstimation(
  holdings: Holding[],
): Promise<EstimationResponse> {
  const res = await fetch(API + '/api/estimation', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ holdings }),
  })
  if (!res.ok) throw new Error('Estimation failed')
  return res.json()
}

// ---- Push ----

export async function testPush(
  config: Record<string, string>,
): Promise<{ push_results: PushResults }> {
  const res = await fetch(API + '/api/push/test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ config }),
  })
  if (!res.ok) throw new Error('Push test failed')
  return res.json()
}

// ---- Logs ----

export async function fetchLogs(
  limit = 200,
  level?: string,
): Promise<{ logs: LogEntry[]; total: number }> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (level) params.set('level', level)
  const res = await fetch(API + '/api/logs?' + params.toString())
  if (!res.ok) throw new Error('Fetch logs failed')
  return res.json()
}

export async function clearLogs(): Promise<void> {
  await fetch(API + '/api/logs', { method: 'DELETE' })
}

// ---- Config ----

export interface ConfigEntry {
  value: string
  has_value: boolean
  sensitive: boolean
}

export async function fetchConfig(): Promise<Record<string, ConfigEntry>> {
  const res = await fetch(API + '/api/config', { headers: authHeaders() })
  if (!res.ok) throw new Error('Config fetch failed')
  return res.json()
}

export async function updateConfig(key: string, value: string): Promise<void> {
  const res = await fetch(API + '/api/config', {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ key, value }),
  })
  if (!res.ok) throw new Error('Config update failed')
}

// ---- Version ----

export async function fetchVersion(): Promise<VersionInfo> {
  const res = await fetch(API + '/api/version')
  if (!res.ok) throw new Error('Version fetch failed')
  return res.json()
}

// ---- Nav History (for auto-invest catch-up) ----

export async function fetchNavHistory(
  fundCode: string,
  start: string,
  end: string,
): Promise<{ fund_code: string; nav_list: { date: string; nav: number }[] }> {
  const res = await fetch(
    API + `/api/fund/${fundCode}/nav-history?start=${start}&end=${end}`,
    { headers: authHeaders() },
  )
  if (!res.ok) throw new Error('Nav history fetch failed')
  return res.json()
}
