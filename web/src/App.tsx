import { useEffect, useState } from 'react'
import { State } from './components/bits'
import { loadAll, type Data } from './data/load'
import { weekdaysBetween } from './lib/format'
import { formatHash, useRoute, type View } from './router'
import Leaderboard from './views/Leaderboard'
import Overview from './views/Overview'

type Load = { status: 'loading' } | { status: 'error'; message: string } | { status: 'ready'; data: Data }

const NAV: { view: View; label: string; id?: string }[] = [
  { view: 'overview', label: 'Overview' },
  { view: 'list', label: 'Leaderboards' },
  { view: 'mix', label: 'Mix' },
  { view: 'movers', label: 'Movers' },
]

export default function App() {
  const [load, setLoad] = useState<Load>({ status: 'loading' })
  const route = useRoute()
  useEffect(() => {
    loadAll().then(
      (data) => setLoad({ status: 'ready', data }),
      (e: unknown) => setLoad({ status: 'error', message: e instanceof Error ? e.message : String(e) }),
    )
  }, [])

  const data = load.status === 'ready' ? load.data : null
  const firstList = data?.leaderboard.lists[0]?.key
  const [today] = useState(() => new Date().toISOString().slice(0, 10))
  const old = data && !data.meta.demo && weekdaysBetween(data.meta.asof, today) > 2

  return (
    <>
      <header className="topbar">
        <a className="brand" href="#/">Market leaderboard</a>
        <nav className="nav" aria-label="Views">
          {NAV.map((n) => (
            <a key={n.view} href={formatHash({ view: n.view, id: n.view === 'list' ? firstList : undefined })}
              aria-current={route.view === n.view ? 'page' : undefined}>
              {n.label}
            </a>
          ))}
        </nav>
        {data && (
          <p className="status" style={{ margin: 0 }}>
            Data as of <b>{data.meta.asof}</b>
            {data.meta.failures.length > 0 && <> · {data.meta.failures.length} without data</>}
          </p>
        )}
      </header>
      <main>
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
        {data && route.view === 'overview' && <Overview data={data} route={route} />}
        {data && route.view === 'list' && <Leaderboard data={data} route={route} />}
        {data && (route.view === 'mix' || route.view === 'movers') && (
          <State title="This view is not built yet">
            <p>It is part of the next build session.</p>
          </State>
        )}
        {data && route.view === 'notfound' && (
          <State title="Page not found">
            <p><a href="#/">Go to the overview</a></p>
          </State>
        )}
      </main>
    </>
  )
}
