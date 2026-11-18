"""Last-30-days headlines for the shares you hold (config/portfolio.toml) or for given tickers.

Writes web/public/data/news30.json (git-ignored: it names your holdings). Source: Google News RSS, no key needed.
This is news flow (how many headlines, which ones), not sentiment. Usage:
    uv run python scripts/news30.py [--tickers A,B] [--pause 1.0]"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path
from xml.etree.ElementTree import ParseError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.holdings import read_holdings  # noqa: E402
from engine.news import feed_url, parse_rss, summarize_news  # noqa: E402

OUT = ROOT / "web" / "public" / "data" / "news30.json"
UA = "Mozilla/5.0 (compatible; market-leaderboard research tool)"


def fetch(url: str) -> str:
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", help="comma list; default is every holding that has a Yahoo ticker")
    ap.add_argument("--pause", type=float, default=1.0, help="seconds between requests")
    a = ap.parse_args()
    if a.tickers:
        targets = [(t.strip(), t.strip()) for t in a.tickers.split(",") if t.strip()]
    else:
        held = read_holdings()
        if held is None:
            print("No config/portfolio.toml: pass --tickers.")
            return 1
        targets = [(h.ticker, h.name) for h in held.holdings if h.ticker]
    today, companies, failed = date.today(), [], []
    for ticker, name in targets:
        words = tuple(w for w in [ticker.split(".")[0], name.split()[0]] if len(w) >= 3)
        try:
            xml = fetch(feed_url(name, ticker))
            companies.append(summarize_news(parse_rss(xml, today, terms=words), ticker, name, today, raw_count=xml.count("<item>")))
        except (OSError, ParseError) as e:
            failed.append({"ticker": ticker, "reason": type(e).__name__})
        time.sleep(a.pause)
    OUT.write_text(json.dumps({"schema_version": 1, "asof": today.isoformat(), "source": "Google News RSS", "companies": companies, "failed": failed}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"news30: {len(companies)} ok, {len(failed)} failed -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
