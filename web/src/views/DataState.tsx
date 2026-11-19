import type { Data } from '../data/load'

export default function DataState({ data }: { data: Data }) {
  const { meta } = data
  return (
    <>
      <div className="pagehead"><div><h1>Tonight&rsquo;s data</h1></div></div>
      <section className="card panel" style={{ marginTop: 0 }}>
        <p>Data as of {meta.asof}: {meta.usable} of {meta.tickers} companies have prices.</p>
        <table className="board plain">
          <thead><tr><th scope="col" className="l">Watchlist</th><th scope="col">Companies</th><th scope="col">With prices</th></tr></thead>
          <tbody>{meta.lists.map((l) => <tr key={l.key}><th scope="row" className="l">{l.name}</th><td className="num">{l.count}</td><td className="num">{l.usable}</td></tr>)}</tbody>
        </table>
        {meta.failures.length > 0 && (
          <>
            <h3 style={{ marginTop: 14 }}>No data tonight</h3>
            <ul>{meta.failures.map((f) => <li key={f.ticker}>{f.name} ({f.ticker}): {f.reason}</li>)}</ul>
          </>
        )}
        <h3 style={{ marginTop: 14 }}>What to keep in mind</h3>
        <ul className="muted">{meta.notes.map((n) => <li key={n}>{n}</li>)}</ul>
      </section>
    </>
  )
}
