import { describe, it, expect, beforeEach } from 'vitest'
import { getApiToken, setApiToken } from '../api'

describe('API Token management', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('returns empty string when no token set', () => {
    expect(getApiToken()).toBe('')
  })

  it('stores and retrieves token', () => {
    setApiToken('test-token-123')
    expect(getApiToken()).toBe('test-token-123')
  })

  it('removes token when set to empty', () => {
    setApiToken('test-token-123')
    setApiToken('')
    expect(getApiToken()).toBe('')
    expect(localStorage.getItem('fundpal_api_token')).toBeNull()
  })
})
