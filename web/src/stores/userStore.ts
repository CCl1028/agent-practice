/**
 * 用户 Store — Zustand
 * 管理登录状态、JWT token、用户信息
 */

import { create } from 'zustand'
import * as api from '../api'

const TOKEN_KEY = 'fundpal_api_token'
const USER_KEY = 'fundpal_user'

interface UserInfo {
  user_id: number
  username: string
  nickname: string
}

interface UserStore {
  token: string
  user: UserInfo | null
  loading: boolean
  error: string | null

  login: (username: string, password: string) => Promise<boolean>
  register: (username: string, password: string, nickname?: string) => Promise<boolean>
  logout: () => void
  restoreSession: () => void
}

export const useUserStore = create<UserStore>((set) => ({
  token: localStorage.getItem(TOKEN_KEY) || '',
  user: (() => {
    try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null') } catch { return null }
  })(),
  loading: false,
  error: null,

  login: async (username, password) => {
    set({ loading: true, error: null })
    try {
      const data = await api.login(username, password)
      localStorage.setItem(TOKEN_KEY, data.token)
      localStorage.setItem(USER_KEY, JSON.stringify(data.user))
      api.setApiToken(data.token)
      set({ token: data.token, user: data.user, loading: false })
      return true
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '登录失败'
      set({ error: msg, loading: false })
      return false
    }
  },

  register: async (username, password, nickname) => {
    set({ loading: true, error: null })
    try {
      await api.register(username, password, nickname)
      // 注册成功后自动登录
      const data = await api.login(username, password)
      localStorage.setItem(TOKEN_KEY, data.token)
      localStorage.setItem(USER_KEY, JSON.stringify(data.user))
      api.setApiToken(data.token)
      set({ token: data.token, user: data.user, loading: false })
      return true
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '注册失败'
      set({ error: msg, loading: false })
      return false
    }
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    api.setApiToken('')
    set({ token: '', user: null })
  },

  restoreSession: () => {
    const token = localStorage.getItem(TOKEN_KEY) || ''
    const user = (() => {
      try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null') } catch { return null }
    })()
    if (token) api.setApiToken(token)
    set({ token, user })
  },
}))
