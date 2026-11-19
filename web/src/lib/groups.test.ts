import { describe, expect, it } from 'vitest'
import type { Data, Position } from '../data/load'
import holdings from '../fixtures/holdings.json'
import leaderboard from '../fixtures/leaderboard.json'
import { candidatesOf, eur, groupLabel, median, sectorCards, techTickers } from './groups'

const data = { holdings, leaderboard } as unknown as Data

describe('techTickers', () => {
  it('holds shares in Technology or Communication Services and ETFs tagged technology, nothing else', () => {
    const t = techTickers(data)
    expect(t.has('DEMA')).toBe(true) // Technology
    expect(t.has('DEMD')).toBe(true) // Communication Services
    expect(t.has('DEMETF.DE')).toBe(true) // ETF with group = "technology"
    expect(t.has('DEMETG.DE')).toBe(false) // ETF without the tag
    expect(t.has('DEFA.DE')).toBe(false) // Industrials
  })
})

describe('groupLabel', () => {
  const p = (over: Partial<Position>) => ({ kind: 'stock', group: null, ...over }) as Position
  it('uses the owner tag when there is one, else the kind', () => {
    expect(groupLabel(p({ group: 'technology' }))).toBe('Technology')
    expect(groupLabel(p({}))).toBe('Other shares')
    expect(groupLabel(p({ kind: 'etf' }))).toBe('ETFs')
    expect(groupLabel(p({ kind: 'fund' }))).toBe('Funds')
  })
})

describe('eur', () => {
  it('groups thousands, uses a real minus, and signs on request', () => {
    expect(eur(12345.678, 2)).toBe('12,345.68')
    expect(eur(-123.45, 2, true)).toBe('−123.45')
    expect(eur(1234.56, 0, true)).toBe('+1,235')
    expect(eur(null)).toBe('—')
  })
})

describe('median and sectorCards', () => {
  it('median handles odd, even and empty lists', () => {
    expect(median([3, 1, 2])).toBe(2)
    expect(median([1, 2, 3, 4])).toBe(2.5)
    expect(median([])).toBeNull()
  })

  const demo = { holdings, leaderboard } as unknown as Data
  it('one card per sector, each share only once, with the portfolio share of that sector', () => {
    const cards = sectorCards(demo)
    const by = Object.fromEntries(cards.map((c) => [c.sector, c]))
    expect(by.Industrials.count).toBe(4) // DEFA.DE, DEFB.L, DEFC.PA, NRDB.CO
    expect(by.Energy.count).toBe(3) // ENGA.OL is on two lists but counted once
    expect(by.Industrials.share).toBeCloseTo(0.3675, 3) // the one Industrials holding
    expect(by.Energy.share).toBe(0)
    expect(cards[0].share).toBe(0) // sectors with nothing in the portfolio come first
  })

  it('leaves inconsistent forward P/E out of the median', () => {
    const rows = [10, 20, 400, -5].map((fwd_pe, i) => ({ ticker: `X${i}`, sector: 'S', fwd_pe, lists: ['l'] }))
    const d = { holdings: { positions: [], etfs: [] }, leaderboard: { lists: [{ key: 'l', rows }] } } as unknown as Data
    expect(sectorCards(d)[0].medianFwdPe).toBe(15) // 400 and -5 are not used
  })
})

describe('candidatesOf', () => {
  it('lists every share once with all its lists, then the ETFs', () => {
    const c = candidatesOf({ holdings, leaderboard } as unknown as Data)
    const enga = c.filter((x) => x.ticker === 'ENGA.OL')
    expect(enga).toHaveLength(1)
    expect(enga[0].origin).toContain('European energy')
    expect(enga[0].origin).toContain('Nordic energy')
    expect(c.filter((x) => x.kind === 'ETF').map((x) => x.ticker).sort()).toEqual(['DEMETF.DE', 'DEMETG.DE'])
    expect(c.find((x) => x.ticker === 'DEMETG.DE')?.pe).toBeNull()
  })
})
