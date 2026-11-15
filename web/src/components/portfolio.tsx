// Pieces of the Portfolio view: key strip, holdings table, holding details (inline row or bottom sheet), history chart,
// group bars, view options and the command field. Numbers come from holdings.json and the engine's covariance matrix
// (lib/basket.ts); nothing is invented here.
import { useEffect, useRef, useState, type FormEvent, type PointerEvent } from 'react'
import type { Data, History, Position } from '../data/load'
import { evaluate } from '../lib/basket'
import { DASH, direction, pct } from '../lib/format'
import { eur, groupLabel, techTickers } from '../lib/groups'
import { sortBy } from '../lib/sort'
import { withCompany, type Route } from '../router'
import { InfoTip, Pct } from './bits'
import { CompanyLink } from './research'

const money = (x: number | null | undefined, digits = 0) => (x == null ? DASH : `${eur(x, digits)} €`)

export function KeyStrip({ data }: { data: Data }) {
  const { totals, history } = data.holdings
  const before = evaluate(data.holdings, [], data.portfolio, techTickers(data))
  const s = history?.summary
  const approx = data.holdings.positions.some((p) => p.cost_approx)
  const items: { label: string; value: string; cls?: string; note?: string; tip?: string }[] = [
    { label: 'Value', value: money(totals.value_eur), note: totals.unpriced ? `${totals.unpriced} without a price` : undefined },
    {
      label: 'Result', value: totals.result_eur == null ? DASH : `${eur(totals.result_eur, 0, true)} €`, cls: direction(totals.result_eur),
      note: [!totals.result_complete && 'not every holding counted', approx && 'cost approximate'].filter(Boolean).join(' · ') || undefined,
      tip: 'Value now minus what the holdings cost, in EUR. Can differ slightly from the broker’s figure, which includes exchange-rate effects.',
    },
    ...(s ? [
      { label: 'Since first deposit', value: pct(s.since_start), cls: direction(s.since_start), tip: 'Time-weighted return from the broker’s weekly export: deposits do not distort it.' },
      { label: '1 month', value: pct(s.month), cls: direction(s.month), note: 'weekly points' },
      { label: 'Year to date', value: pct(s.ytd), cls: direction(s.ytd), note: 'weekly points' },
      { label: 'Largest fall', value: pct(s.max_drawdown), cls: 'down', note: `${s.drawdown_from} to ${s.drawdown_to}`, tip: 'The deepest fall from a high to a later low in the weekly series.' },
    ] : []),
    {
      label: 'Volatility (estimate)', value: before.vol == null ? DASH : pct(before.vol, 1, false),
      note: before.vol == null ? 'no risk data' : `covers ${pct(before.volCovered, 0, false)} of value`,
      tip: 'Annualised, from weekly EUR returns over two years, for the part of the portfolio with price history. An estimate, not a forecast.',
    },
    {
      label: 'Concentration', value: pct(before.top3, 0, false), note: `three largest · ${pct(before.tech, 0, false)} technology-heavy`,
      tip: 'Share of the portfolio in its three largest holdings. Technology-heavy: holdings you tagged “technology” in the holdings file.',
    },
  ]
  return (
    <dl className="kpis pf-kpis">
      {items.map((i) => (
        <div key={i.label}>
          <dt>{i.label}{i.tip && <InfoTip label={i.label}><p>{i.tip}</p></InfoTip>}</dt>
          <dd className={`num ${i.cls ?? ''}`}>{i.value}</dd>
          {i.note && <dd className="small muted">{i.note}</dd>}
        </div>
      ))}
    </dl>
  )
}

const KIND_TAG: Record<Position['kind'], string> = { stock: 'share', etf: 'ETF', etn: 'ETN', fund: 'fund' }

function HoldingDetails({ p, data, route }: { p: Position; data: Data; route: Route }) {
  const researchable = data.research.companies.some((c) => c.ticker === p.ticker)
  return (
    <>
      <dl>
        <div><dt>Price</dt><dd className="num">{p.price == null ? DASH : `${p.price} ${p.currency ?? ''}`}</dd></div>
        <div><dt>Units</dt><dd className="num">{p.quantity ?? DASH}</dd></div>
        <div><dt>Cost</dt><dd className="num">{money(p.cost_eur)}{p.cost_approx ? ' (approximate)' : ''}</dd></div>
        <div><dt>Result</dt><dd className={`num ${direction(p.result_eur)}`}>{p.result_eur == null ? DASH : `${eur(p.result_eur, 0, true)} €`}</dd></div>
        <div><dt>Return</dt><dd><Pct value={p.return_local} /></dd></div>
        <div><dt>Group</dt><dd>{groupLabel(p)}{p.sector ? ` · ${p.sector}` : ''}</dd></div>
        {p.note && <div><dt>Note</dt><dd>{p.note}</dd></div>}
        {!p.has_risk && p.value_eur != null && <div><dt>Risk data</dt><dd>none: left out of volatility</dd></div>}
      </dl>
      {p.ticker && researchable && <p className="small"><CompanyLink c={{ ticker: p.ticker, name: p.name }} route={route}>Open research panel</CompanyLink></p>}
    </>
  )
}

/** The phone's version of a row's details: a sheet from the bottom. Drag the handle down, tap outside or press Esc to close. */
function HoldingSheet({ p, data, route, onClose }: { p: Position; data: Data; route: Route; onClose: () => void }) {
  const grab = useRef<HTMLButtonElement>(null)
  const sheet = useRef<HTMLDivElement>(null)
  const start = useRef<number | null>(null)
  useEffect(() => {
    grab.current?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  const down = (e: PointerEvent) => { start.current = e.clientY }
  const move = (e: PointerEvent) => {
    if (start.current != null && sheet.current) sheet.current.style.transform = `translateY(${Math.max(0, e.clientY - start.current)}px)`
  }
  const up = (e: PointerEvent) => {
    if (start.current == null) return
    const d = e.clientY - start.current
    start.current = null
    if (d > 70) onClose()
    else if (sheet.current) sheet.current.style.transform = ''
  }
  return (
    <>
      <div className="scrim" onClick={onClose} aria-hidden="true" />
      <div ref={sheet} className="sheet" role="dialog" aria-modal="true" aria-label={`${p.name}: details`}>
        <button ref={grab} type="button" className="grab" aria-label="Close details" onClick={onClose} onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up} />
        <div className="rhead"><div><h2>{p.name}</h2><p className="muted small">{p.ticker ? `${p.ticker} · ` : ''}{KIND_TAG[p.kind]}</p></div><span className="num">{p.weight == null ? DASH : pct(p.weight, 1, false)}</span></div>
        <div className="detail sheetbody"><HoldingDetails p={p} data={data} route={route} /></div>
      </div>
    </>
  )
}

export function HoldingsTable({ data, route, more, phone }: { data: Data; route: Route; more: boolean; phone: boolean }) {
  const [open, setOpen] = useState<string | null>(null)
  const rows = sortBy(data.holdings.positions, (p) => p.weight, 'desc')
  const maxW = Math.max(0.0001, ...rows.map((p) => p.weight ?? 0))
  const span = 6 + (more ? 3 : 0)
  const sheet = phone ? rows.find((p) => p.key === open) : undefined
  return (
    <section aria-labelledby="holdings-h">
      <div className="sechead">
        <h2 id="holdings-h">Holdings <span className="muted small">{rows.length} positions</span></h2>
      </div>
      <div className="card scrollx">
        <table className="board dense pf-table">
          <caption className="sr-only">Holdings with value, result, return since purchase and weight. Select a name for details.</caption>
          <thead>
            <tr>
              <th scope="col" className="l">Name</th>
              <th scope="col" className="l wide">Group</th>
              {more && <><th scope="col" className="wide">Price</th><th scope="col" className="wide">Units</th><th scope="col" className="wide">Cost €</th></>}
              <th scope="col">Value €</th>
              <th scope="col" className="wide">Result €</th>
              <th scope="col" className="wide">Return<InfoTip label="Return"><p>Price against your purchase price, in the currency the holding trades in. Excludes exchange-rate effects.</p></InfoTip></th>
              <th scope="col">Weight</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => {
              const isOpen = open === p.key
              return [
                <tr key={p.key} className={isOpen ? 'selrow' : p.value_eur == null ? 'stale' : undefined}>
                  <th scope="row" className="l name">
                    <button type="button" className="rowbtn" aria-expanded={isOpen} aria-haspopup={phone ? 'dialog' : undefined} onClick={() => setOpen(isOpen ? null : p.key)}>
                      <b>{p.name}</b>
                      <span>{p.ticker ? `${p.ticker} · ` : ''}<span className="tag">{KIND_TAG[p.kind]}</span></span>
                    </button>
                  </th>
                  <td className="l wide small">{groupLabel(p)}</td>
                  {more && <>
                    <td className="wide num">{p.price == null ? DASH : `${p.price} ${p.currency ?? ''}`}</td>
                    <td className="wide num">{p.quantity ?? DASH}</td>
                    <td className="wide num">{eur(p.cost_eur, 0)}{p.cost_approx ? ' ≈' : ''}</td>
                  </>}
                  <td className="num">{p.value_eur == null ? <span className="muted">no price</span> : eur(p.value_eur, 2)}</td>
                  <td className={`wide num ${direction(p.result_eur)}`}>{eur(p.result_eur, 0, true)}</td>
                  <td className="wide"><Pct value={p.return_local} /></td>
                  <td className="num">
                    {p.weight == null ? DASH : <><span className="wbar" aria-hidden="true"><i style={{ width: `${(p.weight / maxW) * 100}%` }} /></span>{pct(p.weight, 1, false)}</>}
                  </td>
                </tr>,
                isOpen && !phone && (
                  <tr key={`${p.key}-d`} className="detail">
                    <td colSpan={span}><HoldingDetails p={p} data={data} route={route} /></td>
                  </tr>
                ),
              ]
            })}
          </tbody>
        </table>
      </div>
      <p className="under">
        Values are Yahoo closes converted to EUR; they can differ slightly from the broker’s report. A holding without a price tonight stays in
        the list but not in the totals.
      </p>
      {sheet && <HoldingSheet p={sheet} data={data} route={route} onClose={() => setOpen(null)} />}
    </section>
  )
}

const RANGES = [
  { key: '3m', label: '3M', weeks: 13 },
  { key: '6m', label: '6M', weeks: 26 },
  { key: '1y', label: '1Y', weeks: 52 },
  { key: 'max', label: 'Max', weeks: Infinity },
] as const

const W = 560
const H = 190
const PAD = { l: 10, r: 10, t: 18, b: 20 }

export function HistoryChart({ history }: { history: History }) {
  const [range, setRange] = useState<(typeof RANGES)[number]['key']>('max')
  const weeks = RANGES.find((r) => r.key === range)!.weeks
  const pts = history.points.slice(Number.isFinite(weeks) ? -(weeks + 1) : 0)
  const cum = pts.map((p) => p.cum)
  const lo = Math.min(0, ...cum)
  const hi = Math.max(0, ...cum)
  const span = hi - lo || 1
  const x = (i: number) => PAD.l + (pts.length > 1 ? (i / (pts.length - 1)) * (W - PAD.l - PAD.r) : 0)
  const y = (v: number) => PAD.t + ((hi - v) / span) * (H - PAD.t - PAD.b)
  const iLow = cum.indexOf(Math.min(...cum))
  const iHigh = cum.indexOf(Math.max(...cum))
  const last = pts[pts.length - 1]
  const summary =
    `Accumulated return, weekly points, ${pts[0].date} to ${last.date}. ` +
    `Lowest ${pct(cum[iLow])} on ${pts[iLow].date}, highest ${pct(cum[iHigh])} on ${pts[iHigh].date}, latest ${pct(last.cum)}.`
  const anchor = (i: number) => (x(i) > W * 0.6 ? 'end' : 'start')
  return (
    <section aria-labelledby="history-h">
      <div className="sechead">
        <h2 id="history-h">Return since first deposit</h2>
        <div className="seg" role="group" aria-label="Range">
          {RANGES.map((r) => <button key={r.key} type="button" aria-pressed={range === r.key} onClick={() => setRange(r.key)}>{r.label}</button>)}
        </div>
      </div>
      <div className="card chartbox">
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={summary} className="linechart">
          <line x1={PAD.l} x2={W - PAD.r} y1={y(0)} y2={y(0)} className="zero" />
          <polyline fill="none" className="line" points={pts.map((p, i) => `${x(i).toFixed(1)},${y(p.cum).toFixed(1)}`).join(' ')} />
          <circle cx={x(iLow)} cy={y(cum[iLow])} r="4" className="lowdot" />
          <text x={x(iLow) + (anchor(iLow) === 'end' ? -8 : 8)} y={y(cum[iLow]) + 14} textAnchor={anchor(iLow)} className="chartlabel">▼ {pct(cum[iLow])} · {pts[iLow].date}</text>
          <circle cx={x(iHigh)} cy={y(cum[iHigh])} r="4" className="highdot" />
          <text x={x(iHigh) + (anchor(iHigh) === 'end' ? -8 : 8)} y={y(cum[iHigh]) - 7} textAnchor={anchor(iHigh)} className="chartlabel">▲ {pct(cum[iHigh])} · {pts[iHigh].date}</text>
          <circle cx={x(pts.length - 1)} cy={y(last.cum)} r="4" className="nowdot" />
        </svg>
        <p className="small muted pf-cap">
          Latest <b className={`num ${direction(last.cum)}`}>{pct(last.cum)}</b> on {last.date}. Time-weighted, weekly points; the dashed line is zero.
        </p>
      </div>
      <details className="how">
        <summary>Weekly points as a table</summary>
        <div className="scrollx tallscroll">
          <table className="board plain dense">
            <thead><tr><th scope="col" className="l">Week</th><th scope="col">Value €</th><th scope="col">Return</th></tr></thead>
            <tbody>
              {[...pts].reverse().map((p) => (
                <tr key={p.date}><th scope="row" className="l num">{p.date}</th><td className="num">{eur(p.value, 2)}</td><td><Pct value={p.cum} /></td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  )
}

export function GroupBars({ data }: { data: Data }) {
  const totals = new Map<string, number>()
  for (const p of data.holdings.positions) if (p.weight != null) totals.set(groupLabel(p), (totals.get(groupLabel(p)) ?? 0) + p.weight)
  const rows = [...totals].sort((a, b) => b[1] - a[1])
  return (
    <section aria-labelledby="groups-h">
      <h2 id="groups-h" className="sechead">Where the money sits</h2>
      <div className="card panel pf-groups">
        <ul className="bars">
          {rows.map(([label, w]) => (
            <li key={label}>
              <span className="blabel">{label}</span>
              <span className="btrack" aria-hidden="true"><span className="bfill" style={{ width: `${Math.min(100, w * 100)}%` }} /></span>
              <span className="num bvalue">{pct(w, 1, false)}</span>
            </li>
          ))}
        </ul>
        <p className="small muted">Groups are your own tags from the holdings file; untagged holdings are grouped by type.</p>
      </div>
    </section>
  )
}

export interface ViewOptionsState { chart: boolean; groups: boolean; columns: boolean }
export const DEFAULT_VIEW: ViewOptionsState = { chart: true, groups: true, columns: false }

/** "View" button: choose what the page shows. Dense columns and secondary panels are opt-in. */
export function ViewOptions({ value, onChange }: { value: ViewOptionsState; onChange: (v: ViewOptionsState) => void }) {
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    const onDown = (e: Event) => box.current && !box.current.contains(e.target as Node) && setOpen(false)
    window.addEventListener('keydown', onKey)
    window.addEventListener('pointerdown', onDown)
    return () => { window.removeEventListener('keydown', onKey); window.removeEventListener('pointerdown', onDown) }
  }, [open])
  const row = (k: keyof ViewOptionsState, label: string) => (
    <label key={k}><input type="checkbox" checked={value[k]} onChange={(e) => onChange({ ...value, [k]: e.target.checked })} /> {label}</label>
  )
  return (
    <div className="viewopts" ref={box}>
      <button type="button" className="btn small" aria-expanded={open} aria-controls="viewopts-pop" onClick={() => setOpen(!open)}>View ▾</button>
      {open && (
        <div id="viewopts-pop" className="opts" role="group" aria-label="View options">
          {row('chart', 'History chart')}
          {row('groups', 'Where the money sits')}
          {row('columns', 'Extra columns (price, units, cost)')}
        </div>
      )}
    </div>
  )
}

const VIEWS: Record<string, Parameters<typeof withCompany>[0]['view']> = {
  portfolio: 'portfolio', candidates: 'candidates', screener: 'screener', watchlists: 'list', mix: 'mix', movers: 'movers', data: 'data',
}

/** A command field in the spirit of a terminal: type a ticker to open its panel, or a view name to go there. */
export function CommandField({ data, route }: { data: Data; route: Route }) {
  const [msg, setMsg] = useState('')
  const go = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const input = e.currentTarget.elements.namedItem('cmd') as HTMLInputElement
    const q = input.value.trim().toLowerCase()
    if (!q) return
    const view = VIEWS[q]
    const company = data.research.companies.find((c) => c.ticker.toLowerCase() === q)
    if (view) window.location.hash = view === 'portfolio' ? '#/' : `#/${view === 'list' ? 'list' : view}`
    else if (company) window.location.hash = withCompany(route, company.ticker)
    else { setMsg(`Nothing matches “${input.value.trim()}”. Try a ticker or a view name.`); return }
    setMsg('')
    input.value = ''
  }
  return (
    <form className="cmd" onSubmit={go} role="search">
      <label className="sr-only" htmlFor="cmd">Go to a ticker or view</label>
      <span aria-hidden="true">›</span>
      <input id="cmd" name="cmd" autoComplete="off" placeholder="Ticker or view: NVDA, mix, screener" />
      <button type="submit" className="btn">Go</button>
      {msg && <span className="small muted" role="status">{msg}</span>}
    </form>
  )
}
