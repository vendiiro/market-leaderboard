// The only financial arithmetic in the browser: weighted sums and w'Σw on numbers the engine supplies.
// Reference versions are in engine/portfolio.py; mix.test.ts checks these against its fixture.
import type { Portfolio } from '../data/load'

export type Weights = Record<string, number>
export type ExposureKey = 'sector' | 'country' | 'currency' | 'lists'
export interface TickerMeta {
  sector: string | null
  country: string | null
  currency: string | null
  lists: string[]
}

/** Scale weights to sum to 1. Weights must be non-negative and not all zero. */
export function normalise(weights: Weights): Weights {
  const entries = Object.entries(weights)
  const total = entries.reduce((s, [, w]) => s + w, 0)
  if (!(total > 0) || entries.some(([, w]) => !(w >= 0))) throw new Error('Weights must be zero or more and add up to more than zero.')
  return Object.fromEntries(entries.map(([t, w]) => [t, w / total]))
}

/** Share of the mix per group. A ticker on two lists counts in both, so list shares can add up to more than 1. */
export function exposure(weights: Weights, meta: Record<string, TickerMeta>, key: ExposureKey): Record<string, number> {
  const out: Record<string, number> = {}
  for (const [t, w] of Object.entries(normalise(weights))) {
    const groups = key === 'lists' ? meta[t].lists : [meta[t][key] ?? 'Unknown']
    for (const g of groups) out[g] = (out[g] ?? 0) + w
  }
  return out
}

/** (Σw)_i for each ticker of the mix; `order` gives the row and column order of `cov`. */
function covTimesWeights(w: Weights, order: string[], cov: number[][]): Record<string, number> {
  const index = new Map(order.map((t, i) => [t, i]))
  const names = Object.keys(w)
  for (const t of names) if (!index.has(t)) throw new Error(`No risk data for ${t}.`)
  return Object.fromEntries(names.map((a) => [a, names.reduce((s, b) => s + cov[index.get(a)!][index.get(b)!] * w[b], 0)]))
}

function variance(w: Weights, sw: Record<string, number>): number {
  return Object.keys(w).reduce((s, t) => s + w[t] * sw[t], 0)
}

/** Mix volatility sqrt(w'Σw). */
export function portfolioVol(weights: Weights, order: string[], cov: number[][]): number {
  const w = normalise(weights)
  return Math.sqrt(variance(w, covTimesWeights(w, order, cov)))
}

/** Each name's share of the mix variance, w_i (Σw)_i / (w'Σw); sums to 1. */
export function riskContribution(weights: Weights, order: string[], cov: number[][]): Record<string, number> {
  const w = normalise(weights)
  const sw = covTimesWeights(w, order, cov)
  const v = variance(w, sw)
  return Object.fromEntries(Object.keys(w).map((t) => [t, v > 0 ? (w[t] * sw[t]) / v : 0]))
}

/** Effective number of names 1 / Σw²: 1 for a single name, n for n equal weights. */
export function effectiveN(weights: Weights): number {
  return 1 / Object.values(normalise(weights)).reduce((s, w) => s + w * w, 0)
}

export interface MixItem {
  ticker: string
  weight: number
}
export interface Analysis {
  weights: Weights // normalised, only tickers that have data tonight
  missing: string[] // in the mix but not in tonight's data
  exposure: Record<ExposureKey, Record<string, number>>
  effectiveN: number
  risk: null | {
    tickers: string[] // the part of the mix that has risk data
    covered: number // share of the mix (by weight) that the risk numbers describe
    vol: number
    contribution: Record<string, number>
    weights: Weights // weights within the covered part (sum to 1)
  }
  noRisk: { ticker: string; reason: string }[]
}

/** Everything the mix view shows, or null for a mix with nothing usable. Never returns NaN: problems are named. */
export function analyse(items: MixItem[], portfolio: Portfolio): Analysis | null {
  const meta = Object.fromEntries(portfolio.tickers.map((t) => [t.ticker, t]))
  const usable = items.filter((i) => Number.isFinite(i.weight) && i.weight > 0)
  const missing = usable.filter((i) => !meta[i.ticker]).map((i) => i.ticker)
  const known: Weights = {}
  for (const i of usable) if (meta[i.ticker]) known[i.ticker] = (known[i.ticker] ?? 0) + i.weight
  if (Object.keys(known).length === 0) return null
  const weights = normalise(known)
  const risky = new Set(portfolio.risk_tickers)
  const reasons = new Map(portfolio.no_risk_data.map((x) => [x.ticker, x.reason]))
  const riskTickers = Object.keys(weights).filter((t) => risky.has(t))
  const sub: Weights = Object.fromEntries(riskTickers.map((t) => [t, weights[t]]))
  return {
    weights,
    missing,
    exposure: {
      sector: exposure(weights, meta, 'sector'),
      country: exposure(weights, meta, 'country'),
      currency: exposure(weights, meta, 'currency'),
      lists: exposure(weights, meta, 'lists'),
    },
    effectiveN: effectiveN(weights),
    risk: riskTickers.length
      ? {
          tickers: riskTickers,
          covered: riskTickers.reduce((s, t) => s + weights[t], 0),
          vol: portfolioVol(sub, portfolio.risk_tickers, portfolio.cov),
          contribution: riskContribution(sub, portfolio.risk_tickers, portfolio.cov),
          weights: normalise(sub),
        }
      : null,
    noRisk: Object.keys(weights).filter((t) => !risky.has(t)).map((t) => ({ ticker: t, reason: reasons.get(t) ?? 'no risk data' })),
  }
}
