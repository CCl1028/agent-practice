import { describe, it, expect, beforeEach } from 'vitest'
import { useTradeStore } from '../stores/tradeStore'

describe('tradeStore', () => {
  beforeEach(() => {
    useTradeStore.setState({
      transactions: [],
      investPlans: [],
      tradeOpen: false,
      tradeType: 'buy',
      tradeHolding: null,
      investOpen: false,
      investHolding: null,
    })
    localStorage.clear()
  })

  it('initializes with empty state', () => {
    const state = useTradeStore.getState()
    expect(state.transactions).toEqual([])
    expect(state.investPlans).toEqual([])
    expect(state.tradeOpen).toBe(false)
  })

  it('openTrade and closeTrade', () => {
    const holding = { fund_code: '005827', fund_name: 'Test' } as any
    useTradeStore.getState().openTrade(holding, 'buy')
    expect(useTradeStore.getState().tradeOpen).toBe(true)
    expect(useTradeStore.getState().tradeType).toBe('buy')
    expect(useTradeStore.getState().tradeHolding).toEqual(holding)

    useTradeStore.getState().closeTrade()
    expect(useTradeStore.getState().tradeOpen).toBe(false)
  })

  it('openInvest and closeInvest', () => {
    const holding = { fund_code: '005827', fund_name: 'Test' } as any
    useTradeStore.getState().openInvest(holding)
    expect(useTradeStore.getState().investOpen).toBe(true)

    useTradeStore.getState().closeInvest()
    expect(useTradeStore.getState().investOpen).toBe(false)
  })

  it('submitTrade adds transaction and returns recalculated values', () => {
    const result = useTradeStore.getState().submitTrade('005827', 'buy', 10000, 2.0, 'test buy')
    expect(result.total_shares).toBeGreaterThan(0)
    expect(result.total_cost).toBe(10000)
    expect(useTradeStore.getState().transactions).toHaveLength(1)
    expect(useTradeStore.getState().transactions[0].type).toBe('buy')
  })

  it('submitInvest creates an invest plan', () => {
    useTradeStore.getState().submitInvest('005827', 'Test Fund', 1000, 'weekly', 1)
    const plans = useTradeStore.getState().investPlans
    expect(plans).toHaveLength(1)
    expect(plans[0].fund_code).toBe('005827')
    expect(plans[0].status).toBe('active')
  })

  it('pauseInvest and resumeInvest toggle plan status', () => {
    useTradeStore.getState().submitInvest('005827', 'Test Fund', 1000, 'weekly', 1)
    const planId = useTradeStore.getState().investPlans[0].id

    useTradeStore.getState().pauseInvest(planId)
    expect(useTradeStore.getState().investPlans[0].status).toBe('paused')

    useTradeStore.getState().resumeInvest(planId)
    expect(useTradeStore.getState().investPlans[0].status).toBe('active')
  })

  it('stopInvest sets plan status to stopped', () => {
    useTradeStore.getState().submitInvest('005827', 'Test Fund', 1000, 'weekly', 1)
    const planId = useTradeStore.getState().investPlans[0].id

    useTradeStore.getState().stopInvest(planId)
    expect(useTradeStore.getState().investPlans[0].status).toBe('stopped')
  })
})
