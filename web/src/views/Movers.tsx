import { useId } from 'react'
import { Pct, State } from '../components/bits'
import { CompanyLink } from '../components/research'
import type { Data, Movers } from '../data/load'
import { formatHash, type Route } from '../router'

type Mover = Movers['gainers'][number]

function Table({ title, rows, data, empty, route }: { title: string; rows: Mover[]; data: Data; empty: string; route: Route }) {
  const listName = new Map(data.leaderboard.lists.map((l) => [l.key, l.name]))
  const id = useId()
  return (
    <section className="card panel" aria-labelledby={id}>
      <h2 id={id}>{title}</h2>
      {rows.length === 0 ? <p className="muted">{empty}</p> : (
        <table className="board plain">
          <thead>
            <tr><th scope="col" className="l">Company</th><th scope="col" className="l wide">Watchlist</th><th scope="col">1d</th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.ticker}>
                <th scope="row" className="l name">
                  <b><CompanyLink c={r} route={route} /></b>
                  <span>{r.ticker}{r.last_bar !== data.movers.asof ? ` · price day ${r.last_bar}` : ''}</span>
                </th>
                <td className="l wide">
                  {r.lists.map((k, i) => (
                    <span key={k}>{i > 0 && ', '}<a href={formatHash({ view: 'list', id: k })}>{listName.get(k) ?? k}</a></span>
                  ))}
                </td>
                <td><Pct value={r.ret_1d} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

export default function MoversView({ data, route }: { data: Data; route: Route }) {
  const { gainers, losers, alerts } = data.movers
  const moved = new Set([...gainers, ...losers, ...alerts].map((m) => m.ticker))
  const news = data.research.companies.filter((c) => moved.has(c.ticker) && c.headlines.length > 0)
  const nothing = gainers.length + losers.length + alerts.length === 0
  return (
    <>
      <div className="pagehead">
        <div>
          <h1>Movers</h1>
          <p className="muted small">
            Largest one-day moves across all watchlists, each in the stock's own currency. Each company is listed once.
          </p>
        </div>
      </div>
      {nothing ? (
        <State title="Nothing moved">
          <p>No company with a recent price changed on its last trading day.</p>
        </State>
      ) : (
        <>
          <div className="grid two">
            <Table title="Largest gains" rows={gainers} data={data} route={route} empty="No company rose on its last trading day." />
            <Table title="Largest falls" rows={losers} data={data} route={route} empty="No company fell on its last trading day." />
          </div>
          <section className="card panel" aria-labelledby="mv-alerts">
            <h2 id="mv-alerts">Dip flags</h2>
            <p className="muted small">
              Companies whose recent fall crosses a fixed threshold. An untested screen rule: it describes the price move and
              says nothing about what happens next.
            </p>
            {alerts.length === 0 ? <p className="muted">No company is flagged tonight.</p> : (
              <ul className="alerts">
                {alerts.map((a) => (
                  <li key={a.ticker}>
                    <b><CompanyLink c={a} route={route} /></b> <span className="muted">{a.ticker}</span> <Pct value={a.ret_1d} />
                    <div className="small">
                      Flagged because: {a.reasons.join('; ')}.
                      {a.q_scored > 0 && <> Passes {a.q_passed} of {a.q_scored} fundamentals checks.</>}
                      <span className="muted"> ({a.label})</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
          {news.length > 0 && (
            <section className="card panel" aria-labelledby="mv-news">
              <h2 id="mv-news">Recent headlines for these companies</h2>
              <p className="muted small">Yahoo&rsquo;s text, shown as received. A headline may be about the wider market.</p>
              <ul className="news">
                {news.flatMap((c) => c.headlines.slice(0, 2).map((h) => (
                  <li key={c.ticker + h.title}>
                    <b><CompanyLink c={c} route={route} /></b>: {h.url ? <a href={h.url} target="_blank" rel="noopener noreferrer">{h.title}</a> : h.title}
                    <span className="muted small"> · {h.source || 'Yahoo'} · {h.date}</span>
                  </li>
                )))}
              </ul>
            </section>
          )}
        </>
      )}
    </>
  )
}
