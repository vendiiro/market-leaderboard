"""Network layer for the research view: annual statements (cached), unadjusted closes, region indices, headlines.

Yahoo through yfinance, imported inside the functions so tests never touch the network. Everything returned is
plain data; headlines are third-party text and are only ever shown as text."""
from __future__ import annotations

import json
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

from .cache import atomic_write_json

STATEMENT_MAX_AGE_DAYS = 30          # annual statements change once a year
ROWS = {"net_income": "Net Income", "eps": "Diluted EPS", "revenue": "Total Revenue"}


def _yahoo_statement(ticker: str) -> dict:
    import yfinance as yf

    inc = yf.Ticker(ticker).income_stmt
    return {key: {str(c)[:10]: (None if pd.isna(v) else float(v)) for c, v in inc.loc[row].items()}
            for key, row in ROWS.items() if row in inc.index}


def fetch_statements(tickers: list[str], cache_path: Path, fetch: Callable[[str], dict] | None = None,
                     now: float | None = None, pace: float = 0.3, sleep: Callable[[float], None] = time.sleep) -> dict:
    """{ticker: {net_income, eps, revenue: {fiscal year end: value}}} from a cache refreshed every 30 days.
    A ticker whose fetch fails keeps its old entry; one that never worked is simply absent."""
    fetch = fetch or _yahoo_statement
    now = time.time() if now is None else now
    try:
        cache = json.loads(Path(cache_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    changed = False
    for t in tickers:
        if t in cache and now - cache[t].get("ts", 0) < STATEMENT_MAX_AGE_DAYS * 86400:
            continue
        try:
            d = fetch(t)
        except Exception:
            d = None
        if d and any(d.values()):
            cache[t] = {"ts": now, "d": d}
            changed = True
        sleep(pace)
    if changed:
        atomic_write_json(cache_path, cache)
    return {t: cache[t]["d"] for t in tickers if t in cache}


def fetch_raw_closes(tickers: list[str], period: str = "6y") -> dict[str, pd.Series]:
    """Closes adjusted for splits only (not dividends): the price level a P/E at a past year-end needs."""
    import yfinance as yf

    df = yf.download(tickers, period=period, interval="1d", auto_adjust=False, group_by="ticker", threads=True, progress=False)
    out = {}
    for t in tickers:
        try:
            s = (df[t] if isinstance(df.columns, pd.MultiIndex) else df)["Close"].dropna()
        except (KeyError, TypeError):
            continue
        if len(s):
            out[t] = s
    return out


def fetch_indices(symbols: list[str], period: str = "4y") -> dict[str, pd.Series]:
    import yfinance as yf

    out = {}
    for sym in symbols:
        try:
            c = yf.Ticker(sym).history(period=period)["Close"].dropna()
        except Exception:
            continue
        if len(c):
            c.index = pd.DatetimeIndex(c.index).tz_localize(None).normalize()
            out[sym] = c
    return out


def parse_headlines(items: list, asof: date, limit: int = 5, max_days: int = 14) -> list[dict]:
    """Yahoo news items -> [{title, source, url, date, days_old}] for items from the last `max_days` days.
    Only http(s) links are kept; titles are cut to 200 characters and never interpreted."""
    out = []
    for n in items:
        c = n.get("content") if isinstance(n.get("content"), dict) else n
        title = c.get("title")
        raw = c.get("pubDate") or c.get("displayTime") or c.get("providerPublishTime")
        try:
            day = (datetime.fromtimestamp(raw, timezone.utc) if isinstance(raw, (int, float))
                   else datetime.fromisoformat(str(raw).replace("Z", "+00:00"))).date()
        except (TypeError, ValueError, OSError):
            continue
        age = (asof - day).days
        if not isinstance(title, str) or not title.strip() or age > max_days:
            continue
        provider = c.get("provider")
        url = next((c[k]["url"] for k in ("canonicalUrl", "clickThroughUrl") if isinstance(c.get(k), dict) and c[k].get("url")), c.get("link"))
        out.append({"title": title.strip()[:200], "source": (provider.get("displayName") if isinstance(provider, dict) else c.get("publisher")) or "",
                    "url": url if isinstance(url, str) and url.startswith(("https://", "http://")) else None,
                    "date": str(day), "days_old": max(age, 0)})
    return sorted(out, key=lambda h: h["days_old"])[:limit]


def fetch_headlines(tickers: list[str], asof: date, pace: float = 0.3) -> dict[str, list[dict]]:
    import yfinance as yf

    out = {}
    for t in tickers:
        try:
            out[t] = parse_headlines(yf.Ticker(t).news or [], asof)
        except Exception:
            out[t] = []
        time.sleep(pace)
    return out
