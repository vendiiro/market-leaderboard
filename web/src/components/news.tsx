// Headlines from the last 30 days for the shares you hold. News flow only: how many stories and which ones.
import { useEffect, useState } from 'react'
import { countLabel, loadNews, type News30 } from '../lib/news'

export function NewsFlow() {
  const [news, setNews] = useState<News30 | null | undefined>(undefined)
  useEffect(() => { void loadNews().then(setNews) }, [])
  if (news === undefined) return null
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
              What the news said about your holdings, as of {news.asof} ({news.source}). This counts and lists stories. It does not say whether
              they are good or bad news, and it is not advice.
            </p>
            <ul className="newslist">
              {news.companies.map((c) => (
                <li key={c.ticker}>
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
            {news.failed.length > 0 && <p className="muted small" role="status">Not fetched: {news.failed.map((f) => f.ticker).join(', ')}.</p>}
            <p className="muted small">Headlines are third-party text, shown as received. Funds and trackers often have few or no stories by name.</p>
          </>
        )}
      </div>
    </section>
  )
}
