// Test mixes live in the browser only (localStorage) and in files the owner exports. Nothing is uploaded.
import type { MixItem } from './mix'

export interface Mix {
  name: string
  items: MixItem[]
}
export interface Saved {
  a: Mix
  b: Mix | null
}

const KEY = 'market-leaderboard.mixes.v1'
const FILE_MARK = 'market_leaderboard_mix'
const MAX_ITEMS = 200
export const EMPTY: Saved = { a: { name: 'Mix A', items: [] }, b: null }

/** A valid mix, or null. Files and stored text are untrusted: every field is checked. */
export function asMix(x: unknown): Mix | null {
  if (typeof x !== 'object' || x === null) return null
  const { name, items } = x as { name?: unknown; items?: unknown }
  if (typeof name !== 'string' || !Array.isArray(items) || items.length > MAX_ITEMS) return null
  const out: MixItem[] = []
  for (const it of items) {
    const { ticker, weight } = (it ?? {}) as { ticker?: unknown; weight?: unknown }
    if (typeof ticker !== 'string' || !ticker || ticker.length > 20) return null
    if (typeof weight !== 'number' || !Number.isFinite(weight) || weight < 0) return null
    out.push({ ticker, weight })
  }
  return { name: name.slice(0, 40), items: out }
}

export function load(storage: Pick<Storage, 'getItem'> | undefined = globalThis.localStorage): Saved {
  try {
    const raw = JSON.parse(storage?.getItem(KEY) ?? 'null') as { a?: unknown; b?: unknown } | null
    const a = asMix(raw?.a)
    if (!a) return EMPTY
    return { a, b: asMix(raw?.b) }
  } catch {
    return EMPTY // corrupt or blocked storage: start empty rather than fail
  }
}

export function save(saved: Saved, storage: Pick<Storage, 'setItem'> | undefined = globalThis.localStorage): void {
  try {
    storage?.setItem(KEY, JSON.stringify(saved))
  } catch {
    // storage full or blocked: the mix still works for this visit
  }
}

export function toFile(mix: Mix): string {
  return JSON.stringify({ [FILE_MARK]: 1, ...mix }, null, 1)
}

/** Read an exported mix file. Throws a message the page can show as it is. */
export function fromFile(text: string): Mix {
  let parsed: unknown
  try {
    parsed = JSON.parse(text)
  } catch {
    throw new Error('This file is not a mix file (it is not valid JSON).')
  }
  const mix = (parsed as Record<string, unknown> | null)?.[FILE_MARK] === 1 ? asMix(parsed) : null
  if (!mix) throw new Error('This file is not a mix file exported from this page.')
  return mix
}
