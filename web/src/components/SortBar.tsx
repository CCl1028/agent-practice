import type { SortKey, SortDir } from '../types'

const SORT_KEYS: { key: SortKey; label: string }[] = [
  { key: 'time', label: '添加时间' },
  { key: 'cost', label: '持仓' },
  { key: 'profit_ratio', label: '收益率' },
  { key: 'profit', label: '收益额' },
  { key: 'today', label: '今日涨幅' },
]

interface SortBarProps {
  sortKey: SortKey
  sortDir: SortDir
  onSort: (key: SortKey) => void
}

export default function SortBar({ sortKey, sortDir, onSort }: SortBarProps) {
  return (
    <div className="sort-bar">
      {SORT_KEYS.map(({ key, label }) => {
        const isActive = sortKey === key
        return (
          <span
            key={key}
            className={`sort-btn${isActive ? ' active' : ''}`}
            onClick={() => onSort(key)}
          >
            {label}{' '}
            <span className="sort-arrows">
              <span
                className={`arrow-up${isActive && sortDir === 'asc' ? ' lit' : ''}`}
              >
                ▲
              </span>
              <span
                className={`arrow-down${isActive && sortDir === 'desc' ? ' lit' : ''}`}
              >
                ▼
              </span>
            </span>
          </span>
        )
      })}
    </div>
  )
}
