import { describe, expect, it } from 'vitest'
import fixture from '../fixtures/news30.json'
import { balanceWord, countLabel, isNews30 } from './news'

describe('news30', () => {
  it('accepts the demo fixture and rejects other payloads', () => {
    expect(isNews30(fixture)).toBe(true)
    expect(isNews30({ ...fixture, schema_version: 3 })).toBe(false)
    expect(isNews30(null)).toBe(false)
    expect(isNews30({ schema_version: 4 })).toBe(false)
  })
  it('marks a full feed as a minimum', () => {
    expect(countLabel({ count: 100, capped: true })).toBe('100+')
    expect(countLabel({ count: 14, capped: false })).toBe('14')
  })
  it('puts the balance in words', () => {
    expect(balanceWord(0.5)).toBe('more upbeat than downbeat')
    expect(balanceWord(-0.5)).toBe('more downbeat than upbeat')
    expect(balanceWord(0.1)).toBe('about even')
    expect(balanceWord(null)).toBe('no upbeat or downbeat story')
  })
})
