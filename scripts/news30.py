"""Last-30-days headlines for the shares you hold (config/portfolio.toml) and for tonight's research candidates.

Writes web/public/data/news30.json (git-ignored: it names your holdings). Sources: Google News RSS and the Hacker News
search (Algolia), both keyless. This is news flow (how many headlines, which ones), not sentiment. Usage:
    uv run python scripts/news30.py [--tickers A,B] [--no-candidates] [--limit 8] [--discover] [--keep 5] [--pause 1.0]"""
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
from engine.news import feed_url, hn_url, is_unusual, merge_items, parse_hn, parse_rss, summarize_news  # noqa: E402

OUT = ROOT / "web" / "public" / "data" / "news30.json"
UA = "Mozilla/5.0 (compatible; market-leaderboard research tool)"


def fetch(url: str) -> str:
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def headlines(ticker: str, name: str, today: date, group: str) -> dict:
    """Google News plus Hacker News for one share. One source failing leaves the other; both failing raises."""
    words = tuple(w for w in [ticker.split(".")[0], name.split()[0]] if len(w) >= 3)
    lists, raw, errors = [], 0, []
    try:
        xml = fetch(feed_url(name, ticker))
        lists.append(parse_rss(xml, today, terms=words))
        raw = xml.count("<item>")
    except (OSError, ParseError) as e:
        errors.append(e)
    try:
        lists.append(parse_hn(fetch(hn_url(name.split()[0], today)), today, terms=words))
    except (OSError, ValueError) as e:
        errors.append(e)
    if len(errors) == 2:
        raise errors[0]
    return summarize_news(merge_items(*lists), ticker, name, today, raw_count=raw, group=group)


def names_all(root: Path) -> dict[str, str]:
    """Every company on the dashboard, from research.json; empty when the file is missing."""
    try:
        research = json.loads((root / "web" / "public" / "data" / "research.json").read_text(encoding="utf-8"))
        return {c["ticker"]: c["name"] for c in research["companies"]}
    except (OSError, KeyError, ValueError):
        return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", help="comma list instead of the holdings")
    ap.add_argument("--no-candidates", action="store_true", help="skip tonight's research shortlist")
    ap.add_argument("--limit", type=int, default=8, help="most candidates to fetch")
    ap.add_argument("--discover", action="store_true", help="also scan the dashboard's other names for an unusually upbeat week (about 2 minutes)")
    ap.add_argument("--keep", type=int, default=5, help="most discovered names to keep")
    ap.add_argument("--pause", type=float, default=1.0, help="seconds between requests")
    a = ap.parse_args()
    if a.tickers:
        targets = [(t.strip(), t.strip(), "holding") for t in a.tickers.split(",") if t.strip()]
    else:
        held = read_holdings()
        if held is None:
            print("No config/portfolio.toml: pass --tickers.")
            return 1
        targets = [(h.ticker, h.name, "holding") for h in held.holdings if h.ticker]
    if not a.no_candidates and not a.tickers:
        data_dir = ROOT / "web" / "public" / "data"
        try:
            research = json.loads((data_dir / "research.json").read_text(encoding="utf-8"))
            names = {c["ticker"]: c["name"] for c in research["companies"]}
            owned = {t for t, _, _ in targets}
            targets += [(t, names.get(t, t), "candidate") for t in research["shortlist"] if t not in owned][: a.limit]
        except (OSError, KeyError, ValueError):
            print("research.json not readable: candidates skipped.")
    today, companies, failed = date.today(), [], []
    for ticker, name, group in targets:
        try:
            companies.append(headlines(ticker, name, today, group))
        except (OSError, ValueError, ParseError) as e:
            failed.append({"ticker": ticker, "reason": type(e).__name__})
        time.sleep(a.pause)
    if a.discover and not a.tickers:
        seen = {t for t, _, _ in targets}
        found = []
        for t, name in names_all(ROOT).items():
            if t in seen:
                continue
            try:
                c = headlines(t, name, today, "discovery")
            except (OSError, ValueError, ParseError):
                continue          # a name that cannot be fetched is simply not considered
            if is_unusual(c["per_week"], c["capped"]) and c["upbeat_week"] >= 2:
                found.append(c)
            time.sleep(a.pause)
        companies += sorted(found, key=lambda c: c["upbeat_week"], reverse=True)[: a.keep]
    OUT.write_text(json.dumps({"schema_version": 3, "asof": today.isoformat(), "source": "Google News RSS, Hacker News", "companies": companies, "failed": failed}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"news30: {len(companies)} ok, {len(failed)} failed -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
