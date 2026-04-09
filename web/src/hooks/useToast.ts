import { useState, useCallback, useRef } from 'react'

type ToastType = 'success' | 'error' | ''

interface ToastState {
  message: string
  type: ToastType
  visible: boolean
}

export function useToast() {
  const [toast, setToast] = useState<ToastState>({
    message: '',
    type: '',
    visible: false,
  })
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const showToast = useCallback((msg: string, type: ToastType = '') => {
    if (timerRef.current) clearTimeout(timerRef.current)
    setToast({ message: msg, type, visible: true })
    timerRef.current = setTimeout(() => {
      setToast((prev) => ({ ...prev, visible: false }))
    }, 3000)
  }, [])

  return { toast, showToast }
}
