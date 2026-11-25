import { useEffect, useState } from 'react'
import { State, useMediaQuery } from './components/bits'
import { ResearchPanel } from './components/research'
import { loadAll, type Data } from './data/load'
import { weekdaysBetween } from './lib/format'
import { formatHash, useRoute, type View } from './router'
import Candidates from './views/Candidates'
import DataState from './views/DataState'
import Leaderboard from './views/Leaderboard'
import MixView from './views/Mix'
import MoversView from './views/Movers'
import Overview from './views/Overview'
import Screener from './views/Screener'

type Load = { status: 'loading' } | { status: 'error'; message: string } | { status: 'ready'; data: Data }

const NAV: { view: View; label: string }[] = [
  { view: 'candidates', label: 'Candidates' },
  { view: 'screener', label: 'Screener' },
  { view: 'list', label: 'Watchlists' },
  { view: 'mix', label: 'Mix' },
  { view: 'movers', label: 'Movers' },
]

export default function App() {
  const [load, setLoad] = useState<Load>({ status: 'loading' })
  const route = useRoute()
  const phone = useMediaQuery('(max-width: 900px)')
  useEffect(() => {
    loadAll().then(
      (data) => setLoad({ status: 'ready', data }),
      (e: unknown) => setLoad({ status: 'error', message: e instanceof Error ? e.message : String(e) }),
    )
  }, [])

  const data = load.status === 'ready' ? load.data : null
  const [today] = useState(() => new Date().toISOString().slice(0, 10))
  const old = data && !data.meta.demo && weekdaysBetween(data.meta.asof, today) > 2
  const company = data && route.params.c ? data.research.companies.find((c) => c.ticker === route.params.c) : undefined
  const panel = data && company ? <ResearchPanel c={company} data={data} route={route} /> : null
  const view = data && (
    <>
      {route.view === 'candidates' && <Candidates data={data} route={route} />}
      {route.view === 'screener' && <Screener data={data} route={route} />}
      {route.view === 'list' && (route.id ? <Leaderboard data={data} route={route} /> : <Overview data={data} route={route} />)}
      {route.view === 'mix' && <MixView data={data} />}
      {route.view === 'movers' && <MoversView data={data} route={route} />}
      {route.view === 'data' && <DataState data={data} />}
      {route.view === 'notfound' && (
        <State title="Page not found">
          <p><a href="#/">Go to Candidates</a></p>
        </State>
      )}
    </>
  )

  return (
    <>
      <header className="topbar">
        <a className="brand" href="#/">Market leaderboard</a>
        <nav className="nav" aria-label="Views">
          {NAV.map((n) => (
            <a key={n.view} href={formatHash({ view: n.view })} aria-current={route.view === n.view ? 'page' : undefined}>
              {n.label}
            </a>
          ))}
        </nav>
        {data && (
          <a className="status" href={formatHash({ view: 'data' })} aria-current={route.view === 'data' ? 'page' : undefined}>
            Data as of <b>{data.meta.asof}</b>
            {data.meta.failures.length > 0 && <> · {data.meta.failures.length} without data</>}
          </a>
        )}
      </header>
      <main className={panel && !phone ? 'split' : undefined}>
        <div className="content">
          {data?.meta.demo && <p className="banner demo">Demo data: invented companies and prices, for trying the page.</p>}
          {old && (
            <p className="banner warn" role="status">
              The data is from {data.meta.asof}. The nightly build has not produced newer data; the numbers below are from that day.
            </p>
          )}
          {load.status === 'loading' && <State title="Loading data…" role="status" />}
          {load.status === 'error' && (
            <State title="The data could not be shown" role="alert">
              <p>{load.message}</p>
            </State>
          )}
          {/* On a narrow screen the panel is the page; on a wide one it sits beside the view. */}
          {panel && phone ? panel : view}
        </div>
        {panel && !phone && panel}
      </main>
    </>
  )
}
