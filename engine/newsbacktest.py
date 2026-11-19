"""Pure pieces of the news-tone backtest (spec: docs/backtests/2026-11-18-news-tone-spec.json).

scripts/backtest_news.py does the fetching and runs one test per measure. Nothing here may be tuned after a result."""
from __future__ import annotations

from datetime import date, timedelta
from urllib.parse import quote

import pandas as pd

from .news import balance, tone

MIN_STORIES = 4        # stories in the month for a company to count at all
MIN_TONED = 2          # upbeat or downbeat stories needed for the balance measure


def month_ends(first: str = "2023-11", last: str = "2025-10") -> list[pd.Period]:
    return list(pd.period_range(first, last, freq="M"))


def month_bounds(p: pd.Period) -> tuple[date, date]:
    """First and last calendar day of the month."""
    return p.start_time.date(), p.end_time.date()


def month_url(name: str, ticker: str, start: date, end: date) -> str:
    """Google News RSS limited to one calendar month (before: is exclusive)."""
    q = quote(f'"{name}" OR "{ticker.split(".")[0]}" stock after:{start.isoformat()} before:{(end + timedelta(days=1)).isoformat()}')
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def month_counts(items: list[dict]) -> dict[str, int]:
    tones = [tone(i["title"]) for i in items]
    return {"n": len(tones), "up": tones.count("upbeat"), "down": tones.count("downbeat")}


def measures(counts: dict[str, dict[pd.Period, dict[str, int]]]) -> dict[str, pd.DataFrame]:
    """month x ticker frames: upbeat_share and balance. A company-month that is not eligible is NaN."""
    share: dict[str, dict] = {}
    bal: dict[str, dict] = {}
    for t, months in counts.items():
        share[t] = {m: c["up"] / c["n"] for m, c in months.items() if c["n"] >= MIN_STORIES}
        bal[t] = {m: balance(c["up"], c["down"]) for m, c in months.items() if c["n"] >= MIN_STORIES and c["up"] + c["down"] >= MIN_TONED}
    return {"upbeat_share": pd.DataFrame(share), "balance": pd.DataFrame(bal)}


def next_month_returns(close: pd.Series) -> pd.Series:
    """Return from the last close of each month to the last close of the next month, indexed by the first month."""
    c = close.dropna()
    c.index = pd.DatetimeIndex(c.index).tz_localize(None)
    last = c.groupby(c.index.to_period("M")).last()
    return (last.shift(-1) / last - 1).dropna()
