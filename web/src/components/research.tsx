// Pieces of the research view shared by Candidates, Screener and the panel. Every figure comes from research.json.
import { useEffect, useRef } from 'react'
import type { Company, Data } from '../data/load'
import { DASH, pct } from '../lib/format'
import { withCompany, type Route } from '../router'
import { InfoTip, Pct, Sparkline } from './bits'

export const MEASURES = ['quality', 'value', 'trend', 'steady'] as const
export const num = (x: number | null | undefined, digits = 1) => (x == null ? DASH : x.toFixed(digits))

const GUIDE: Record<(typeof MEASURES)[number], string> = {
  quality: 'How profitable the business is and how much debt it carries, compared with the other companies here.',
  value: 'How the price compares with profit: against the company’s own past year-ends, against comparable companies, and on EV/EBITDA.',
  trend: 'The share’s return over the past 12 months, leaving out the latest month.',
  steady: 'How seldom the share makes a move of 5 % or more on a day when its market index is calm.',
}

export function ValuationPill({ c }: { c: Company }) {
  const cls = c.valuation === 'low for it' ? 'low' : c.valuation === 'high for it' ? 'high' : 'mid'
  return <span className={`pill ${cls}`}>{c.valuation === 'no data' ? 'No comparison' : c.valuation[0].toUpperCase() + c.valuation.slice(1)}</span>
}

/** Rank bars, 100 = best in the universe. The number is printed, so the bar is never the only carrier. */
export function MeasureBars({ c, data }: { c: Company; data: Data }) {
  return (
    <dl className="measures">
      {MEASURES.map((k) => (
        <div key={k}>
          <dt>
            {data.research.labels[k]}
            <InfoTip label={data.research.labels[k]}>
              <p>{GUIDE[k]}</p>
              <p className="muted">Rank among {data.research.companies.length} companies, 100 = best. {data.research.evidence[k]?.text ?? 'Not tested on these companies.'}</p>
            </InfoTip>
          </dt>
          <dd>
            <span className="mbar" aria-hidden="true"><i style={{ width: `${c.measures[k] ?? 0}%` }} /></span>
            <span className="num">{c.measures[k] ?? DASH}</span>
          </dd>
        </div>
      ))}
    </dl>
  )
}

/** A number line: grey marks for the comparison values, a dark mark for the value now. */
export function Strip({ now, marks, label, lo, mid, hi }: { now: number | null; marks: number[]; label: string; lo: string; mid: string; hi: string }) {
  const all = [...marks, ...(now == null ? [] : [now])]
  if (all.length < 2) return <p className="muted small">Not enough data for this comparison.</p>
  const min = Math.min(...all)
  const span = Math.max(...all) - min || 1
  const at = (v: number) => `${2 + ((v - min) / span) * 96}%`
  return (
    <div role="img" aria-label={label}>
      <div className="strip">
        {marks.map((m, i) => <b key={i} style={{ left: at(m) }} />)}
        {now != null && <u style={{ left: at(now) }} />}
      </div>
      <div className="striplabels"><span>{lo}</span><span>{mid}</span><span>{hi}</span></div>
    </div>
  )
}

export function OwnPastStrip({ c }: { c: Company }) {
  const pes = c.own_pes.map((x) => x.pe)
  return (
    <Strip now={c.inconsistent.includes('pe') ? null : c.pe} marks={pes}
      label={`P/E now ${num(c.pe)} against ${pes.length} past fiscal year-ends from ${num(Math.min(...pes))} to ${num(Math.max(...pes))}`}
      lo={`low ${num(Math.min(...pes, c.pe ?? Infinity))}`} mid={`now ${num(c.pe)} · middle ${num(c.own_mid)}`} hi={`high ${num(Math.max(...pes, c.pe ?? -Infinity))}`} />
  )
}

const NUMBERS: { key: keyof Company; label: string; guide: string; fmt: (v: number) => string }[] = [
  { key: 'pe', label: 'P/E', guide: 'Price divided by last year’s profit per share. 20 means the price equals 20 years of that profit.', fmt: (v) => v.toFixed(1) },
  { key: 'fwd_pe', label: 'Forward P/E', guide: 'The same, using next year’s profit as analysts expect it. An estimate that can change.', fmt: (v) => v.toFixed(1) },
  { key: 'ev_ebitda', label: 'EV/EBITDA', guide: 'The whole company including its debt, against operating profit before depreciation. Compares companies with different debt.', fmt: (v) => v.toFixed(1) },
  { key: 'pb', label: 'P/B', guide: 'Price against the accounting value of what the company owns. High for companies with few physical assets.', fmt: (v) => v.toFixed(1) },
  { key: 'margin', label: 'Profit margin', guide: 'Share of sales left as profit.', fmt: (v) => pct(v, 0, false) },
  { key: 'roe', label: 'Return on equity', guide: 'Yearly profit against the owners’ capital. Above 100 % usually means very little capital on the books, so it is treated as distorted.', fmt: (v) => pct(v, 0, false) },
  { key: 'debt_equity', label: 'Debt to equity', guide: 'Debt for each 100 of the owners’ capital.', fmt: (v) => v.toFixed(0) },
  { key: 'revenue_growth', label: 'Revenue growth', guide: 'Change in sales against a year earlier.', fmt: (v) => pct(v, 0) },
  { key: 'earnings_growth', label: 'Earnings growth', guide: 'Change in profit against a year earlier.', fmt: (v) => pct(v, 0) },
]

export function CompanyLink({ c, route, children }: { c: Pick<Company, 'ticker' | 'name'>; route: Route; children?: React.ReactNode }) {
  return <a className="clink" href={withCompany(route, c.ticker)}>{children ?? c.name}</a>
}

export function ResearchPanel({ c, data, route }: { c: Company; data: Data; route: Route }) {
  const close = useRef<HTMLAnchorElement>(null)
  const listName = new Map(data.leaderboard.lists.map((l) => [l.key, l.name]))
  useEffect(() => {
    close.current?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && (window.location.hash = withCompany(route, undefined))
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [c.ticker, route])
  const peers = c.sector_marks
  return (
    <aside className="rpanel" aria-label={`Research: ${c.name}`}>
      <div className="rhead">
        <div>
          <h2>{c.name}</h2>
          <p className="muted small">{[c.ticker, c.sector, c.country, c.currency].filter(Boolean).join(' · ')}</p>
        </div>
        <a ref={close} className="btn icon" href={withCompany(route, undefined)} aria-label="Close research panel">×</a>
      </div>
      <p className="small">
        {c.place ? <b>On tonight&rsquo;s shortlist, place {c.place} of {data.research.shortlist.length}. </b>
          : c.gate.status === 'pass' ? 'Not on tonight’s shortlist. ' : c.gate.status === 'fail'
            ? `Not a candidate: profitable in ${c.gate.profit_years} of its last ${c.gate.years} fiscal years. ` : `Not a candidate: only ${c.gate.years} fiscal years of statements. `}
        <Pct value={c.dd52} /> from its 52-week high · 1y volatility {pct(c.vol_1y, 0, false)} · 1y return <Pct value={c.ret_1y} />
      </p>
      <Sparkline values={c.spark} width={340} height={44} />
      {c.events.length > 0 && <p className="events">{c.events.map((e) => <span key={e} className="pill mid">{e}</span>)}</p>}

      <h3>Four measures</h3>
      <MeasureBars c={c} data={data} />
      <p className="muted small">Ranks among the companies on this page. They are not shown to work here: open a “?” for what was tested.</p>

      {c.why.length > 0 && <div className="case for"><h3>Why look closer</h3><ul>{c.why.map((s) => <li key={s}>{s}</li>)}</ul></div>}
      {c.against.length > 0 && <div className="case against"><h3>What argues against</h3><ul>{c.against.map((s) => <li key={s}>{s}</li>)}</ul></div>}
      <div className="case unknown"><h3>What this cannot tell you</h3><ul>{c.caveats.map((s) => <li key={s}>{s}</li>)}</ul></div>

      <h3>Cheap or expensive?</h3>
      <h4>P/E against its own past fiscal year-ends</h4>
      {c.own_pes.length >= 2 && !c.inconsistent.includes('vs_own') ? <OwnPastStrip c={c} />
        : <p className="muted small">No usable comparison: fewer than two past year-ends with a normal profit, or the figures look inconsistent.</p>}
      <h4>Forward P/E against comparable companies</h4>
      <Strip now={c.inconsistent.includes('fwd_pe') ? null : c.fwd_pe} marks={peers}
        label={`Forward P/E ${num(c.fwd_pe)} against ${peers.length} comparable companies, middle ${num(c.sector_mid)}`}
        lo={`low ${num(peers[0])}`} mid={`now ${num(c.fwd_pe)} · middle ${num(c.sector_mid)}`} hi={`high ${num(peers[peers.length - 1])}`} />
      {c.inconsistent.length > 0 && <p className="banner warn small">Some valuation figures look inconsistent with each other and are left out of the comparisons.</p>}

      <h3>The usual numbers</h3>
      <dl className="numbers">
        {NUMBERS.map((n) => {
          const v = c[n.key] as number | null
          return (
            <div key={n.key}>
              <dt>{n.label}</dt>
              <dd className="num">{v == null ? DASH : n.fmt(v)}</dd>
              <dd className="guide">{n.guide}</dd>
            </div>
          )
        })}
      </dl>

      <h3>Headlines</h3>
      {c.headlines.length === 0 ? <p className="muted small">No headline from the last 14 days was fetched for this company.</p> : (
        <ul className="news">
          {c.headlines.map((h) => (
            <li key={h.title + h.date}>
              {h.url ? <a href={h.url} target="_blank" rel="noopener noreferrer">{h.title}</a> : h.title}
              <span className="muted small"> · {h.source || 'Yahoo'} · {h.date}</span>
            </li>
          ))}
        </ul>
      )}
      {c.headlines.length > 0 && <p className="muted small">Headlines are Yahoo&rsquo;s text, shown as received.</p>}
      <p className="muted small">
        On: {c.lists.map((k) => listName.get(k) ?? k).join(', ')}. Price day {c.last_bar}. Educational, not advice.
      </p>
    </aside>
  )
}
