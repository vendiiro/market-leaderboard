// Headlines from the last 30 days: your holdings, tonight's research candidates and other names with an unusually upbeat week.
// News flow only. The tone label is a keyword match on the headline, not tested as a predictor.
import { useEffect, useState } from 'react'
import { balanceWord, countLabel, loadNews, type NewsCompany, type News30 } from '../lib/news'

function Stories({ list, upbeatOnly }: { list: NewsCompany[]; upbeatOnly: boolean }) {
  return (
    <ul className="newslist">
      {list.map((c) => {
        const items = upbeatOnly ? c.items.filter((i) => i.tone === 'upbeat') : c.items
        return (
          <li key={c.group + c.ticker}>
            <details>
              <summary>
                <b>{c.name}</b> <span className="muted small">{c.ticker}</span>{' '}
                <span className="num">{c.upbeat} upbeat · {c.down} downbeat</span>
                <span className="muted small"> of {countLabel(c)} stories: {balanceWord(c.balance)} · last 7 days {c.upbeat_week} up, {c.down_week} down · per week, oldest to newest: <span className="num">{c.per_week.join(' · ')}</span></span>
              </summary>
              {items.length === 0 ? (
                <p className="muted small">{upbeatOnly ? 'No upbeat story among the newest ones. Switch to all stories to see the rest.' : 'No story from the last 30 days named this company.'}</p>
              ) : (
                <ul className="news">
                  {items.map((i) => (
                    <li key={i.title + i.date}>
                      {i.url ? <a href={i.url} target="_blank" rel="noopener noreferrer">{i.title}</a> : i.title}
                      <span className="muted small"> · {i.source || 'unknown source'} · {i.date}{i.tone === 'downbeat' ? ' · downbeat' : ''}</span>
                    </li>
                  ))}
                </ul>
              )}
              {c.capped && <p className="muted small">The news feed was full, so the counts are minimums and recent days are over-represented.</p>}
            </details>
          </li>
        )
      })}
    </ul>
  )
}

export function NewsFlow() {
  const [news, setNews] = useState<News30 | null | undefined>(undefined)
  const [upbeatOnly, setUpbeatOnly] = useState(true)
  useEffect(() => { void loadNews().then(setNews) }, [])
  if (news === undefined) return null
  const group = (g: NewsCompany['group']) => news?.companies.filter((c) => c.group === g) ?? []
  const held = group('holding')
  const cands = group('candidate')
  const found = group('discovery')
  return (
    <section aria-labelledby="news-h">
      <h2 id="news-h" className="sechead">Headlines, last 30 days</h2>
      <div className="card panel newsflow">
        {news === null ? (
          <p className="muted small">
            No headlines loaded. Create them with <code>uv run python scripts/news30.py --discover</code> and reload this page.
          </p>
        ) : (
          <>
            <div className="newshead">
              <p className="muted small">
                As of {news.asof} ({news.source}). Each story is marked upbeat when its headline holds an upbeat phrase (record, raises outlook,
                invests, new contract, upgrade) and no downbeat one. That is a keyword match: it is not tested as a predictor, it misses context,
                and promotional sites write upbeat headlines too. Not advice.
              </p>
              <div className="seg" role="group" aria-label="Which stories to list">
                <button type="button" aria-pressed={upbeatOnly} onClick={() => setUpbeatOnly(true)}>Upbeat only</button>
                <button type="button" aria-pressed={!upbeatOnly} onClick={() => setUpbeatOnly(false)}>All stories</button>
              </div>
            </div>
            <h3>Your holdings</h3>
            {held.length ? <Stories list={held} upbeatOnly={upbeatOnly} /> : <p className="muted small">No holding was fetched.</p>}
            {cands.length > 0 && (
              <>
                <h3>Research candidates</h3>
                <p className="muted small">Names on tonight’s shortlist, so you can read up on them. Being on the shortlist is a screen result, not a recommendation.</p>
                <Stories list={cands} upbeatOnly={upbeatOnly} />
              </>
            )}
            {found.length > 0 && (
              <>
                <h3>Unusually upbeat this week</h3>
                <p className="muted small">Other names on the dashboard with at least 5 stories in the last 7 days, more than twice their usual weekly count, and several upbeat ones. A busy news week is a reason to read, not a reason to act.</p>
                <Stories list={found} upbeatOnly={upbeatOnly} />
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
