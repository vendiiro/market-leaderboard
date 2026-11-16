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

export function median(xs: number[]): number | null {
  if (xs.length === 0) return null
  const s = [...xs].sort((a, b) => a - b)
  const m = s.length >> 1
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2
}

/** A forward P/E the page may use: above zero and not above 300 (the consistency rule of the workstation spec). */
export const usablePe = (x: number | null | undefined): x is number => x != null && x > 0 && x <= 300

export interface SectorCard {
  sector: string
  count: number // shares in the dashboard's universe, each counted once
  medianFwdPe: number | null // of the consistent forward P/E values
  share: number // share of the portfolio held in this sector (0 to 1)
}

/** One card per sector, sectors with nothing held first, then by number of shares. */
export function sectorCards(data: Pick<Data, 'holdings' | 'leaderboard'>): SectorCard[] {
  const seen = new Map<string, { sector: string; fwd: number | null }>()
  for (const l of data.leaderboard.lists) for (const r of l.rows) if (r.sector && !seen.has(r.ticker)) seen.set(r.ticker, { sector: r.sector, fwd: r.fwd_pe })
  const held = new Map<string, number>()
  for (const p of data.holdings.positions) if (p.sector && p.weight != null) held.set(p.sector, (held.get(p.sector) ?? 0) + p.weight)
  const bySector = new Map<string, (number | null)[]>()
  for (const { sector, fwd } of seen.values()) bySector.set(sector, [...(bySector.get(sector) ?? []), fwd])
  return [...bySector]
    .map(([sector, fwds]) => ({ sector, count: fwds.length, medianFwdPe: median(fwds.filter(usablePe)), share: held.get(sector) ?? 0 }))
    .sort((a, b) => a.share - b.share || b.count - a.count || a.sector.localeCompare(b.sector))
}

export interface Candidate {
  ticker: string
  name: string
  kind: 'share' | 'ETF'
  sector: string | null
  country: string | null
  origin: string // the watchlists the share is on, or the ETF list
  ret_1y: number | null
  dd52: number | null
  pe: number | null
  fwd_pe: number | null
  vol_1y: number | null
}

export const ETF_CARD = '__etf'

/** Every share in the universe once (first list wins), then the ETF candidates. */
export function candidatesOf(data: Pick<Data, 'holdings' | 'leaderboard'>): Candidate[] {
  const out = new Map<string, Candidate>()
  for (const l of data.leaderboard.lists)
    for (const r of l.rows) {
      const hit = out.get(r.ticker)
      if (hit) hit.origin += `, ${l.name}`
      else out.set(r.ticker, { ticker: r.ticker, name: r.name, kind: 'share', sector: r.sector ?? null, country: r.country ?? null, origin: l.name, ret_1y: r.ret_1y, dd52: r.dd52, pe: r.pe, fwd_pe: r.fwd_pe, vol_1y: r.vol_1y })
    }
  for (const e of data.holdings.etfs)
    if (!out.has(e.ticker)) out.set(e.ticker, { ticker: e.ticker, name: e.name, kind: 'ETF', sector: null, country: null, origin: e.list_name, ret_1y: e.ret_1y, dd52: e.dd52, pe: null, fwd_pe: null, vol_1y: e.vol_1y })
  return [...out.values()]
}

/** 12,345.68 ; a real minus sign; a plus sign when `signed`; a dash for missing. */
export function eur(x: number | null | undefined, digits = 0, signed = false): string {
  if (x == null || !Number.isFinite(x)) return '—'
  const s = new Intl.NumberFormat('en-GB', { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(Math.abs(x))
  return (x < 0 ? '−' : signed && x > 0 ? '+' : '') + s
}
