import { Stethoscope, Construction, Bell } from 'lucide-react'

export default function DiagnosisPage() {
  return (
    <div className="page-content diagnosis-page">
      <div className="simple-page-header">
        <h1>基金诊断</h1>
      </div>

      <div className="page-content-body">
      <div className="coming-soon">
        <div className="coming-soon-icon">
          <Construction size={48} />
        </div>
        <h2>基金诊断</h2>
        <p className="coming-soon-desc">
          深度分析单支基金的健康状况
          <br />
          包括风险评估、业绩归因、持仓分析等
        </p>
        
        <div className="feature-preview">
          <h3>即将上线功能</h3>
          <ul>
            <li>
              <Stethoscope size={18} />
              <span>基金健康度评分</span>
            </li>
            <li>
              <Stethoscope size={18} />
              <span>业绩归因分析</span>
            </li>
            <li>
              <Stethoscope size={18} />
              <span>持仓穿透分析</span>
            </li>
            <li>
              <Stethoscope size={18} />
              <span>风险预警提示</span>
            </li>
            <li>
              <Stethoscope size={18} />
              <span>同类基金对比</span>
            </li>
          </ul>
        </div>

        <button className="notify-btn" disabled>
          <Bell size={16} />
          功能开发中，敬请期待
        </button>
      </div>
      </div>
    </div>
  )
}
