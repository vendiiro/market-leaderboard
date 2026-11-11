import { describe, expect, it } from 'vitest'
import type { Portfolio } from '../data/load'
import reference from '../fixtures/mix_reference.json'
import demo from '../fixtures/portfolio.json'
import { analyse, effectiveN, exposure, normalise, portfolioVol, riskContribution, type TickerMeta, type Weights } from './mix'
import { asMix, EMPTY, fromFile, load, save, toFile } from './storage'

const portfolio = demo as Portfolio
const meta = reference.meta as Record<string, TickerMeta>
const close = (a: Record<string, number>, b: Record<string, number>) => {
  expect(Object.keys(a).sort()).toEqual(Object.keys(b).sort())
  for (const k of Object.keys(b)) expect(a[k]).toBeCloseTo(b[k], 9)
}

describe('mix formulas match the Python reference (engine/portfolio.py)', () => {
  reference.mixes.forEach((m, i) => {
    it(`mix ${i + 1}: ${Object.keys(m.weights).join(' + ')}`, () => {
      const w = m.weights as Weights
      expect(portfolioVol(w, reference.tickers, reference.cov)).toBeCloseTo(m.vol, 9)
      expect(effectiveN(w)).toBeCloseTo(m.effective_n, 9)
      close(riskContribution(w, reference.tickers, reference.cov), m.risk_contribution as Weights)
      for (const key of ['sector', 'country', 'currency', 'lists'] as const) close(exposure(w, meta, key), m.exposure[key] as Weights)
    })
  })

  it('reproduces the worked check in the spec', () => {
    const w = { AAA: 0.6, BBB: 0.4 }
    expect(portfolioVol(w, reference.tickers, reference.cov)).toBeCloseTo(0.230651, 6)
    const rc = riskContribution(w, reference.tickers, reference.cov)
    expect(rc.AAA).toBeCloseTo(0.744361, 6)
    expect(rc.BBB).toBeCloseTo(0.255639, 6)
    expect(effectiveN(w)).toBeCloseTo(1.923077, 6)
  })

  it('normalises weights and rejects unusable ones', () => {
    expect(normalise({ A: 60, B: 40 })).toEqual({ A: 0.6, B: 0.4 })
    expect(portfolioVol({ AAA: 60, BBB: 40 }, reference.tickers, reference.cov)).toBeCloseTo(0.230651, 6)
    expect(() => normalise({ A: 0, B: 0 })).toThrow()
    expect(() => normalise({ A: 2, B: -1 })).toThrow()
    expect(() => normalise({ A: Number.NaN })).toThrow()
    expect(() => portfolioVol({ ZZZ: 1 }, reference.tickers, reference.cov)).toThrow(/No risk data for ZZZ/)
  })
})

describe('analyse: a whole mix against tonight’s data', () => {
  it('names a ticker that is missing tonight and one without risk data, and never gives NaN', () => {
    const a = analyse(
      [{ ticker: 'DEMA', weight: 50 }, { ticker: 'DEFC.PA', weight: 30 }, { ticker: 'FIND.HE', weight: 20 }, { ticker: 'ENGA.OL', weight: 20 }],
      portfolio,
    )!
    expect(a.missing).toEqual(['FIND.HE']) // no data tonight: left out, weights renormalised over the rest
    expect(a.weights).toEqual({ DEMA: 0.5, 'DEFC.PA': 0.3, 'ENGA.OL': 0.2 })
    expect(a.noRisk).toEqual([{ ticker: 'DEFC.PA', reason: expect.stringContaining('weekly returns') }])
    expect(a.risk!.tickers).toEqual(['DEMA', 'ENGA.OL'])
    expect(a.risk!.covered).toBeCloseTo(0.7, 12)
    expect(a.risk!.weights.DEMA).toBeCloseTo(5 / 7, 12)
    expect(Object.values(a.risk!.contribution).reduce((s, x) => s + x, 0)).toBeCloseTo(1, 12)
    expect(a.exposure.lists).toEqual({ us_big_tech: 0.5, eu_defence: 0.3, eu_energy: 0.2, nordic_energy: 0.2 })
    expect(JSON.stringify(a)).not.toMatch(/NaN|null,"vol"/)
    expect(Number.isFinite(a.risk!.vol) && a.risk!.vol > 0).toBe(true)
  })

  it('handles the edges: empty, zero weights, only names without risk data, a repeated ticker', () => {
    expect(analyse([], portfolio)).toBeNull()
    expect(analyse([{ ticker: 'DEMA', weight: 0 }, { ticker: 'NOPE', weight: 5 }], portfolio)).toBeNull()
    const noRisk = analyse([{ ticker: 'DEFC.PA', weight: 1 }], portfolio)!
    expect(noRisk.risk).toBeNull()
    expect(noRisk.effectiveN).toBe(1)
    expect(analyse([{ ticker: 'DEMA', weight: 1 }, { ticker: 'DEMA', weight: 1 }, { ticker: 'DEMB', weight: 2 }], portfolio)!.weights).toEqual({ DEMA: 0.5, DEMB: 0.5 })
  })

  it('a single name has its own volatility from the engine', () => {
    const a = analyse([{ ticker: 'DEMA', weight: 7 }], portfolio)!
    const vol = portfolio.tickers.find((t) => t.ticker === 'DEMA')!.vol_eur!
    expect(a.risk!.vol).toBeCloseTo(vol, 3)
  })
})

describe('storage and files', () => {
  const mix = { name: 'Mix A', items: [{ ticker: 'DEMA', weight: 60 }, { ticker: 'ENGA.OL', weight: 40 }] }

  it('round-trips through storage and survives corrupt or missing storage', () => {
    const box = new Map<string, string>()
    const storage = { getItem: (k: string) => box.get(k) ?? null, setItem: (k: string, v: string) => void box.set(k, v) }
    expect(load(storage)).toEqual(EMPTY)
    save({ a: mix, b: null }, storage)
    expect(load(storage)).toEqual({ a: mix, b: null })
    expect(load({ getItem: () => '{not json' })).toEqual(EMPTY)
    expect(load({ getItem: () => '{"a":{"name":"x","items":[{"ticker":"A","weight":"1"}]}}' })).toEqual(EMPTY)
    expect(load({ getItem: () => { throw new Error('blocked') } })).toEqual(EMPTY)
    expect(() => save({ a: mix, b: null }, { setItem: () => { throw new Error('full') } })).not.toThrow()
  })

  it('exports a file it can import again and rejects anything else', () => {
    expect(fromFile(toFile(mix))).toEqual(mix)
    expect(() => fromFile('hello')).toThrow(/not valid JSON/)
    expect(() => fromFile('{"name":"x","items":[]}')).toThrow(/not a mix file exported/)
    expect(() => fromFile('{"market_leaderboard_mix":1,"name":"x","items":[{"ticker":"A","weight":-1}]}')).toThrow(/not a mix file/)
    expect(asMix({ name: 'x', items: [{ ticker: '', weight: 1 }] })).toBeNull()
    expect(asMix({ name: 'x', items: Array(201).fill({ ticker: 'A', weight: 1 }) })).toBeNull()
  })
})
