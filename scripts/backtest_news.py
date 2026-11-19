#!/usr/bin/env python3
"""Run the pre-registered news-tone test (docs/backtests/2026-11-18-news-tone-spec.json).

Needs network and yfinance:   uv run python scripts/backtest_news.py

Fetches one Google News RSS month per company (about 1500 requests; each answer is cached in data/news_backtest/, so
an interrupted run resumes), then writes docs/backtests/2026-11-18-news-tone-result.md.
One run per measure. Do not change engine/news.py word lists, engine/newsbacktest.py or the spec after looking at a
result: write a new dated spec instead. Educational: a past difference says nothing certain about the future.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path
from xml.etree.ElementTree import ParseError

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.evidence import block_interval, spreads  # noqa: E402
from engine.fmt import pct  # noqa: E402
from engine.news import parse_rss  # noqa: E402
from engine.newsbacktest import MIN_STORIES, MIN_TONED, measures, month_bounds, month_counts, month_ends, month_url, next_month_returns  # noqa: E402
from engine.watchlists import all_tickers, load_watchlists  # noqa: E402

CACHE = ROOT / "data" / "news_backtest"
UA = "Mozilla/5.0 (compatible; market-leaderboard research tool)"
NAMES = {"upbeat_share": "upbeat share (ignores bad news)", "balance": "balance (uses bad news)"}


def fetch(url: str) -> str:
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=25) as r:
        return r.read().decode("utf-8", "replace")


def month_items(ticker: str, name: str, month: pd.Period, pause: float) -> list[dict] | None:
    """Stories of one company-month, from the cache or Google. None when the request failed (not cached, retried next run)."""
    path = CACHE / f"{ticker}_{month}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    start, end = month_bounds(month)
    words = tuple(w for w in [ticker.split(".")[0], name.split()[0]] if len(w) >= 3)
    try:
        items = parse_rss(fetch(month_url(name, ticker, start, end)), end, days=(end - start).days + 1, terms=words)
    except (OSError, ParseError):
        return None
    path.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    time.sleep(pause)
    return items


def main() -> int:
    import yfinance as yf

    CACHE.mkdir(parents=True, exist_ok=True)
    pause = 1.5   # slower than the first run, which Google rate-limited; not a test parameter
    tickers = all_tickers(load_watchlists())
    research = json.loads((ROOT / "web" / "public" / "data" / "research.json").read_text(encoding="utf-8"))
    names = {c["ticker"]: c["name"] for c in research["companies"]}
    months = month_ends()
    counts: dict[str, dict[pd.Period, dict[str, int]]] = {}
    missing = 0
    for k, t in enumerate(tickers, 1):
        counts[t] = {}
        for m in months:
            items = month_items(t, names.get(t, t), m, pause)
            if items is None:
                missing += 1
                continue
            counts[t][m] = month_counts(items)
        print(f"{k}/{len(tickers)} {t}", flush=True)
    close = yf.download(tickers, period="max", interval="1d", auto_adjust=True, progress=False, threads=True)["Close"]
    outcome = pd.DataFrame({t: next_month_returns(close[t]) for t in tickers if t in close and close[t].notna().sum() > 0})
    frames = measures(counts)
    rows = []
    for key, label in NAMES.items():
        s = spreads(frames[key], outcome)
        lo, hi = block_interval(s, block=3)
        mean = float(s.mean()) if len(s) else float("nan")
        status = "supported" if lo == lo and lo > 0 else "not supported"
        rows.append((label, len(s), mean, lo, hi, status))
    eligible = {k: int(frames[k].notna().sum().sum()) for k in NAMES}
    lines = ["# News tone test: result\n",
             f"Run on {date.today()} with {len(tickers)} tickers, {len(months)} formation months ({months[0]} to {months[-1]}). Spec: `2026-11-18-news-tone-spec.json` (written and committed before the run).\n",
             f"Requests that failed and were left out: {missing}. Company-months that met the eligibility rule (at least {MIN_STORIES} stories; balance also at least {MIN_TONED} toned): "
             + ", ".join(f"{NAMES[k]} {v}" for k, v in eligible.items()) + ".\n",
             "| Measure | Months used | Top third minus bottom third, next month | 90% interval | Verdict |", "|---|---|---|---|---|"]
    for label, n, mean, lo, hi, status in rows:
        lines.append(f"| {label} | {n} | {pct(mean)} | {pct(lo)} to {pct(hi)} | {status} |")
    lines += ["", "Read with the limits in the spec: a sample of Google's archive, today's survivors only, 24 months, tone from keywords.",
              "A difference between groups in the past says nothing certain about the future. Not advice."]
    out = ROOT / "docs" / "backtests" / "2026-11-18-news-tone-result.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
