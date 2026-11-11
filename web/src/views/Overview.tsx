import { asPeriod, Pct, PeriodPicker, PERIODS } from '../components/bits'
import type { Data } from '../data/load'
import { formatHash, replaceRoute, type Route } from '../router'

export default function Overview({ data, route }: { data: Data; route: Route }) {
  const period = asPeriod(route.params.period)
  const label = PERIODS.find((p) => p.key === period)!.label
  const { meta } = data
  const nameOf = new Map(data.leaderboard.lists.flatMap((l) => l.rows.map((r) => [r.ticker, r] as const)))

  return (
    <>
      <div className="pagehead">
        <div>
          <h1>Overview</h1>
          <p className="muted small">Average return of each watchlist: every company counts the same, each in its own currency.</p>
        </div>
        <PeriodPicker value={period} onChange={(p) => replaceRoute({ view: 'overview', params: { period: p } })} />
      </div>

      <div className="grid">
        {data.leaderboard.lists.map((l) => {
          const s = l.summary.periods[period]
          const top = s.top ? nameOf.get(s.top) : undefined
          const bottom = s.bottom ? nameOf.get(s.bottom) : undefined
          return (
            <section key={l.key} className="card tile" aria-labelledby={`t-${l.key}`}>
              <h2 id={`t-${l.key}`}>
                <a href={formatHash({ view: 'list', id: l.key, params: { period: route.params.period } })}>{l.name}</a>
              </h2>
              <div>
                <div className="hero"><Pct value={s.mean} /></div>
                <div className="muted small">average {label} return of {s.n} {s.n === 1 ? 'company' : 'companies'}</div>
              </div>
              <dl className="mini">
                {PERIODS.map((p) => (
                  <div key={p.key} className={p.key === period ? 'sel' : undefined}>
                    <dt>{p.label}</dt>
                    <dd><Pct value={l.summary.periods[p.key].mean} /></dd>
                  </div>
                ))}
              </dl>
              <dl className="pairs">
                {top && (<><dt>Highest</dt><dd>{top.name}</dd><dd><Pct value={top[`ret_${period}`]} /></dd></>)}
                {bottom && bottom !== top && (<><dt>Lowest</dt><dd>{bottom.name}</dd><dd><Pct value={bottom[`ret_${period}`]} /></dd></>)}
              </dl>
              <p className="muted small" style={{ margin: 0 }}>
                {l.summary.flags} {l.summary.flags === 1 ? 'dip flag' : 'dip flags'} (untested screen rule)
                {l.summary.stale > 0 && <> · {l.summary.stale} without a recent price</>}
              </p>
            </section>
          )
        })}
      </div>

      <section className="card panel" aria-labelledby="data-state">
        <h2 id="data-state">Tonight's data</h2>
        <p>
          Data as of {meta.asof}: {meta.usable} of {meta.tickers} companies have prices.
        </p>
        {meta.failures.length > 0 && (
          <>
            <h3>No data tonight</h3>
            <ul>{meta.failures.map((f) => <li key={f.ticker}>{f.name} ({f.ticker}): {f.reason}</li>)}</ul>
          </>
        )}
        <h3 style={{ marginTop: 12 }}>What to keep in mind</h3>
        <ul className="muted">{meta.notes.map((n) => <li key={n}>{n}</li>)}</ul>
      </section>
    </>
  )
}
