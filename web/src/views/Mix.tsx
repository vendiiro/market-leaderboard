import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { InfoTip, State } from '../components/bits'
import type { Data, Portfolio } from '../data/load'
import { pct } from '../lib/format'
import { analyse, type Analysis, type ExposureKey } from '../lib/mix'
import { EMPTY, fromFile, load, save, toFile, type Mix, type Saved } from '../lib/storage'
import { treemap } from '../lib/treemap'

const GROUPS: { key: ExposureKey; label: string }[] = [
  { key: 'sector', label: 'Sector' },
  { key: 'country', label: 'Country' },
  { key: 'currency', label: 'Currency' },
  { key: 'lists', label: 'Watchlist' },
]

/** Horizontal bars with the value printed on each row, so nothing depends on colour or hover. */
function Bars({ rows, second }: { rows: { label: string; value: number; other?: number }[]; second?: boolean }) {
  return (
    <ul className="bars">
      {rows.map((r) => (
        <li key={r.label}>
          <span className="blabel">{r.label}</span>
          <span className="btrack" aria-hidden="true">
            {second && <span className="bfill ref" style={{ width: `${Math.min(100, (r.other ?? 0) * 100)}%` }} />}
            <span className="bfill" style={{ width: `${Math.min(100, Math.max(0, r.value) * 100)}%` }} />
          </span>
          <span className="num bvalue">
            {second && <span className="muted">{pct(r.other ?? 0, 0, false)} → </span>}
            {pct(r.value, 0, false)}
          </span>
        </li>
      ))}
    </ul>
  )
}

function Heatmap({ tickers, portfolio }: { tickers: string[]; portfolio: Portfolio }) {
  const index = new Map(portfolio.risk_tickers.map((t, i) => [t, i]))
  return (
    <div className="scrollx">
      <table className="heat">
        <caption className="sr-only">Correlation of weekly EUR returns between the companies in the mix</caption>
        <thead>
          <tr>
            <td />
            {tickers.map((t) => <th key={t} scope="col">{t}</th>)}
          </tr>
        </thead>
        <tbody>
          {tickers.map((a) => (
            <tr key={a}>
              <th scope="row">{a}</th>
              {tickers.map((b) => {
                const c = portfolio.corr[index.get(a)!][index.get(b)!]
                const tint = a === b ? 0 : Math.round(Math.min(1, Math.abs(c)) * 50)
                return (
                  <td key={b} className={`num${a === b ? ' diag' : ''}`}
                    style={{ background: `color-mix(in srgb, var(${c < 0 ? '--corr-neg' : '--corr-pos'}) ${tint}%, var(--surface))` }}>
                    {c.toFixed(2).replace('-', '−')}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Map of the mix: tile area = weight, colour = share of risk minus weight (cool = less risk than its weight,
 *  grey = equal, warm = more). Each tile prints both numbers, so the colour is never the only carrier. */
function MixMap({ risk }: { risk: NonNullable<Analysis['risk']> }) {
  const rects = treemap(risk.tickers.map((t) => ({ key: t, value: risk.weights[t] })))
  return (
    <>
      <div className="map" role="img" aria-label={`Map of the mix: ${risk.tickers.map((t) => `${t} weight ${pct(risk.weights[t], 0, false)}, share of risk ${pct(risk.contribution[t], 0, false)}`).join('; ')}`}>
        {rects.map((r) => {
          const diff = risk.contribution[r.key] - risk.weights[r.key]
          const tint = Math.round(Math.min(1, Math.abs(diff) / 0.1) * 40)
          return (
            <div key={r.key} className="maptile" style={{ left: `${r.x}%`, top: `${r.y}%`, width: `${r.w}%`, height: `${r.h}%` }}>
              <div style={{ background: `color-mix(in srgb, var(${diff < 0 ? '--risk-less' : '--risk-more'}) ${tint}%, var(--neutral-bar))` }}>
                <b>{r.key}</b>
                <span className="num">{pct(risk.weights[r.key], 0, false)} · risk {pct(risk.contribution[r.key], 0, false)}</span>
              </div>
            </div>
          )
        })}
      </div>
      <p className="legend small">
        Tile size = weight. Colour: <span className="key less" /> less risk than its weight <span className="key ref" /> about equal{' '}
        <span className="key more" /> more risk than its weight
      </p>
    </>
  )
}

function Result({ a, data }: { a: Analysis; data: Data }) {
  const listName = new Map(data.leaderboard.lists.map((l) => [l.key, l.name]))
  const top = a.risk ? Object.entries(a.risk.contribution).sort((x, y) => y[1] - x[1])[0] : null
  const sorted = (o: Record<string, number>) => Object.entries(o).sort((x, y) => y[1] - x[1] || x[0].localeCompare(y[0]))
  return (
    <>
      {a.missing.length > 0 && (
        <p className="banner warn" role="status">
          Left out, no data tonight: {a.missing.join(', ')}. The weights below are shares of the rest of the mix.
        </p>
      )}
      <dl className="tiles">
        <div>
          <dt>Mix volatility
            <InfoTip label="Mix volatility">
              <p>How much the value of the whole mix has varied, as a yearly figure in EUR. It comes from weekly returns over the last {data.portfolio.window.weeks} weeks, so currency moves count.</p>
              <p className="muted">An estimate from past data, not a forecast.</p>
            </InfoTip>
          </dt>
          <dd className="num">{a.risk ? pct(a.risk.vol, 1, false) : '—'}</dd>
        </div>
        <div>
          <dt>Effective number of names
            <InfoTip label="Effective number of names">
              <p>How many equally weighted companies would be as spread out as this mix. 4 equal weights give 4; one dominant weight pulls it towards 1.</p>
            </InfoTip>
          </dt>
          <dd className="num">{a.effectiveN.toFixed(1)}</dd>
        </div>
        <div>
          <dt>Largest share of risk
            <InfoTip label="Share of risk">
              <p>The part of the mix's ups and downs that comes from one company: its weight times how strongly it moves with the rest of the mix.</p>
            </InfoTip>
          </dt>
          <dd className="num">{top ? `${pct(top[1], 0, false)} ${top[0]}` : '—'}</dd>
        </div>
      </dl>
      {a.risk && a.risk.covered < 0.9999 && (
        <p className="banner warn" role="status">
          The risk numbers cover {pct(a.risk.covered, 0, false)} of the mix. Without risk data: {a.noRisk.map((x) => `${x.ticker} (${x.reason})`).join('; ')}.
        </p>
      )}
      {!a.risk && <p className="banner warn" role="status">No company in this mix has risk data yet, so only exposure is shown.</p>}

      <h3>Exposure</h3>
      <div className="groups">
        {GROUPS.map((g) => (
          <section key={g.key} aria-label={`Exposure by ${g.label.toLowerCase()}`}>
            <h4>{g.label}</h4>
            <Bars rows={sorted(a.exposure[g.key]).map(([k, v]) => ({ label: g.key === 'lists' ? listName.get(k) ?? k : k, value: v }))} />
          </section>
        ))}
      </div>
      <p className="muted small">A company on two watchlists counts in both, so watchlist shares can add up to more than 100 %.</p>

      {a.risk && (
        <>
          <h3>Map of the mix</h3>
          <MixMap risk={a.risk} />
          <h3>Weight and share of risk</h3>
          <p className="legend small"><span className="key ref" /> Weight <span className="key" /> Share of risk</p>
          <Bars second rows={sorted(a.risk.contribution).map(([t, v]) => ({ label: t, value: v, other: a.risk!.weights[t] }))} />
          {a.risk.tickers.length > 1 && (
            <>
              <h3>How the companies move together</h3>
              <p className="muted small">
                Correlation of weekly EUR returns: 1 means they moved together, 0 unrelated, below 0 in opposite directions.
              </p>
              <Heatmap tickers={a.risk.tickers} portfolio={data.portfolio} />
            </>
          )}
        </>
      )}
    </>
  )
}

function Editor({ mix, onChange, data }: { mix: Mix; onChange: (m: Mix) => void; data: Data }) {
  const [text, setText] = useState('')
  const [error, setError] = useState('')
  const listId = useId()
  const file = useRef<HTMLInputElement>(null)
  const universe = data.portfolio.tickers
  const nameOf = new Map(universe.map((t) => [t.ticker, t.name]))
  const total = mix.items.reduce((s, i) => s + (Number.isFinite(i.weight) ? i.weight : 0), 0)
  const set = (items: Mix['items']) => onChange({ ...mix, items })

  const add = (e: FormEvent) => {
    e.preventDefault()
    const q = text.trim().toLowerCase()
    const hit = universe.find((t) => t.ticker.toLowerCase() === q) ?? universe.find((t) => t.name.toLowerCase() === q)
    if (!hit) return setError(q ? `"${text.trim()}" is not in tonight's data. Pick a company from the list.` : 'Type a company or ticker first.')
    if (mix.items.some((i) => i.ticker === hit.ticker)) return setError(`${hit.name} is already in the mix.`)
    set([...mix.items, { ticker: hit.ticker, weight: 10 }])
    setText('')
    setError('')
  }
  const download = () => {
    const a = document.createElement('a')
    a.href = URL.createObjectURL(new Blob([toFile(mix)], { type: 'application/json' }))
    a.download = `${mix.name.toLowerCase().replace(/\s+/g, '-')}.json`
    a.click()
    URL.revokeObjectURL(a.href)
  }
  const upload = async (f: File | undefined) => {
    if (!f) return
    try {
      onChange({ ...fromFile(await f.text()), name: mix.name })
      setError('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'The file could not be read.')
    }
    if (file.current) file.current.value = ''
  }

  return (
    <div className="editor">
      <form onSubmit={add} className="addrow">
        <label className="sr-only" htmlFor={`${listId}-in`}>Company or ticker to add to {mix.name}</label>
        <input id={`${listId}-in`} list={listId} value={text} placeholder="Add a company or ticker" autoComplete="off"
          onChange={(e) => setText(e.target.value)} />
        <datalist id={listId}>{universe.map((t) => <option key={t.ticker} value={t.ticker}>{t.name}</option>)}</datalist>
        <button type="submit" className="btn primary">Add</button>
      </form>
      {error && <p className="banner crit" role="alert">{error}</p>}
      {mix.items.length > 0 && (
        <table className="weights">
          <thead>
            <tr><th scope="col" className="l">Company</th><td /><th scope="col">Weight</th><th scope="col">Share</th><td /></tr>
          </thead>
          <tbody>
            {mix.items.map((it, i) => (
              <tr key={it.ticker}>
                <th scope="row" className="l name"><b>{nameOf.get(it.ticker) ?? it.ticker}</b><span>{it.ticker}</span></th>
                <td className="slidercell">
                  <input type="range" min={0} max={100} step={1} value={Number.isFinite(it.weight) ? Math.min(100, it.weight) : 0}
                    aria-label={`Weight slider for ${nameOf.get(it.ticker) ?? it.ticker}`}
                    onChange={(e) => set(mix.items.map((x, j) => (j === i ? { ...x, weight: e.target.valueAsNumber } : x)))} />
                </td>
                <td>
                  <input type="number" min={0} step={1} inputMode="decimal" value={Number.isFinite(it.weight) ? it.weight : ''}
                    aria-label={`Weight of ${nameOf.get(it.ticker) ?? it.ticker}`}
                    onChange={(e) => set(mix.items.map((x, j) => (j === i ? { ...x, weight: Math.max(0, e.target.valueAsNumber || 0) } : x)))} />
                </td>
                <td className="num">{total > 0 ? pct(it.weight / total, 0, false) : '—'}</td>
                <td>
                  <button type="button" className="btn icon" aria-label={`Remove ${nameOf.get(it.ticker) ?? it.ticker}`}
                    onClick={() => set(mix.items.filter((_, j) => j !== i))}>×</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="actions">
        <button type="button" className="btn" disabled={!mix.items.length} onClick={() => set(mix.items.map((x) => ({ ...x, weight: 10 })))}>Equal weights</button>
        <button type="button" className="btn" disabled={!mix.items.length} onClick={download}>Export</button>
        <button type="button" className="btn" onClick={() => file.current?.click()}>Import</button>
        <input ref={file} type="file" accept="application/json,.json" hidden aria-label={`Import a file into ${mix.name}`}
          onChange={(e) => void upload(e.target.files?.[0])} />
        <button type="button" className="btn" disabled={!mix.items.length} onClick={() => set([])}>Clear</button>
      </div>
      {mix.items.length > 0 && Math.abs(total - 100) > 0.01 && (
        <p className="muted small">Weights add up to {total.toFixed(0)}; shares are scaled so they total 100 %.</p>
      )}
    </div>
  )
}

export default function MixView({ data }: { data: Data }) {
  const [saved, setSaved] = useState<Saved>(load)
  useEffect(() => save(saved), [saved])
  const mixes = saved.b ? ([['a', saved.a], ['b', saved.b]] as const) : ([['a', saved.a]] as const)
  const w = data.portfolio.window

  return (
    <>
      <div className="pagehead">
        <div>
          <h1>Mix</h1>
          <p className="muted small">
            Build a test mix to see where it is exposed and how its companies move together. Saved in this browser only.
          </p>
        </div>
        <div className="actions">
          {saved.b ? (
            <button type="button" className="btn" onClick={() => setSaved({ ...saved, b: null })}>Remove mix B</button>
          ) : (
            <button type="button" className="btn" disabled={!saved.a.items.length}
              onClick={() => setSaved({ ...saved, b: { name: 'Mix B', items: saved.a.items.map((x) => ({ ...x })) } })}>
              Compare with a copy
            </button>
          )}
          {(saved.a.items.length > 0 || saved.b) && <button type="button" className="btn" onClick={() => setSaved(EMPTY)}>Start over</button>}
        </div>
      </div>
      <div className={saved.b ? 'compare two' : 'compare'}>
        {mixes.map(([slot, mix]) => {
          const a = analyse(mix.items, data.portfolio)
          return (
            <section key={slot} className="card panel mix" aria-labelledby={`mix-${slot}`}>
              <h2 id={`mix-${slot}`}>{mix.name}</h2>
              {slot === 'b' && <p className="muted small">A copy of mix A: add or change a company here to see what changes.</p>}
              <Editor mix={mix} data={data} onChange={(m) => setSaved({ ...saved, [slot]: m })} />
              {a ? <Result a={a} data={data} /> : (
                <State title="No companies yet">
                  <p>Add a company above to see exposure and risk.</p>
                </State>
              )}
            </section>
          )
        })}
      </div>
      <p className="under">
        Risk numbers use weekly returns in EUR{w.start && w.end ? ` from ${w.start} to ${w.end}` : ''} ({w.weeks} weeks). They are
        estimates from past data, not forecasts. Exposure uses each company's current sector, country and trading currency.
        Educational, not advice.
      </p>
    </>
  )
}
