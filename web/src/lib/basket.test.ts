import { describe, expect, it } from 'vitest'
import type { Holdings, Portfolio } from '../data/load'
import reference from '../fixtures/basket_reference.json'
import { corrToPortfolio, evaluate, type BasketItem } from './basket'
import { loadBasket, saveBasket } from './basket-storage'

// Inputs are cut down to the fields the maths reads; the casts keep the fixtures readable.
const holdings = (positions: { key: string; ticker: string | null; value_eur: number | null; group: string | null }[]) =>
  ({ positions }) as unknown as Holdings
const portfolioOf = (tickers: string[], cov: number[][], noRisk: { ticker: string; reason: string }[] = []) =>
  ({ tickers: tickers.map((ticker) => ({ ticker })), risk_tickers: tickers, cov, no_risk_data: noRisk }) as unknown as Portfolio

const h = holdings(reference.positions)
const p = portfolioOf(reference.tickers, reference.cov)
const tech = new Set(reference.tech_tickers)

describe('evaluate matches the Python reference (engine/holdings.py)', () => {
  reference.baskets.forEach((b, i) => {
    it(`basket ${i + 1}: ${b.items.map((x) => `${x.ticker} ${x.amountEur}`).join(', ') || 'empty'}`, () => {
      const e = evaluate(h, b.items, p, tech)
      const x = b.expected
      expect(e.total).toBeCloseTo(x.total, 9)
      expect(e.top3).toBeCloseTo(x.top3, 9)
      expect(e.tech).toBeCloseTo(x.tech, 9)
      expect(e.vol).toBeCloseTo(x.vol, 9)
      expect(e.volCovered).toBeCloseTo(x.volCovered, 9)
      expect(e.topRisk?.key).toBe(x.topRisk.key)
      expect(e.topRisk?.share).toBeCloseTo(x.topRisk.share, 9)
      expect(Object.keys(e.weights).sort()).toEqual(Object.keys(x.weights).sort())
      for (const [k, w] of Object.entries(x.weights)) expect(e.weights[k]).toBeCloseTo(w, 9)
      expect(e.ignored).toEqual([])
    })
  })
})

describe('evaluate edge cases', () => {
  it('an empty basket equals before, and ignored items do not change anything', () => {
    const before = evaluate(h, [], p, tech)
    const after = evaluate(h, [{ ticker: 'AAA', amountEur: 0 }], p, tech)
    expect(after.total).toBe(before.total)
    expect(after.vol).toBe(before.vol)
    expect(after.weights).toEqual(before.weights)
  })

  it('an amount for a holding adds to that holding', () => {
    const e = evaluate(h, [{ ticker: 'BBB', amountEur: 100 }], p, tech)
    expect(e.total).toBe(1100)
    expect(e.weights.BBB).toBeCloseTo(400 / 1100, 12)
  })

  it('ignores zero, negative and NaN amounts and unknown tickers, each with a reason', () => {
    const items: BasketItem[] = [
      { ticker: 'AAA', amountEur: 0 },
      { ticker: 'BBB', amountEur: -5 },
      { ticker: 'CCC', amountEur: Number.NaN },
      { ticker: 'ZZZ', amountEur: 50 },
    ]
    const e = evaluate(h, items, p, tech)
    expect(e.ignored.map((x) => x.ticker)).toEqual(['AAA', 'BBB', 'CCC', 'ZZZ'])
    expect(e.ignored.every((x) => x.reason.length > 0)).toBe(true)
    expect(e.total).toBe(1000)
  })

  it('a portfolio without risk data has no volatility, and nothing is NaN', () => {
    const funds = holdings([{ key: 'fund:F', ticker: null, value_eur: 500, group: null }])
    const e = evaluate(funds, [], portfolioOf([], []), new Set())
    expect(e.vol).toBeNull()
    expect(e.topRisk).toBeNull()
    expect(e.volCovered).toBe(0)
    expect(Object.values(e.weights).every(Number.isFinite)).toBe(true)
  })

  it('volCovered is the share of value that has risk data', () => {
    expect(evaluate(h, [], p, tech).volCovered).toBeCloseTo(0.9, 12)
  })

  it('a holding without a price is left out and an empty portfolio gives zeros', () => {
    const none = holdings([{ key: 'X', ticker: 'X', value_eur: null, group: null }])
    const e = evaluate(none, [], p, tech)
    expect(e.total).toBe(0)
    expect(e.weights).toEqual({})
    expect(e.vol).toBeNull()
  })

  it('counts a basket ticker in the technology share through the tech set, and a tagged holding through its group', () => {
    const e = evaluate(h, [{ ticker: 'CCC', amountEur: 100 }], p, tech)
    expect(e.tech).toBeCloseTo((600 + 100) / 1100, 12) // AAA is tagged technology, CCC is in the set
  })
})

describe('corrToPortfolio', () => {
  it('is 1 for a single-holding portfolio of the same ticker', () => {
    const one = holdings([{ key: 'AAA', ticker: 'AAA', value_eur: 100, group: null }])
    expect(corrToPortfolio('AAA', one, p).value).toBeCloseTo(1, 12)
  })

  it('matches the matrix: AAA against a BBB-only portfolio is its pairwise correlation (0.5)', () => {
    const one = holdings([{ key: 'BBB', ticker: 'BBB', value_eur: 100, group: null }])
    expect(corrToPortfolio('AAA', one, p).value).toBeCloseTo(0.5, 12)
  })

  it('gives a reason, not a number, for a ticker without risk data', () => {
    const noRisk = portfolioOf(['AAA', 'BBB', 'CCC'], reference.cov, [{ ticker: 'NEW', reason: 'only 30 of 104 weekly returns' }])
    const r = corrToPortfolio('NEW', h, noRisk)
    expect(r.value).toBeNull()
    expect(r.reason).toContain('only 30 of 104')
  })

  it('gives a reason when no holding has risk data', () => {
    const funds = holdings([{ key: 'fund:F', ticker: null, value_eur: 500, group: null }])
    expect(corrToPortfolio('AAA', funds, p)).toEqual({ value: null, reason: expect.stringContaining('holdings') })
  })
})

describe('basket storage', () => {
  const memory = () => {
    const data = new Map<string, string>()
    return { getItem: (k: string) => data.get(k) ?? null, setItem: (k: string, v: string) => void data.set(k, v) }
  }

  it('round-trips a basket', () => {
    const s = memory()
    saveBasket([{ ticker: 'AAA', amountEur: 250 }], s)
    expect(loadBasket(s)).toEqual([{ ticker: 'AAA', amountEur: 250 }])
  })

  it('returns an empty basket for corrupt, missing or blocked storage', () => {
    expect(loadBasket({ getItem: () => '{not json' })).toEqual([])
    expect(loadBasket({ getItem: () => null })).toEqual([])
    expect(
      loadBasket({
        getItem: () => {
          throw new Error('blocked')
        },
      }),
    ).toEqual([])
  })

  it('rejects a stored basket with a negative or non-numeric amount', () => {
    expect(loadBasket({ getItem: () => JSON.stringify([{ ticker: 'AAA', amountEur: -1 }]) })).toEqual([])
    expect(loadBasket({ getItem: () => JSON.stringify([{ ticker: 'AAA', amountEur: 'lots' }]) })).toEqual([])
  })
})
