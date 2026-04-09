interface ToastProps {
  message: string
  type: 'success' | 'error' | ''
  visible: boolean
}

export default function Toast({ message, type, visible }: ToastProps) {
  const className = ['toast', type, visible ? 'show' : '']
    .filter(Boolean)
    .join(' ')

  return <div className={className}>{message}</div>
}
