// Headlines from the last 30 days for the shares you hold and for tonight's research candidates.
// News flow only: how many stories and which ones. It does not judge them.
import { useEffect, useState } from 'react'
import { countLabel, loadNews, type NewsCompany, type News30 } from '../lib/news'

function Stories({ list }: { list: NewsCompany[] }) {
  return (
    <ul className="newslist">
      {list.map((c) => (
        <li key={c.group + c.ticker}>
          <details>
            <summary>
              <b>{c.name}</b> <span className="muted small">{c.ticker}</span>{' '}
              <span className="num">{countLabel(c)} {c.count === 1 ? 'story' : 'stories'}</span>
              <span className="muted small"> · per week, oldest to newest: <span className="num">{c.per_week.join(' · ')}</span></span>
            </summary>
            {c.items.length === 0 ? (
              <p className="muted small">No story from the last 30 days named this company.</p>
            ) : (
              <ul className="news">
                {c.items.map((i) => (
                  <li key={i.title + i.date}>
                    {i.url ? <a href={i.url} target="_blank" rel="noopener noreferrer">{i.title}</a> : i.title}
                    <span className="muted small"> · {i.source || 'unknown source'} · {i.date}</span>
                  </li>
                ))}
              </ul>
            )}
            {c.capped && <p className="muted small">The news feed was full, so the count is a minimum and recent days are over-represented.</p>}
          </details>
        </li>
      ))}
    </ul>
  )
}

export function NewsFlow() {
  const [news, setNews] = useState<News30 | null | undefined>(undefined)
  useEffect(() => { void loadNews().then(setNews) }, [])
  if (news === undefined) return null
  const held = news?.companies.filter((c) => c.group === 'holding') ?? []
  const cands = news?.companies.filter((c) => c.group === 'candidate') ?? []
  return (
    <section aria-labelledby="news-h">
      <h2 id="news-h" className="sechead">Headlines, last 30 days</h2>
      <div className="card panel newsflow">
        {news === null ? (
          <p className="muted small">
            No headlines loaded. Create them with <code>uv run python scripts/news30.py</code> and reload this page.
          </p>
        ) : (
          <>
            <p className="muted small">
              As of {news.asof} ({news.source}). This counts and lists stories. It does not say whether they are good or bad news, and it is not advice.
            </p>
            <h3>Your holdings</h3>
            {held.length ? <Stories list={held} /> : <p className="muted small">No holding was fetched.</p>}
            {cands.length > 0 && (
              <>
                <h3>Research candidates</h3>
                <p className="muted small">Names on tonight’s shortlist, so you can read up on them. Being on the shortlist is a screen result, not a recommendation.</p>
                <Stories list={cands} />
              </>
            )}
            {news.failed.length > 0 && <p className="muted small" role="status">Not fetched: {news.failed.map((f) => f.ticker).join(', ')}.</p>}
            <p className="muted small">Headlines are third-party text, shown as received. Funds and trackers often have few or no stories by name.</p>
          </>
        )}
      </div>
    </section>
  )
}
