import { useEffect } from 'react'

/**
 * Lock body scroll when a drawer/modal is open.
 * Prevents scroll chaining on mobile browsers.
 */
export function useBodyScrollLock(isLocked: boolean) {
  useEffect(() => {
    if (!isLocked) return

    const scrollY = window.scrollY
    const body = document.body

    // Lock body scroll
    body.style.position = 'fixed'
    body.style.top = `-${scrollY}px`
    body.style.left = '0'
    body.style.right = '0'
    body.style.overflow = 'hidden'

    return () => {
      // Restore body scroll
      body.style.position = ''
      body.style.top = ''
      body.style.left = ''
      body.style.right = ''
      body.style.overflow = ''
      window.scrollTo(0, scrollY)
    }
  }, [isLocked])
}
