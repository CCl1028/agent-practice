import type { InvestPlan } from './types'

export function formatFrequency(plan: InvestPlan): string {
  if (plan.frequency === 'daily') return '每天'
  if (plan.frequency === 'monthly') return '每月' + plan.day + '号'
  if (plan.frequency === 'biweekly') {
    const days = ['', '周一', '周二', '周三', '周四', '周五']
    return '每两周' + (days[plan.day] || '')
  }
  const days = ['', '周一', '周二', '周三', '周四', '周五']
  return '每' + (days[plan.day] || '')
}

export function maskValue(val: string): string {
  if (!val) return ''
  if (val.length <= 8) return '*'.repeat(val.length)
  return val.slice(0, 3) + '*'.repeat(val.length - 6) + val.slice(-3)
}

export function generateId(): string {
  return Date.now() + '_' + Math.random().toString(36).slice(2, 8)
}

export function formatPushResults(
  results: Record<string, boolean | null>,
): string {
  const parts: string[] = []
  if (results.bark === true) parts.push('Bark(成功)')
  else if (results.bark === false) parts.push('Bark(失败)')
  if (results.serverchan === true) parts.push('微信(成功)')
  else if (results.serverchan === false) parts.push('微信(失败)')
  if (results.wecom === true) parts.push('企微(成功)')
  else if (results.wecom === false) parts.push('企微(失败)')
  return parts.length > 0 ? '| 推送: ' + parts.join(' ') : ''
}
