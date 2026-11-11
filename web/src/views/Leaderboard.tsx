import { Fragment, useState } from 'react'
import { asPeriod, Flag, InfoTip, Pct, PeriodPicker, PERIODS, RankChange, Sparkline, State, useMediaQuery } from '../components/bits'
import type { Data, Period, Row } from '../data/load'
import { DASH, pct } from '../lib/format'
import { sortBy, type Dir } from '../lib/sort'
import { formatHash, replaceRoute, type Route } from '../router'

type SortKey = 'rank' | 'name' | `ret_${Period}` | 'dd52' | 'vol_1y' | 'quality' | 'flag'

const quality = (r: Row) => (r.q_scored ? r.q_passed / r.q_scored : null)

function sortValue(r: Row, key: SortKey, period: Period): number | string | null {
  switch (key) {
    case 'rank': return r.rank?.[period].rank ?? null
    case 'name': return r.name
    case 'quality': return quality(r)
    case 'flag': return r.dip ? 1 : 0
    default: return r[key]
  }
}

const SORT_KEYS: SortKey[] = ['rank', 'name', ...PERIODS.map((p) => `ret_${p.key}` as const), 'dd52', 'vol_1y', 'quality', 'flag']

export default function Leaderboard({ data, route }: { data: Data; route: Route }) {
  const phone = useMediaQuery('(max-width: 640px)')
  const [open, setOpen] = useState<string | null>(null)
  const list = data.leaderboard.lists.find((l) => l.key === route.id)
  if (!list) {
    return (
      <State title="No such watchlist">
        <p><a href="#/">Go to the overview</a></p>
      </State>
    )
  }
  const period = asPeriod(route.params.period)
  const [rawKey, rawDir] = (route.params.sort ?? '').split(':')
  const sortKey: SortKey = SORT_KEYS.includes(rawKey as SortKey) ? (rawKey as SortKey) : 'rank'
  const dir: Dir = rawDir === 'asc' || rawDir === 'desc' ? rawDir : sortKey === 'rank' || sortKey === 'name' ? 'asc' : 'desc'
  const rows = sortBy(list.rows, (r) => sortValue(r, sortKey, period), dir)
  const failures = data.meta.failures.filter((f) => f.lists.includes(list.key))

  const go = (params: { period?: Period; sort?: string }) =>
    replaceRoute({ view: 'list', id: list.key, params: { period: params.period ?? period, sort: 'sort' in params ? params.sort : route.params.sort } })
  const sortOn = (key: SortKey) => {
    const firstDir: Dir = key === 'rank' || key === 'name' ? 'asc' : 'desc'
    const next: Dir = key === sortKey ? (dir === 'asc' ? 'desc' : 'asc') : firstDir
    go({ sort: key === 'rank' && next === 'asc' ? undefined : `${key}:${next}` })
  }
  const th = (key: SortKey, label: string, cls = '', tip?: React.ReactNode) => (
    <th scope="col" className={cls} aria-sort={sortKey === key ? (dir === 'asc' ? 'ascending' : 'descending') : undefined}>
      <button type="button" onClick={() => sortOn(key)}>{label}</button>
      {tip}
    </th>
  )
  const selLabel = PERIODS.find((p) => p.key === period)!.label
  const columns = phone ? 5 : 14

  return (
    <>
      <nav className="tabs" aria-label="Watchlists">
        {data.leaderboard.lists.map((l) => (
          <a key={l.key} href={formatHash({ view: 'list', id: l.key, params: { period: route.params.period } })}
            aria-current={l.key === list.key ? 'page' : undefined}>
            {l.name}
          </a>
        ))}
      </nav>
      <div className="pagehead">
        <div>
          <h1>{list.name}</h1>
          <p className="muted small">
            Ranked by {selLabel} return, in each stock's own currency. {list.summary.count} names
            {list.summary.stale > 0 && <>, {list.summary.stale} without a recent price</>}.
          </p>
        </div>
        <PeriodPicker value={period} onChange={(p) => go({ period: p })} />
      </div>

      <div className="card">
        <table className="board">
          <caption className="sr-only">{list.name}: returns, drawdown, volatility and screen flags per company</caption>
          <thead>
            <tr>
              {th('rank', '#', 'rank')}
              <th scope="col" className="chg"><span className="sr-only">Rank change since the previous close</span></th>
              {th('name', 'Company', 'l')}
              <th scope="col" className="l">60 days</th>
              {PERIODS.map((p) => (
                <Fragment key={p.key}>{th(`ret_${p.key}`, p.label, p.key === period ? 'sel' : 'wide')}</Fragment>
              ))}
              {th('dd52', 'From high', 'wide',
                <InfoTip label="From high"><p>How far the last close is below the highest close of the past 52 weeks.</p></InfoTip>)}
              {th('vol_1y', 'Vol 1y', 'wide',
                <InfoTip label="Vol 1y"><p>Volatility: how much the daily returns varied over the past year, scaled to a year. In the stock's own currency.</p></InfoTip>)}
              {th('quality', 'Checks', 'wide',
                <InfoTip label="Checks">
                  <p>How many of the simple fundamentals checks the company passes, out of those that had data (profitability, debt, cash flow, growth, size).</p>
                  <p className="muted">Untested screen rule, from current fundamentals, not point-in-time.</p>
                </InfoTip>)}
              {th('flag', 'Flag', 'wide')}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const rank = r.rank?.[period]
              const isOpen = phone && open === r.ticker
              const name = (
                <>
                  <b>{r.name}</b>
                  <span>{r.ticker}{r.stale && r.stale_reason ? ` · ${r.stale_reason}` : ''}</span>
                </>
              )
              return (
                <Fragment key={r.ticker}>
                  <tr className={r.stale ? 'stale' : undefined}>
                    <td className="rank">{rank?.rank ?? DASH}</td>
                    <td className="chg"><RankChange delta={rank?.rank_delta} /></td>
                    <th scope="row" className="l name">
                      {phone ? (
                        <button type="button" className="rowbtn" aria-expanded={isOpen} onClick={() => setOpen(isOpen ? null : r.ticker)}>{name}</button>
                      ) : name}
                    </th>
                    <td className="l"><Sparkline values={r.spark} width={phone ? 64 : 96} /></td>
                    {PERIODS.map((p) => (
                      <td key={p.key} className={p.key === period ? 'sel' : 'wide'}><Pct value={r[`ret_${p.key}`]} /></td>
                    ))}
                    <td className="wide"><Pct value={r.dd52} /></td>
                    <td className="wide num">{pct(r.vol_1y, 0, false)}</td>
                    <td className="wide num">{r.q_scored ? `${r.q_passed}/${r.q_scored}` : DASH}</td>
                    <td className="wide">{r.dip && <Flag reasons={r.dip_reasons} />}</td>
                  </tr>
                  {isOpen && (
                    <tr className="detail">
                      <td colSpan={columns}>
                        <dl>
                          {PERIODS.filter((p) => p.key !== period).map((p) => (
                            <div key={p.key}><dt>{p.label} return</dt><dd><Pct value={r[`ret_${p.key}`]} /></dd></div>
                          ))}
                          <div><dt>From 52-week high</dt><dd><Pct value={r.dd52} /></dd></div>
                          <div><dt>Volatility 1y</dt><dd className="num">{pct(r.vol_1y, 0, false)}</dd></div>
                          <div><dt>Checks passed</dt><dd className="num">{r.q_scored ? `${r.q_passed} of ${r.q_scored}` : DASH}</dd></div>
                          <div><dt>Last price day</dt><dd className="num">{r.last_bar}</dd></div>
                          {r.dip && <div><dt>Flag (untested screen rule)</dt><dd><Flag reasons={r.dip_reasons} /></dd></div>}
                        </dl>
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>

      {failures.length > 0 && (
        <div className="under">
          No data tonight:
          <ul>{failures.map((f) => <li key={f.ticker}>{f.name} ({f.ticker}): {f.reason}</li>)}</ul>
        </div>
      )}
      <p className="under">
        Returns use each stock's own last trading days, so a market holiday shifts its dates. Flags and checks are untested
        screen rules. Educational, not advice.
      </p>
    </>
  )
}
