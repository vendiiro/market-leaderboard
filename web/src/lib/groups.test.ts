import { describe, expect, it } from 'vitest'
import type { Data, Position } from '../data/load'
import holdings from '../fixtures/holdings.json'
import leaderboard from '../fixtures/leaderboard.json'
import { eur, groupLabel, techTickers } from './groups'

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
