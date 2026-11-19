import { InfoTip, Pct, State } from '../components/bits'
import { CompanyLink, MEASURES, num, ValuationPill } from '../components/research'
import type { Company, Data } from '../data/load'
import { DASH, pct } from '../lib/format'
import { sortBy, type Dir } from '../lib/sort'
import { replaceRoute, type Route } from '../router'
import { applyFilters, Filters } from './Candidates'

type Col = { key: string; label: string; value: (c: Company) => number | string | null; cls?: string; tip?: string; first?: Dir }

const COLS: Col[] = [
  { key: 'name', label: 'Company', value: (c) => c.name, cls: 'l', first: 'asc' },
  { key: 'ret_1y', label: '1y', value: (c) => c.ret_1y, cls: 'wide' },
  { key: 'dd52', label: 'From high', value: (c) => c.dd52, cls: 'wide', first: 'asc', tip: 'How far the last close is below the highest close of the past 52 weeks.' },
  { key: 'pe', label: 'P/E', value: (c) => c.pe, first: 'asc', tip: 'Price divided by last year’s profit per share.' },
  { key: 'fwd_pe', label: 'Fwd P/E', value: (c) => c.fwd_pe, cls: 'wide', first: 'asc', tip: 'Price divided by next year’s profit per share as analysts expect it.' },
  { key: 'vs_own', label: 'vs own past', value: (c) => c.vs_own, first: 'asc', tip: 'P/E now against the middle of the company’s own P/E at its past fiscal year-ends. Below zero = lower than its own past.' },
  { key: 'vs_sector', label: 'vs peers', value: (c) => c.vs_sector, cls: 'wide', first: 'asc', tip: 'Forward P/E against the middle forward P/E of comparable companies on this page.' },
  { key: 'profit', label: 'Profit yrs', value: (c) => (c.gate.years ? c.gate.profit_years / c.gate.years : null), cls: 'wide', tip: 'Fiscal years with a profit out of the last four on record.' },
  { key: 'valuation', label: 'Valuation', value: (c) => c.vs_own, cls: 'l wide', first: 'asc' },
  ...MEASURES.map((k): Col => ({ key: k, label: { quality: 'Qual', value: 'Val', trend: 'Trend', steady: 'Steady' }[k], value: (c) => c.measures[k], cls: 'wide m' })),
]

export default function Screener({ data, route }: { data: Data; route: Route }) {
  const all = data.research.companies
  const [rawKey, rawDir] = (route.params.sort ?? '').split(':')
  const col = COLS.find((c) => c.key === rawKey) ?? COLS[5]
  const dir: Dir = rawDir === 'asc' || rawDir === 'desc' ? rawDir : col.first ?? 'desc'
  const rows = sortBy(applyFilters(all, route), col.value, dir)
  const sortOn = (c: Col) =>
    replaceRoute({ view: 'screener', params: { ...route.params, sort: `${c.key}:${c.key === col.key ? (dir === 'asc' ? 'desc' : 'asc') : c.first ?? 'desc'}` } })
  const low = all.filter((c) => c.valuation === 'low for it')
  const fell = all.filter((c) => c.dd52 != null && c.dd52 <= -0.2)
  const kpis: [string, string | number][] = [
    ['Companies', all.length], ['Low against own past P/E', low.length], ['Fell more than 20 % from high', fell.length],
    ['Both', low.filter((c) => fell.includes(c)).length], ['Pass the profit rule', data.research.gate_passed],
  ]
  return (
    <>
      <div className="pagehead">
        <div>
          <h1>Screener</h1>
          <p className="muted small">Every company once, with its valuation figures. Click a name for the full picture.</p>
        </div>
        <Filters data={data} route={route} />
      </div>
      <dl className="kpis">{kpis.map(([k, v]) => <div key={k}><dt>{k}</dt><dd className="num">{v}</dd></div>)}</dl>
      {rows.length === 0 ? <State title="No company matches these filters"><p>Clear a filter to see more.</p></State> : (
        <div className="card scrollx">
          <table className="board dense">
            <caption className="sr-only">All companies with valuation figures and measure ranks</caption>
            <thead>
              <tr>
                {COLS.map((c) => (
                  <th key={c.key} scope="col" className={c.cls} aria-sort={c.key === col.key ? (dir === 'asc' ? 'ascending' : 'descending') : undefined}>
                    <button type="button" onClick={() => sortOn(c)}>{c.label}</button>
                    {c.tip && <InfoTip label={c.label}><p>{c.tip}</p></InfoTip>}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.ticker} className={c.stale ? 'stale' : route.params.c === c.ticker ? 'selrow' : undefined}>
                  <th scope="row" className="l name"><b><CompanyLink c={c} route={route} /></b><span>{c.ticker}{c.place ? ` · shortlist ${c.place}` : ''}</span></th>
                  <td className="wide"><Pct value={c.ret_1y} /></td>
                  <td className="wide"><Pct value={c.dd52} /></td>
                  <td className="num">{num(c.pe)}</td>
                  <td className="wide num">{num(c.fwd_pe)}</td>
                  <td className="num">{pct(c.vs_own, 0)}</td>
                  <td className="wide num">{pct(c.vs_sector, 0)}</td>
                  <td className="wide num">{c.gate.years ? `${c.gate.profit_years}/${c.gate.years}` : DASH}</td>
                  <td className="l wide"><ValuationPill c={c} /></td>
                  {MEASURES.map((k) => <td key={k} className="wide num m">{c.measures[k] ?? DASH}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="under">
        Qual, Val, Trend, Steady are ranks from 0 to 100 among these companies (100 = best); see Candidates for what has been
        tested. A lower P/E is not by itself a reason: read the caveats in each company&rsquo;s panel. Educational, not advice.
      </p>
    </>
  )
}
