"""Last-30-days news flow for one share, from Google News RSS (keyless). Pure: scripts/news30.py does the fetching.

This counts and lists headlines. It is not a sentiment score and nothing here is tested as a predictor.
Headlines are third-party text, trimmed and shown as received."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote

MAX_TITLE = 160
WEEKS = 4


def feed_url(name: str, ticker: str) -> str:
    q = quote(f'"{name}" OR "{ticker.split(".")[0]}" stock when:30d')
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def _day(raw: str | None) -> date | None:
    try:
        return parsedate_to_datetime(raw).date() if raw else None
    except (TypeError, ValueError):
        return None


def parse_rss(xml_text: str, today: date, days: int = 30, terms: tuple[str, ...] = ()) -> list[dict]:
    """Newest first. Items outside the window, duplicates and (with `terms`) stories naming none of the terms are dropped."""
    seen: set[str] = set()
    out: list[dict] = []
    for it in ET.fromstring(xml_text).iter("item"):
        title = (it.findtext("title") or "").strip()
        d = _day(it.findtext("pubDate"))
        if not title or d is None or not 0 <= (today - d).days < days or title.lower() in seen:
            continue
        if terms and not any(t.lower() in title.lower() for t in terms):
            continue
        seen.add(title.lower())
        link = (it.findtext("link") or "").strip()
        out.append({
            "title": title[:MAX_TITLE],
            "source": (it.findtext("source") or "").strip()[:60],
            "url": link if link.startswith(("http://", "https://")) else None,
            "date": d.isoformat(),
        })
    return sorted(out, key=lambda x: x["date"], reverse=True)


FEED_CAP = 100   # Google News returns at most 100 items; at the cap the count and the weekly split lean to recent days


def summarize_news(items: list[dict], ticker: str, name: str, today: date, top: int = 8, raw_count: int = 0) -> dict:
    """Count, headlines per week (oldest week first; the last entry is the most recent 7 days) and the newest `top`.
    `raw_count` is the feed's item count before filtering; at FEED_CAP the result is flagged `capped`."""
    weeks = [0] * WEEKS
    for i in items:
        age = (today - date.fromisoformat(i["date"])).days
        weeks[WEEKS - 1 - min(age // 7, WEEKS - 1)] += 1
    return {"ticker": ticker, "name": name, "asof": today.isoformat(), "count": len(items), "capped": raw_count >= FEED_CAP, "per_week": weeks, "items": items[:top]}
