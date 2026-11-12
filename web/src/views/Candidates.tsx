import { Pct, State } from '../components/bits'
import { CompanyLink, num, OwnPastStrip, ValuationPill } from '../components/research'
import type { Company, Data } from '../data/load'
import { replaceRoute, type Route } from '../router'

const uniq = (xs: (string | null)[]) => [...new Set(xs.filter((x): x is string => !!x))].sort()

/** List, sector and country pickers shared by Candidates and Screener; the choice lives in the address. */
export function Filters({ data, route }: { data: Data; route: Route }) {
  const cs = data.research.companies
  const set = (key: string, value: string) => replaceRoute({ view: route.view, id: route.id, params: { ...route.params, [key]: value || undefined } })
  const pick = (key: string, label: string, options: [string, string][]) => (
    <label className="pick">
      <span>{label}</span>
      <select value={route.params[key] ?? ''} onChange={(e) => set(key, e.target.value)}>
        <option value="">All</option>
        {options.map(([v, text]) => <option key={v} value={v}>{text}</option>)}
      </select>
    </label>
  )
  return (
    <div className="filters">
      {pick('list', 'Watchlist', data.leaderboard.lists.map((l) => [l.key, l.name]))}
      {pick('sector', 'Sector', uniq(cs.map((c) => c.sector)).map((s) => [s, s]))}
      {pick('country', 'Country', uniq(cs.map((c) => c.country)).map((s) => [s, s]))}
    </div>
  )
}

export function applyFilters(cs: Company[], route: Route): Company[] {
  const { list, sector, country } = route.params
  return cs.filter((c) => (!list || c.lists.includes(list)) && (!sector || c.sector === sector) && (!country || c.country === country))
}

export default function Candidates({ data, route }: { data: Data; route: Route }) {
  const r = data.research
  const by = new Map(r.companies.map((c) => [c.ticker, c]))
  const all = r.shortlist.map((t) => by.get(t)!).filter(Boolean)
  const shown = applyFilters(all, route)
  return (
    <>
      <div className="pagehead">
        <div>
          <h1>Candidates</h1>
          <p className="muted small">
            Tonight&rsquo;s {all.length} companies worth a closer look, out of {r.gate_passed} that pass the profit rule. A starting
            point for your own research, with what speaks against each one. Not advice.
          </p>
        </div>
        <Filters data={data} route={route} />
      </div>

      <details className="card how">
        <summary>How these are picked, and what has been tested</summary>
        <p>
          A company must show a profit in its latest fiscal year and in at least 3 of its last 4. Every company is then ranked on
          four measures, and the highest average ranks are listed here. The measures come from published research on large
          samples of shares; on these companies they are tested or untested as follows.
        </p>
        <dl className="evidence">
          {(['value', 'quality', 'trend', 'steady'] as const).map((k) => (
            <div key={k}>
              <dt>{r.labels[k]} <span className="pill mid">{r.evidence[k]?.status ?? 'untested'}</span></dt>
              <dd>{r.evidence[k]?.text ?? 'Not tested on these companies.'}</dd>
            </div>
          ))}
        </dl>
      </details>

      {shown.length === 0 ? (
        <State title={all.length ? 'No candidate matches these filters' : 'No candidates tonight'}>
          <p>{all.length ? 'Clear a filter to see the others.' : 'No company passed the profit rule with enough data to rank.'}</p>
        </State>
      ) : (
        <div className="cards">
          {shown.map((c) => (
            <article key={c.ticker} className="card cand">
              <header>
                <div>
                  <h2><CompanyLink c={c} route={route} /></h2>
                  <p className="muted small">{c.ticker} · {c.sector ?? 'Sector unknown'} · place {c.place}</p>
                </div>
                <ValuationPill c={c} />
              </header>
              {c.own_pes.length >= 2 && !c.inconsistent.includes('vs_own') ? <OwnPastStrip c={c} />
                : <p className="muted small">No own-past P/E comparison: fewer than two past year-ends with a normal profit, or the figures look inconsistent.</p>}
              <div className="twocol">
                <div className="case for"><h3>Why look closer</h3><ul>{c.why.map((s) => <li key={s}>{s}</li>)}</ul></div>
                <div className="case against">
                  <h3>What argues against</h3>
                  {c.against.length ? <ul>{c.against.map((s) => <li key={s}>{s}</li>)}</ul> : <p className="muted small">No measure is in the lower half. See the caveats in the panel.</p>}
                </div>
              </div>
              <p className="small keyline">
                1y <Pct value={c.ret_1y} /> · from high <Pct value={c.dd52} /> · P/E <span className="num">{num(c.pe)}</span> · forward{' '}
                <span className="num">{num(c.fwd_pe)}</span>
              </p>
              {c.events.length > 0 && <p className="events">{c.events.map((e) => <span key={e} className="pill mid">{e}</span>)}</p>}
            </article>
          ))}
        </div>
      )}
      <p className="under">
        Ranks compare the {r.companies.length} companies on this page with each other only. Fundamentals are current values from
        Yahoo. Educational, not advice.
      </p>
    </>
  )
}
