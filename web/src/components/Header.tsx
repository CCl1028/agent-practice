import { Briefcase, FileText, Stethoscope, User } from 'lucide-react'

export type TabKey = 'portfolio' | 'briefing' | 'diagnosis' | 'profile'

interface HeaderProps {
  activeTab: TabKey
  onTabChange: (tab: TabKey) => void
}

const tabs: { key: TabKey; label: string; icon: typeof Briefcase }[] = [
  { key: 'portfolio', label: '持仓', icon: Briefcase },
  { key: 'briefing', label: '简报', icon: FileText },
  { key: 'diagnosis', label: '诊断', icon: Stethoscope },
  { key: 'profile', label: '我的', icon: User },
]

export default function Header({ activeTab, onTabChange }: HeaderProps) {
  return (
    <header className="web-header">
      <div className="header-inner">
        <span className="header-logo">FundPal</span>
        <nav className="header-tabs">
          {tabs.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.key
            return (
              <button
                key={tab.key}
                className={`header-tab ${isActive ? 'active' : ''}`}
                onClick={() => onTabChange(tab.key)}
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
