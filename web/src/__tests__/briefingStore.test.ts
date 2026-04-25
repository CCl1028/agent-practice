import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useBriefingStore } from '../stores/briefingStore'
import { usePortfolioStore } from '../stores/portfolioStore'

vi.mock('../api', () => ({
  fetchBriefing: vi.fn(),
  refreshPortfolioNav: vi.fn().mockResolvedValue({ holdings: [] }),
  fetchEstimation: vi.fn().mockResolvedValue({ estimations: {} }),
}))

describe('briefingStore', () => {
  beforeEach(() => {
    useBriefingStore.setState({
      briefing: null,
      loading: false,
      error: null,
      pushEnabled: true,
    })
    usePortfolioStore.setState({ holdings: [] })
  })

  it('initializes with null briefing', () => {
    const state = useBriefingStore.getState()
    expect(state.briefing).toBeNull()
    expect(state.loading).toBe(false)
    expect(state.pushEnabled).toBe(true)
  })

  it('togglePush flips pushEnabled', () => {
    useBriefingStore.getState().togglePush()
    expect(useBriefingStore.getState().pushEnabled).toBe(false)
    useBriefingStore.getState().togglePush()
    expect(useBriefingStore.getState().pushEnabled).toBe(true)
  })

  it('generate does nothing when no holdings', async () => {
    await useBriefingStore.getState().generate()
    expect(useBriefingStore.getState().briefing).toBeNull()
    expect(useBriefingStore.getState().loading).toBe(false)
  })

  it('generate sets briefing on success', async () => {
    const mockBriefing = { summary: 'test', funds: [] }
    const { fetchBriefing } = await import('../api')
    ;(fetchBriefing as any).mockResolvedValueOnce({ raw: mockBriefing })

    usePortfolioStore.setState({
      holdings: [{ fund_code: '005827', fund_name: 'Test' } as any],
    })

    await useBriefingStore.getState().generate()
    expect(useBriefingStore.getState().briefing).toEqual(mockBriefing)
    expect(useBriefingStore.getState().error).toBeNull()
  })

  it('generate sets error on failure', async () => {
    const { fetchBriefing } = await import('../api')
    ;(fetchBriefing as any).mockRejectedValueOnce(new Error('network error'))

    usePortfolioStore.setState({
      holdings: [{ fund_code: '005827', fund_name: 'Test' } as any],
    })

    await useBriefingStore.getState().generate()
    expect(useBriefingStore.getState().error).toBe('network error')
    expect(useBriefingStore.getState().briefing).toBeNull()
  })

  it('reset clears briefing and error', () => {
    useBriefingStore.setState({ briefing: { summary: 'x' } as any, error: 'err' })
    useBriefingStore.getState().reset()
    expect(useBriefingStore.getState().briefing).toBeNull()
    expect(useBriefingStore.getState().error).toBeNull()
  })
})
