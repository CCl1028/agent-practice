import { useState, useEffect } from 'react'
import { Signal, Wifi, BatteryFull } from 'lucide-react'

export default function Header() {
  const [time, setTime] = useState('')

  useEffect(() => {
    const updateTime = () => {
      const now = new Date()
      const hours = now.getHours().toString().padStart(2, '0')
      const minutes = now.getMinutes().toString().padStart(2, '0')
      setTime(`${hours}:${minutes}`)
    }
    updateTime()
    const timer = setInterval(updateTime, 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="status-bar">
      <div className="status-left">
        <span className="status-time">{time}</span>
      </div>
      <div className="status-notch" />
      <div className="status-right">
        <Signal size={14} />
        <Wifi size={14} />
        <BatteryFull size={16} />
      </div>
    </div>
  )
}
