import { describe, expect, it } from 'vitest'
import { checked, loadAll, type Data } from './data/load'
import leaderboard from './fixtures/leaderboard.json'
import meta from './fixtures/meta.json'
import movers from './fixtures/movers.json'
import portfolio from './fixtures/portfolio.json'
import { direction, pct, rankChange, weekdaysBetween } from './lib/format'
import { sortBy } from './lib/sort'
import { formatHash, parseHash } from './router'

const fixtures = { meta, leaderboard, movers, portfolio } as Record<keyof Data, unknown>

describe('data loading', () => {
  it('returns the four typed files from the fixtures', async () => {
    const data = await loadAll(async (name) => fixtures[name])
    expect(data.meta.demo).toBe(true)
    expect(data.leaderboard.lists.map((l) => l.key)).toEqual(['us_big_tech', 'eu_defence', 'eu_energy', 'nordic_energy', 'fi_small'])
    expect(data.portfolio.cov.length).toBe(data.portfolio.risk_tickers.length)
  })

  it('rejects a wrong or missing schema version with a readable message', async () => {
    await expect(loadAll(async (name) => (name === 'movers' ? { ...movers, schema_version: 2 } : fixtures[name]))).rejects.toThrow(
      /movers\.json has schema version 2, this page needs 1/,
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
    expect(parseHash('').view).toBe('overview')
    expect(parseHash('#/').view).toBe('overview')
    expect(parseHash('#/mix').view).toBe('mix')
    expect(parseHash('#/movers?x=1')).toEqual({ view: 'movers', params: { x: '1' } })
    expect(parseHash('#/list').view).toBe('notfound')
    expect(parseHash('#/nothing/here').view).toBe('notfound')
    expect(formatHash({ view: 'overview', params: { period: undefined } })).toBe('#/')
  })
})
