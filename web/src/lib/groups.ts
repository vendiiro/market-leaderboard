// Small helpers for the Portfolio page: which tickers count as technology-heavy, the label of a position's group,
// and EUR formatting. No financial arithmetic here beyond rounding for display.
import type { Data, Position } from '../data/load'

const TECH_SECTORS = new Set(['Technology', 'Communication Services'])

/** Tickers that count as technology-heavy for a basket: shares in the Technology or Communication Services sector,
 *  and ETFs whose entry in config/watchlists.toml carries group = "technology". Holdings use their own `group` tag. */
export function techTickers(data: Pick<Data, 'holdings' | 'leaderboard'>): Set<string> {
  const out = new Set<string>()
  for (const l of data.leaderboard.lists) for (const r of l.rows) if (r.sector && TECH_SECTORS.has(r.sector)) out.add(r.ticker)
  for (const e of data.holdings.etfs) if (e.group === 'technology') out.add(e.ticker)
  return out
}

const KIND_LABEL: Record<Position['kind'], string> = { stock: 'Other shares', etf: 'ETFs', etn: 'ETNs', fund: 'Funds' }

export function groupLabel(p: Pick<Position, 'kind' | 'group'>): string {
  if (p.group) return p.group.charAt(0).toUpperCase() + p.group.slice(1)
  return KIND_LABEL[p.kind]
}

/** 12,345.68 ; a real minus sign; a plus sign when `signed`; a dash for missing. */
export function eur(x: number | null | undefined, digits = 0, signed = false): string {
  if (x == null || !Number.isFinite(x)) return '—'
  const s = new Intl.NumberFormat('en-GB', { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(Math.abs(x))
  return (x < 0 ? '−' : signed && x > 0 ? '+' : '') + s
}
