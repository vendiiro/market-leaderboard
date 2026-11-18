import { describe, expect, it } from 'vitest'
import fixture from '../fixtures/news30.json'
import { countLabel, isNews30 } from './news'

describe('news30', () => {
  it('accepts the demo fixture and rejects other payloads', () => {
    expect(isNews30(fixture)).toBe(true)
    expect(isNews30({ ...fixture, schema_version: 2 })).toBe(false)
    expect(isNews30(null)).toBe(false)
    expect(isNews30({ schema_version: 3 })).toBe(false)
  })
  it('marks a full feed as a minimum', () => {
    expect(countLabel({ count: 100, capped: true })).toBe('100+')
    expect(countLabel({ count: 14, capped: false })).toBe('14')
  })
})
