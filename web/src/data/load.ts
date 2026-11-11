// Loads the four JSON files the engine writes. Types are generated from schemas/ (npm run gen:types).
import type { Leaderboard } from './generated/leaderboard.schema'
import type { Meta } from './generated/meta.schema'
import type { Movers } from './generated/movers.schema'
import type { Portfolio } from './generated/portfolio.schema'

export type { Leaderboard, Period, Row, Watchlist } from './generated/leaderboard.schema'
export type { Meta } from './generated/meta.schema'
export type { Movers } from './generated/movers.schema'
export type { Portfolio } from './generated/portfolio.schema'

export const SCHEMA_VERSION = 1
export interface Data {
  meta: Meta
  leaderboard: Leaderboard
  movers: Movers
  portfolio: Portfolio
}
export type ReadJson = (name: keyof Data) => Promise<unknown>

/** The page and the data must speak the same schema version; anything else is a clear error, not a broken table. */
export function checked<T>(name: string, payload: unknown): T {
  const version = (payload as { schema_version?: unknown } | null)?.schema_version
  if (version !== SCHEMA_VERSION) {
    throw new Error(
      `${name}.json has schema version ${version === undefined ? 'missing' : String(version)}, this page needs ${SCHEMA_VERSION}. ` +
        'Rebuild the data (python -m engine build) or the page (npm run build) so they match.',
    )
  }
  return payload as T
}

const fromServer: ReadJson = async (name) => {
  const res = await fetch(`data/${name}.json`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`data/${name}.json could not be loaded (HTTP ${res.status}). Run the data build first.`)
  return res.json()
}

// Demo data for development and browser tests: VITE_FIXTURES=1, or a dev server with an empty public/data.
const fromFixtures: ReadJson = async (name) => (await import(`../fixtures/${name}.json`)).default

export async function loadAll(read?: ReadJson): Promise<Data> {
  const source = read ?? (import.meta.env?.VITE_FIXTURES === '1' ? fromFixtures : fromServer)
  const names = ['meta', 'leaderboard', 'movers', 'portfolio'] as const
  let payloads: unknown[]
  try {
    payloads = await Promise.all(names.map(source))
  } catch (e) {
    if (read || source === fromFixtures || !import.meta.env?.DEV) throw e
    payloads = await Promise.all(names.map(fromFixtures)) // dev server without live data
  }
  const [meta, leaderboard, movers, portfolio] = payloads
  return {
    meta: checked<Meta>('meta', meta),
    leaderboard: checked<Leaderboard>('leaderboard', leaderboard),
    movers: checked<Movers>('movers', movers),
    portfolio: checked<Portfolio>('portfolio', portfolio),
  }
}
