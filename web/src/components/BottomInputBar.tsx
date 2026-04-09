import { useRef, useState, useCallback } from 'react'
import { Camera, Paperclip, Send } from 'lucide-react'

interface BottomInputBarProps {
  disabled: boolean
  onSendText: (text: string) => Promise<void>
  onSendFile: (file: File) => Promise<void>
}

export default function BottomInputBar({
  disabled,
  onSendText,
  onSendFile,
}: BottomInputBarProps) {
  const [text, setText] = useState('')
  const [pendingFile, setPendingFile] = useState<File | null>(null)
  const [sending, setSending] = useState(false)
  const textRef = useRef<HTMLTextAreaElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const canSend = !sending && !disabled && (text.trim() || pendingFile)

  const autoGrow = useCallback(() => {
    const el = textRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }, [])

  const handleSend = async () => {
    if (!canSend) return
    setSending(true)
    try {
      if (pendingFile) {
        await onSendFile(pendingFile)
        setPendingFile(null)
        if (fileRef.current) fileRef.current.value = ''
      } else if (text.trim()) {
        await onSendText(text.trim())
      }
      setText('')
      if (textRef.current) {
        textRef.current.style.height = 'auto'
      }
    } finally {
      setSending(false)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) setPendingFile(file)
  }

  const clearFile = () => {
    setPendingFile(null)
    if (fileRef.current) fileRef.current.value = ''
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="bottom-input-bar">
      <div className="input-row">
        <button
          className={`icon-btn upload-btn${pendingFile ? ' has-file' : ''}`}
          onClick={() => fileRef.current?.click()}
          disabled={sending || disabled}
          title="上传截图"
          style={sending || disabled ? { opacity: 0.5, pointerEvents: 'none' } : {}}
        >
          <Camera size={18} />
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
        <textarea
          ref={textRef}
          className="text-input"
          rows={1}
          placeholder="描述持仓或上传截图"
          value={text}
          disabled={sending || disabled}
          style={sending || disabled ? { opacity: 0.6 } : {}}
          onChange={(e) => {
            setText(e.target.value)
            autoGrow()
          }}
          onKeyDown={handleKeyDown}
        />
        <button
          className="icon-btn send-btn"
          onClick={handleSend}
          disabled={!canSend}
          title="发送"
        >
          <Send size={18} />
        </button>
      </div>
      {pendingFile && (
        <div className="file-hint">
          <Paperclip size={12} style={{ verticalAlign: '-1px' }} />{' '}
          {pendingFile.name}{' '}
          <span className="clear-file" onClick={clearFile}>
            ✕
          </span>
        </div>
      )}
    </div>
  )
}
