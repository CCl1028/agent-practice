import { TrendingUp, FileText, Activity, User } from 'lucide-react'
import type { TabKey } from './TabBar'

interface HeaderProps {
  activeTab: TabKey
}

const PAGE_CONFIG: Record<TabKey, { title: string; icon: React.ReactNode; showBrand?: boolean }> = {
  portfolio: {
    title: 'FundPal',
    icon: <TrendingUp size={22} style={{ verticalAlign: '-3px', color: 'var(--accent)' }} />,
    showBrand: true,
  },
  briefing: {
    title: '投资简报',
    icon: <FileText size={20} style={{ verticalAlign: '-3px', color: 'var(--accent)' }} />,
  },
  diagnosis: {
    title: '基金诊断',
    icon: <Activity size={20} style={{ verticalAlign: '-3px', color: 'var(--accent)' }} />,
  },
  profile: {
    title: '我的',
    icon: <User size={20} style={{ verticalAlign: '-3px', color: 'var(--accent)' }} />,
  },
}

export default function Header({ activeTab }: HeaderProps) {
  const config = PAGE_CONFIG[activeTab]

  return (
    <div className="header">
      <div className="header-center">
        <h1>
          {config.icon}{' '}
          {config.title}
        </h1>
        {config.showBrand && <p>智能基金投顾助手</p>}
      </div>
    </div>
  )
}
