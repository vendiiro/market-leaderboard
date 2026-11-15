import { CommandField, GroupBars, HistoryChart, HoldingsTable, KeyStrip } from '../components/portfolio'
import { State } from '../components/bits'
import type { Data } from '../data/load'
import type { Route } from '../router'

export default function Portfolio({ data, route }: { data: Data; route: Route }) {
  const h = data.holdings
  if (h.positions.length === 0) {
    return (
      <State title="No portfolio file found">
        <p>
          Copy <code>config/portfolio.example.toml</code> to <code>config/portfolio.toml</code>, put your holdings in it and run the
          data build again. The file is private and ignored by git.
        </p>
      </State>
    )
  }
  return (
    <>
      <div className="pagehead">
        <div>
          <h1>Portfolio</h1>
          <p className="muted small">{h.label} · prices as of {h.asof} · EUR</p>
        </div>
        <CommandField data={data} route={route} />
      </div>
      <KeyStrip data={data} />
      <div className="pf-grid">
        <HoldingsTable data={data} route={route} />
        <div className="pf-side">
          {h.history ? (
            <HistoryChart history={h.history} />
          ) : (
            <section aria-labelledby="nohistory-h">
              <h2 id="nohistory-h" className="sechead">Return since first deposit</h2>
              <div className="card panel"><p className="muted small">{h.history_note ?? 'No history file.'}</p></div>
            </section>
          )}
          <GroupBars data={data} />
        </div>
      </div>
    </>
  )
}
