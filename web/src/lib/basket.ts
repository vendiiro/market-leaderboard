// Before and after for the research basket. Reference version: engine/holdings.py (evaluate_basket); basket.test.ts
// checks this file against its fixture. Current holdings are locked: their EUR value is fixed and only new money is
// modelled. Estimates from two years of weekly EUR returns, not forecasts. The numbers are never NaN: problems are named.
import type { Holdings, Portfolio } from '../data/load'
import { portfolioVol, riskContribution, type Weights } from './mix'

export interface BasketItem {
  ticker: string
  amountEur: number
}
export interface Evaluation {
  total: number // EUR value of the priced holdings plus the valid basket amounts
  weights: Record<string, number> // share of total, by position key (a ticker, or "fund:<name>")
  top3: number // share of the three largest
  tech: number // share tagged technology (holdings by their group tag, basket tickers by the set given)
  vol: number | null // annualised, over the part with risk data (weights renormalised); null when none has it
  volCovered: number // share of total value that vol describes
  topRisk: { key: string; share: number } | null // largest share of the variance
  ignored: { ticker: string; reason: string }[] // basket items that were not used, with why
}

/** Evaluate the portfolio with `basket` added. An empty basket gives the "before" numbers. */
export function evaluate(h: Holdings, basket: BasketItem[], portfolio: Portfolio, techTickers: ReadonlySet<string>): Evaluation {
  const values = new Map<string, number>()
  const info = new Map<string, { ticker: string | null; group: string | null }>()
  const added = new Set<string>() // basket tickers that are not holdings: tagged through the technology set
  for (const p of h.positions) {
    if (p.value_eur == null) continue
    values.set(p.key, p.value_eur)
    info.set(p.key, { ticker: p.ticker, group: p.group })
  }
  const known = new Set(portfolio.tickers.map((t) => t.ticker))
  const ignored: Evaluation['ignored'] = []
  for (const b of basket) {
    if (!Number.isFinite(b.amountEur) || b.amountEur <= 0) {
      ignored.push({ ticker: b.ticker, reason: 'the amount must be a number above zero' })
    } else if (!known.has(b.ticker)) {
      ignored.push({ ticker: b.ticker, reason: 'no data for this ticker tonight' })
    } else {
      values.set(b.ticker, (values.get(b.ticker) ?? 0) + b.amountEur)
      if (!info.has(b.ticker)) {
        info.set(b.ticker, { ticker: b.ticker, group: null })
        added.add(b.ticker)
      }
    }
  }
  const total = [...values.values()].reduce((s, v) => s + v, 0)
  const empty: Evaluation = { total: 0, weights: {}, top3: 0, tech: 0, vol: null, volCovered: 0, topRisk: null, ignored }
  if (!(total > 0)) return empty

  const weights = Object.fromEntries([...values].map(([k, v]) => [k, v / total]))
  const top3 = Object.values(weights).sort((a, b) => b - a).slice(0, 3).reduce((s, w) => s + w, 0)
  const tech = [...values].reduce((s, [k, v]) => {
    const i = info.get(k)!
    // a holding counts by its own tag only; a new basket ticker counts when it is in the technology set
    return i.group === 'technology' || (added.has(k) && i.ticker != null && techTickers.has(i.ticker)) ? s + v / total : s
  }, 0)

  const risky = new Set(portfolio.risk_tickers)
  const sub: Weights = {}
  for (const [k, v] of values) {
    const t = info.get(k)!.ticker
    if (t != null && risky.has(t)) sub[t] = (sub[t] ?? 0) + v
  }
  const riskValue = Object.values(sub).reduce((s, v) => s + v, 0)
  if (!(riskValue > 0)) return { ...empty, total, weights, top3, tech }
  const contribution = riskContribution(sub, portfolio.risk_tickers, portfolio.cov)
  const topKey = Object.keys(contribution).reduce((a, b) => (contribution[b] > contribution[a] ? b : a))
  return {
    total, weights, top3, tech, ignored,
    vol: portfolioVol(sub, portfolio.risk_tickers, portfolio.cov),
    volCovered: riskValue / total,
    topRisk: { key: topKey, share: contribution[topKey] },
  }
}

/** Correlation of one ticker's weekly EUR returns with the current holdings (value-weighted, the part with risk data).
 *  `value` is null with a plain `reason` when either side lacks risk data. */
export function corrToPortfolio(ticker: string, h: Holdings, portfolio: Portfolio): { value: number | null; reason: string | null } {
  const index = new Map(portfolio.risk_tickers.map((t, i) => [t, i]))
  const i = index.get(ticker)
  if (i === undefined) {
    const why = portfolio.no_risk_data.find((x) => x.ticker === ticker)?.reason
    return { value: null, reason: why ? `no risk data: ${why}` : 'no risk data for this ticker' }
  }
  const w: Weights = {}
  for (const p of h.positions) {
    if (p.value_eur != null && p.ticker != null && index.has(p.ticker)) w[p.ticker] = (w[p.ticker] ?? 0) + p.value_eur
  }
  const total = Object.values(w).reduce((s, v) => s + v, 0)
  if (!(total > 0)) return { value: null, reason: 'no holdings with risk data to compare with' }
  const cov = portfolio.cov
  let covTP = 0
  let varP = 0
  for (const [a, va] of Object.entries(w)) {
    const ia = index.get(a)!
    covTP += (va / total) * cov[i][ia]
    for (const [b, vb] of Object.entries(w)) varP += (va / total) * (vb / total) * cov[ia][index.get(b)!]
  }
  const sd = Math.sqrt(cov[i][i]) * Math.sqrt(varP)
  if (!(sd > 0)) return { value: null, reason: 'no variation to compare' }
  return { value: Math.max(-1, Math.min(1, covTP / sd)), reason: null }
}
