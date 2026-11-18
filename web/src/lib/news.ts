// Optional file: scripts/news30.py writes data/news30.json for the shares in config/portfolio.toml.
// A missing or invalid file is not an error; the page then says how to create it.
import type { News30 } from '../data/generated/news30.schema'

export type { Company as NewsCompany, Item as NewsItem, News30 } from '../data/generated/news30.schema'

export function isNews30(x: unknown): x is News30 {
  const n = x as Partial<News30> | null
  return !!n && n.schema_version === 3 && Array.isArray(n.companies) && Array.isArray(n.failed)
}

export async function loadNews(): Promise<News30 | null> {
  try {
    const payload: unknown = import.meta.env?.VITE_FIXTURES === '1'
      ? (await import('../fixtures/news30.json')).default
      : await (await fetch('data/news30.json', { cache: 'no-store' })).json()
    return isNews30(payload) ? payload : null
  } catch {
    return null
  }
}

/** The count as shown: a full feed (100 items) is "100+" because the real number is not known. */
export const countLabel = (c: { count: number; capped: boolean }) => (c.capped ? `${c.count}+` : String(c.count))
