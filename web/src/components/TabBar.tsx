import { Briefcase, FileText, Stethoscope, User } from 'lucide-react'

export type TabKey = 'portfolio' | 'briefing' | 'diagnosis' | 'profile'

interface TabBarProps {
  active: TabKey
  onChange: (tab: TabKey) => void
}

const tabs: { key: TabKey; label: string; icon: typeof Briefcase }[] = [
  { key: 'portfolio', label: '持仓', icon: Briefcase },
  { key: 'briefing', label: '简报', icon: FileText },
  { key: 'diagnosis', label: '诊断', icon: Stethoscope },
  { key: 'profile', label: '我的', icon: User },
]

export default function TabBar({ active, onChange }: TabBarProps) {
  return (
    <div className="tab-bar">
      {tabs.map((tab) => {
        const Icon = tab.icon
        const isActive = active === tab.key
        return (
          <button
            key={tab.key}
            className={`tab-item ${isActive ? 'active' : ''}`}
            onClick={() => onChange(tab.key)}
          >
            <Icon size={22} />
            <span>{tab.label}</span>
          </button>
        )
      })}
    </div>
  )
}
