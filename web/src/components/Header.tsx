import { useLocation, useNavigate } from 'react-router-dom'
import { Briefcase, FileText, Stethoscope, User } from 'lucide-react'

type TabKey = 'portfolio' | 'briefing' | 'diagnosis' | 'profile'

const tabs: { key: TabKey; path: string; label: string; icon: typeof Briefcase }[] = [
  { key: 'portfolio', path: '/', label: '持仓', icon: Briefcase },
  { key: 'briefing', path: '/briefing', label: '简报', icon: FileText },
  { key: 'diagnosis', path: '/diagnosis', label: '诊断', icon: Stethoscope },
  { key: 'profile', path: '/profile', label: '我的', icon: User },
]

export default function Header() {
  const location = useLocation()
  const navigate = useNavigate()

  const currentPath = location.pathname

  return (
    <header className="web-header">
      <div className="header-inner">
        <span className="header-logo">FundPal</span>
        <nav className="header-tabs">
          {tabs.map((tab) => {
            const Icon = tab.icon
            const isActive = currentPath === tab.path || (tab.path === '/' && currentPath === '')
            return (
              <button
                key={tab.key}
                className={`header-tab ${isActive ? 'active' : ''}`}
                onClick={() => navigate(tab.path)}
              >
                <Icon size={16} />
                <span>{tab.label}</span>
              </button>
            )
          })}
        </nav>
      </div>
    </header>
  )
}
