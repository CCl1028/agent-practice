import { Settings, TrendingUp } from 'lucide-react'

interface HeaderProps {
  onOpenSettings: () => void
}

export default function Header({ onOpenSettings }: HeaderProps) {
  return (
    <div className="header">
      <div className="header-center">
        <h1>
          <TrendingUp
            size={22}
            style={{ verticalAlign: '-3px', color: 'var(--accent)' }}
          />{' '}
          FundPal
        </h1>
        <p>智能基金投顾助手</p>
      </div>
      <button
        className="settings-trigger"
        onClick={onOpenSettings}
        title="设置"
      >
        <Settings size={20} />
      </button>
    </div>
  )
}
