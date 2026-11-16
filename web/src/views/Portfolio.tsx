import { useEffect, useState } from 'react'
import { BasketPanel, CandidateTable, GapCards, newItem } from '../components/additions'
import { State, useMediaQuery } from '../components/bits'
import { CommandField, DEFAULT_VIEW, GroupBars, HistoryChart, HoldingsTable, KeyStrip, ViewOptions, type ViewOptionsState } from '../components/portfolio'
import type { Data } from '../data/load'
import { loadBasket, saveBasket } from '../lib/basket-storage'
import type { BasketItem } from '../lib/basket'
import { ETF_CARD, sectorCards } from '../lib/groups'
import type { Route } from '../router'

const VIEW_KEY = 'market-leaderboard.portfolio-view.v1'
const loadView = (): ViewOptionsState => {
  try {
    return { ...DEFAULT_VIEW, ...(JSON.parse(globalThis.localStorage?.getItem(VIEW_KEY) ?? 'null') as Partial<ViewOptionsState> | null) }
  } catch {
    return DEFAULT_VIEW // blocked or corrupt storage: the defaults still work
  }
}

type Tab = 'holdings' | 'additions' | 'basket'

export default function Portfolio({ data, route }: { data: Data; route: Route }) {
  const h = data.holdings
  const phone = useMediaQuery('(max-width: 900px)')
  const [view, setView] = useState(loadView)
  const [basket, setBasket] = useState<BasketItem[]>(loadBasket)
  const [tab, setTab] = useState<Tab>('holdings')
  const [card, setCard] = useState(() => sectorCards(data)[0]?.sector ?? ETF_CARD)
  useEffect(() => saveBasket(basket), [basket])
  useEffect(() => {
    try { globalThis.localStorage?.setItem(VIEW_KEY, JSON.stringify(view)) } catch { /* blocked storage: the choice lasts for this visit */ }
  }, [view])

  if (h.positions.length === 0) {
    return (
      <State title="No holdings to show">
        <p>
          Copy <code>config/portfolio.example.toml</code> to <code>config/portfolio.toml</code>, put your holdings in it and run the
          data build again. The file is private and ignored by git.
        </p>
        {h.history_note && <p className="small" role="status">{h.history_note}</p>}
      </State>
    )
  }
  const add = (ticker: string) => {
    if (!basket.some((b) => b.ticker === ticker)) setBasket([...basket, newItem(ticker)])
  }
  const show = (t: Tab) => !phone || tab === t
  return (
    <>
      <div className="pagehead">
        <div>
          <h1>Portfolio</h1>
          <p className="muted small">{h.label} · prices as of {h.asof} · EUR</p>
        </div>
        <div className="headtools">
          <ViewOptions value={view} onChange={setView} />
          <CommandField data={data} route={route} />
        </div>
      </div>
      {phone && (
        <div className="seg pf-tabs" role="group" aria-label="Section">
          <button type="button" aria-pressed={tab === 'holdings'} onClick={() => setTab('holdings')}>Holdings</button>
          <button type="button" aria-pressed={tab === 'additions'} onClick={() => setTab('additions')}>Additions</button>
          <button type="button" aria-pressed={tab === 'basket'} onClick={() => setTab('basket')}>Basket{basket.length > 0 && <span className="badge count">{basket.length}</span>}</button>
        </div>
      )}
      {show('holdings') && (
        <>
          <KeyStrip data={data} />
          <div className="pf-grid">
            <HoldingsTable data={data} route={route} more={view.columns} phone={phone} />
            <div className="pf-side">
              {view.chart && (h.history ? (
                <HistoryChart history={h.history} />
              ) : (
                <section aria-labelledby="nohistory-h">
                  <h2 id="nohistory-h" className="sechead">Return since first deposit</h2>
                  <div className="card panel"><p className="muted small">{h.history_note ?? 'No history file.'}</p></div>
                </section>
              ))}
              {view.groups && <GroupBars data={data} />}
            </div>
          </div>
        </>
      )}
      {(show('additions') || show('basket')) && (
        <>
          {!phone && <h2 className="sechead pf-adds">Researchable additions</h2>}
          <div className="pf-adds-grid">
            {show('additions') && (
              <div className="pf-cands">
                <p className="muted small">Sectors and funds you could read more about, from the dashboard’s lists. Screen results, not advice. Sectors with nothing in your portfolio come first.</p>
                <GapCards data={data} selected={card} onSelect={setCard} />
                <CandidateTable data={data} card={card} basket={basket} onAdd={add} route={route} />
              </div>
            )}
            {show('basket') && <BasketPanel data={data} basket={basket} setBasket={setBasket} />}
          </div>
        </>
      )}
    </>
  )
}
