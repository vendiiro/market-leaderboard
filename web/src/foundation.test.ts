import { describe, expect, it } from 'vitest'
import { checked, loadAll, type Data } from './data/load'
import leaderboard from './fixtures/leaderboard.json'
import meta from './fixtures/meta.json'
import movers from './fixtures/movers.json'
import portfolio from './fixtures/portfolio.json'
import research from './fixtures/research.json'
import { direction, pct, rankChange, weekdaysBetween } from './lib/format'
import { sortBy } from './lib/sort'
import { treemap } from './lib/treemap'
import { formatHash, parseHash, withCompany } from './router'

const fixtures = { meta, leaderboard, movers, portfolio, research } as Record<keyof Data, unknown>

describe('data loading', () => {
  it('returns the five typed files from the fixtures', async () => {
    const data = await loadAll(async (name) => fixtures[name])
    expect(data.meta.demo).toBe(true)
    expect(data.leaderboard.lists.map((l) => l.key)).toEqual(['us_big_tech', 'eu_defence', 'eu_energy', 'nordic_energy', 'fi_small'])
    expect(data.portfolio.cov.length).toBe(data.portfolio.risk_tickers.length)
    expect(data.research.shortlist.length).toBeGreaterThan(0)
  })

  it('rejects a wrong or missing schema version with a readable message', async () => {
    await expect(loadAll(async (name) => (name === 'movers' ? { ...movers, schema_version: 1 } : fixtures[name]))).rejects.toThrow(
      /movers\.json has schema version 1, this page needs 2/,
    )
    expect(() => checked('meta', {})).toThrow(/schema version missing/)
    expect(() => checked('meta', null)).toThrow(/schema version missing/)
  })

  it('passes a failed read on', async () => {
    await expect(loadAll(async () => Promise.reject(new Error('offline')))).rejects.toThrow('offline')
  })
})

describe('format', () => {
  it('formats percentages with a sign, a real minus and a dash for missing', () => {
    expect(pct(0.1234)).toBe('+12.3 %')
    expect(pct(-0.05)).toBe('−5.0 %')
    expect(pct(null)).toBe('—')
    expect(pct(Number.NaN)).toBe('—')
    expect(pct(-0.0001)).toBe('0.0 %') // never "−0.0 %"
    expect(pct(0.3, 0, false)).toBe('30 %')
  })

  it('gives direction and rank change as text, not colour alone', () => {
    expect([direction(0.1), direction(-0.1), direction(0), direction(null)]).toEqual(['up', 'down', 'flat', 'flat'])
    expect([rankChange(2), rankChange(-1), rankChange(0), rankChange(null)]).toEqual(['▲2', '▼1', '–', ''])
  })

  it('counts weekdays between two dates', () => {
    expect(weekdaysBetween('2026-11-06', '2026-11-09')).toBe(1) // Friday to Monday
    expect(weekdaysBetween('2026-11-10', '2026-11-10')).toBe(0)
    expect(weekdaysBetween('2026-11-02', '2026-11-13')).toBe(9)
  })
})

describe('sort', () => {
  const rows = [{ t: 'B', v: 2 }, { t: 'A', v: null }, { t: 'C', v: 5 }, { t: 'D', v: 2 }]
  it('sorts both ways, keeps ties in order and puts missing values last', () => {
    expect(sortBy(rows, (r) => r.v, 'desc').map((r) => r.t)).toEqual(['C', 'B', 'D', 'A'])
    expect(sortBy(rows, (r) => r.v, 'asc').map((r) => r.t)).toEqual(['B', 'D', 'C', 'A'])
    expect(sortBy(rows, (r) => r.t, 'desc').map((r) => r.t)).toEqual(['D', 'C', 'B', 'A'])
  })
})

describe('router', () => {
  it('parses a list route with its view state and round-trips it', () => {
    const hash = '#/list/eu_energy?period=1m&sort=dd52:asc'
    const route = parseHash(hash)
    expect(route).toEqual({ view: 'list', id: 'eu_energy', params: { period: '1m', sort: 'dd52:asc' } })
    expect(formatHash(route)).toBe(hash)
  })

  it('knows the other routes and rejects unknown ones', () => {
    expect(parseHash('').view).toBe('candidates')
    expect(parseHash('#/').view).toBe('candidates')
    expect(parseHash('#/screener?sector=Energy')).toEqual({ view: 'screener', params: { sector: 'Energy' } })
    expect(parseHash('#/list')).toEqual({ view: 'list', id: undefined, params: {} })
    expect(parseHash('#/data').view).toBe('data')
    expect(parseHash('#/mix').view).toBe('mix')
    expect(parseHash('#/movers?x=1')).toEqual({ view: 'movers', params: { x: '1' } })
    expect(parseHash('#/list/a/b').view).toBe('notfound')
    expect(parseHash('#/nothing/here').view).toBe('notfound')
    expect(formatHash({ view: 'candidates', params: { period: undefined } })).toBe('#/')
    expect(formatHash({ view: 'list' })).toBe('#/list')
  })
})

describe('research panel address', () => {
  it('opens and closes a company on any view and keeps the other view state', () => {
    const route = parseHash('#/screener?sector=Energy&sort=pe:asc')
    expect(withCompany(route, 'EQNR.OL')).toBe('#/screener?sector=Energy&sort=pe:asc&c=EQNR.OL')
    expect(withCompany(parseHash('#/list/eu_energy?c=EQNR.OL'), undefined)).toBe('#/list/eu_energy')
    expect(withCompany(parseHash('#/'), 'NVDA')).toBe('#/?c=NVDA')
  })
})

describe('treemap', () => {
  const area = (r: { w: number; h: number }) => r.w * r.h
  it('gives every item an area in proportion to its value, inside the box, without overlap', () => {
    const items = [{ key: 'A', value: 40 }, { key: 'B', value: 30 }, { key: 'C', value: 20 }, { key: 'D', value: 10 }, { key: 'Z', value: 0 }]
    const rects = treemap(items, 0, 0, 100, 50)
    expect(rects.map((r) => r.key).sort()).toEqual(['A', 'B', 'C', 'D'])
    for (const r of rects) {
      expect(area(r)).toBeCloseTo((items.find((i) => i.key === r.key)!.value / 100) * 5000, 6)
      expect(r.x).toBeGreaterThanOrEqual(0)
      expect(r.x + r.w).toBeLessThanOrEqual(100 + 1e-9)
      expect(r.y + r.h).toBeLessThanOrEqual(50 + 1e-9)
    }
    for (const a of rects) for (const b of rects) {
      if (a.key < b.key) expect(a.x + a.w <= b.x + 1e-9 || b.x + b.w <= a.x + 1e-9 || a.y + a.h <= b.y + 1e-9 || b.y + b.h <= a.y + 1e-9).toBe(true)
    }
  })
  it('handles one item and none', () => {
    expect(treemap([{ key: 'A', value: 3 }])).toEqual([{ key: 'A', x: 0, y: 0, w: 100, h: 100 }])
    expect(treemap([])).toEqual([])
  })
})
