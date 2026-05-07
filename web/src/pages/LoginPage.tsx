import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useUserStore } from '../stores/userStore'

export default function LoginPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [nickname, setNickname] = useState('')
  const { login, register, loading, error } = useUserStore()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password.trim()) return

    let success: boolean
    if (mode === 'login') {
      success = await login(username.trim(), password)
    } else {
      if (password.length < 6) {
        useUserStore.setState({ error: '密码至少 6 位' })
        return
      }
      success = await register(username.trim(), password, nickname.trim())
    }

    if (success) {
      navigate('/', { replace: true })
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">FundPal</div>
        <p className="login-subtitle">智能基金投顾助手</p>

        <div className="login-tabs">
          <button
            className={`login-tab ${mode === 'login' ? 'active' : ''}`}
            onClick={() => { setMode('login'); useUserStore.setState({ error: null }) }}
          >
            登录
          </button>
          <button
            className={`login-tab ${mode === 'register' ? 'active' : ''}`}
            onClick={() => { setMode('register'); useUserStore.setState({ error: null }) }}
          >
            注册
          </button>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <input
            type="text"
            placeholder="用户名"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
          <input
            type="password"
            placeholder="密码"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          />
          {mode === 'register' && (
            <input
              type="text"
              placeholder="昵称（可选）"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
            />
          )}

          {error && <div className="login-error">{error}</div>}

          <button type="submit" className="login-submit" disabled={loading}>
            {loading ? '处理中...' : mode === 'login' ? '登录' : '注册'}
          </button>
        </form>
      </div>
    </div>
  )
}
