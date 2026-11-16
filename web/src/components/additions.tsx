// Researchable additions: sector cards, the candidate table and the research basket with before and after.
// The basket only models new money; current holdings are locked. Estimates, not advice.
import { useMemo } from 'react'
import type { Data } from '../data/load'
import { corrToPortfolio, evaluate, type BasketItem } from '../lib/basket'
import { DASH, pct } from '../lib/format'
import { candidatesOf, eur, ETF_CARD, sectorCards, techTickers, usablePe, type Candidate } from '../lib/groups'
import { sortBy } from '../lib/sort'
import { withCompany, type Route } from '../router'
import { InfoTip, Pct } from './bits'

const DEFAULT_AMOUNT = 500
const MAX_SLIDER = 10_000

export function GapCards({ data, selected, onSelect }: { data: Data; selected: string; onSelect: (card: string) => void }) {
  const cards = useMemo(() => sectorCards(data), [data])
  const etfs = data.holdings.etfs.length
  return (
    <div className="gaps" role="group" aria-label="Sector">
      {cards.map((c) => (
        <button key={c.sector} type="button" aria-pressed={selected === c.sector} onClick={() => onSelect(c.sector)}>
          <b>{c.sector}</b>
          <span>{c.count} {c.count === 1 ? 'share' : 'shares'} · forward P/E median {c.medianFwdPe == null ? DASH : c.medianFwdPe.toFixed(1)}</span>
          <span className={c.share === 0 ? 'zero' : undefined}>{c.share === 0 ? 'none in the portfolio' : `${pct(c.share, 0, false)} of the portfolio`}</span>
        </button>
      ))}
      {etfs > 0 && (
        <button type="button" aria-pressed={selected === ETF_CARD} onClick={() => onSelect(ETF_CARD)}>
          <b>ETFs</b>
          <span>{etfs} {etfs === 1 ? 'fund' : 'funds'} · no P/E</span>
          <span>index funds as additions</span>
        </button>
      )}
    </div>
  )
}

export function CandidateTable({ data, card, basket, onAdd, route }: { data: Data; card: string; basket: BasketItem[]; onAdd: (ticker: string) => void; route: Route }) {
  const all = useMemo(() => candidatesOf(data), [data])
  const rows = useMemo(() => {
    const inCard = all.filter((c) => (card === ETF_CARD ? c.kind === 'ETF' : c.kind === 'share' && c.sector === card))
    return card === ETF_CARD ? sortBy(inCard, (c) => c.name, 'asc') : sortBy(inCard, (c) => (usablePe(c.fwd_pe) ? c.fwd_pe : null), 'asc')
  }, [all, card])
  const inBasket = new Set(basket.map((b) => b.ticker))
  const held = new Set(data.holdings.positions.map((p) => p.ticker))
  const researchable = new Set(data.research.companies.map((c) => c.ticker))
  if (rows.length === 0) return <div className="card panel"><p className="muted">No candidates in this group tonight.</p></div>
  const pe = (x: number | null, c: Candidate) => (c.kind === 'ETF' ? 'n/a' : x == null ? DASH : usablePe(x) ? x.toFixed(1) : '⚠')
  return (
    <div className="card scrollx">
      <table className="board dense pf-table">
        <caption className="sr-only">Candidates with return, valuation, volatility and correlation to the portfolio</caption>
        <thead>
          <tr>
            <th scope="col" className="l">Name</th>
            <th scope="col" className="wide">1y</th>
            <th scope="col" className="wide">From high</th>
            <th scope="col" className="wide">P/E</th>
            <th scope="col">Fwd P/E</th>
            <th scope="col" className="wide">Volatility</th>
            <th scope="col">Correlation<InfoTip label="Correlation"><p>How closely this moves with your current holdings, from weekly EUR returns over two years. 1 = together, 0 = unrelated, below 0 = opposite. Shown as a dash when there is too little history.</p></InfoTip></th>
            <th scope="col"><span className="sr-only">Add</span></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((c) => {
            const corr = corrToPortfolio(c.ticker, data.holdings, data.portfolio)
            return (
              <tr key={c.ticker}>
                <th scope="row" className="l name">
                  <b>{researchable.has(c.ticker) ? <a className="clink" href={withCompany(route, c.ticker)}>{c.name}</a> : c.name}</b>
                  <span>{c.ticker} · <span className="tag">{c.kind}</span>{held.has(c.ticker) && <> <span className="tag">held</span></>} · {c.country ?? c.origin}</span>
                </th>
                <td className="wide"><Pct value={c.ret_1y} /></td>
                <td className="wide"><Pct value={c.dd52} /></td>
                <td className="wide num">{pe(c.pe, c)}</td>
                <td className="num" title={c.fwd_pe != null && !usablePe(c.fwd_pe) ? 'looks inconsistent: left out of sorting and medians' : undefined}>{pe(c.fwd_pe, c)}</td>
                <td className="wide num">{c.vol_1y == null ? DASH : pct(c.vol_1y, 0, false)}</td>
                <td className="num">
                  {corr.value == null ? <span title={corr.reason ?? undefined}>{DASH}<span className="sr-only"> {corr.reason}</span></span> : corr.value.toFixed(2).replace('-', '−')}
                </td>
                <td>
                  <button type="button" className="btn small" disabled={inBasket.has(c.ticker)} aria-label={`Add ${c.name} to the basket`} onClick={() => onAdd(c.ticker)}>
                    {inBasket.has(c.ticker) ? 'Added' : '+ Add'}
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function corrText(ticker: string, data: Data): string {
  const c = corrToPortfolio(ticker, data.holdings, data.portfolio)
  return c.value == null ? `correlation: ${DASH} (${c.reason})` : `correlation ${c.value.toFixed(2).replace('-', '−')}`
}

export const newItem = (ticker: string): BasketItem => ({ ticker, amountEur: DEFAULT_AMOUNT })

export function BasketPanel({ data, basket, setBasket }: { data: Data; basket: BasketItem[]; setBasket: (b: BasketItem[]) => void }) {
  const tech = useMemo(() => techTickers(data), [data])
  const names = useMemo(() => new Map(candidatesOf(data).map((c) => [c.ticker, c.name])), [data])
  const before = evaluate(data.holdings, [], data.portfolio, tech)
  const after = evaluate(data.holdings, basket, data.portfolio, tech)
  const total = basket.reduce((s, b) => s + (Number.isFinite(b.amountEur) ? Math.max(0, b.amountEur) : 0), 0)
  const set = (ticker: string, amountEur: number) => setBasket(basket.map((b) => (b.ticker === ticker ? { ticker, amountEur } : b)))
  const largest = (e: typeof before) => Math.max(0, ...Object.values(e.weights))
  const rows: { label: string; a: string; b: string; tip?: string }[] = [
    { label: 'Portfolio value', a: `${eur(before.total)} €`, b: `${eur(after.total)} €` },
    { label: 'Three largest', a: pct(before.top3, 1, false), b: pct(after.top3, 1, false) },
    { label: 'Technology-heavy', a: pct(before.tech, 1, false), b: pct(after.tech, 1, false) },
    { label: 'Largest holding', a: pct(largest(before), 1, false), b: pct(largest(after), 1, false) },
    {
      label: 'Volatility (estimate)', a: before.vol == null ? DASH : pct(before.vol, 1, false), b: after.vol == null ? DASH : pct(after.vol, 1, false),
      tip: 'Annualised, from weekly EUR returns over two years, for the part with price history. An estimate, not a forecast.',
    },
    { label: 'Largest risk share', a: before.topRisk ? `${before.topRisk.key} ${pct(before.topRisk.share, 0, false)}` : DASH, b: after.topRisk ? `${after.topRisk.key} ${pct(after.topRisk.share, 0, false)}` : DASH },
  ]
  return (
    <section aria-labelledby="basket-h" className="pf-basket">
      <div className="sechead">
        <h2 id="basket-h">Research basket</h2>
        <span className="tag">current holdings locked</span>
      </div>
      <div className="card panel">
        {basket.length === 0 ? (
          <div className="state emptybasket">
            <h3>The basket is empty</h3>
            <p className="small">Add a share or an ETF from the list to see how new money would change weights, concentration and risk. Nothing is bought.</p>
          </div>
        ) : (
          <>
            <ul className="basket-items">
              {basket.map((b) => (
                <li key={b.ticker}>
                  <div className="bi-head">
                    <b>{names.get(b.ticker) ?? b.ticker}</b>
                    <span className="small muted bi-corr">{corrText(b.ticker, data)}</span>
                    <button type="button" className="btn icon" aria-label={`Remove ${names.get(b.ticker) ?? b.ticker}`} onClick={() => setBasket(basket.filter((x) => x.ticker !== b.ticker))}>×</button>
                  </div>
                  <div className="bi-amount">
                    <input type="range" aria-label={`Amount for ${b.ticker}`} min={0} max={MAX_SLIDER} step={50} value={Math.min(MAX_SLIDER, Math.max(0, b.amountEur || 0))} onChange={(e) => set(b.ticker, Number(e.target.value))} />
                    <label className="sr-only" htmlFor={`amt-${b.ticker}`}>Amount in EUR for {b.ticker}</label>
                    <input id={`amt-${b.ticker}`} className="num" type="number" inputMode="numeric" min={0} step={50} value={Number.isFinite(b.amountEur) ? b.amountEur : ''} onChange={(e) => set(b.ticker, e.target.value === '' ? Number.NaN : Number(e.target.value))} />
                    <span className="muted small">€</span>
                  </div>
                </li>
              ))}
            </ul>
            <div className="actions">
              <button type="button" className="btn small" onClick={() => setBasket(basket.map((b) => ({ ...b, amountEur: Math.max(50, Math.round(total / basket.length / 50) * 50) })))}>Equal amounts</button>
              <button type="button" className="btn small" onClick={() => setBasket([])}>Clear</button>
              <span className="muted small" style={{ alignSelf: 'center' }}>Basket total {eur(total)} €</span>
            </div>
            {after.ignored.length > 0 && (
              <p className="small muted" role="status">
                Not used: {after.ignored.map((i) => `${i.ticker} (${i.reason})`).join('; ')}.
              </p>
            )}
          </>
        )}
        <table className="board plain dense pf-ba">
          <caption className="sr-only">The portfolio now and with the basket added</caption>
          <thead><tr><th scope="col" className="l">Measure</th><th scope="col">Now</th><th scope="col">With basket</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.label}>
                <th scope="row" className="l">{r.label}{r.tip && <InfoTip label={r.label}><p>{r.tip}</p></InfoTip>}</th>
                <td className="num">{r.a}</td>
                <td className="num">{r.b}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="small muted">
          {after.vol != null && <>Volatility covers {pct(after.volCovered, 0, false)} of the value with the basket. </>}
          Estimates from two years of weekly EUR returns, not forecasts. The basket is an example of how weights shift, not advice.
        </p>
      </div>
    </section>
  )
}
