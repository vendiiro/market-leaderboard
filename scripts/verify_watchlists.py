#!/usr/bin/env python3
"""Check every ticker in config/watchlists.toml against Yahoo and write config/watchlists_verified.csv.

Needs network and yfinance:   uv run python scripts/verify_watchlists.py

It never edits the TOML; it reports a status per ticker (see engine/verify.py). A ticker that is not `ok` must be
fixed or removed from the TOML by hand. Exit code: 0 when every ticker is ok, 1 otherwise.
Sector and country are Yahoo's current values (not point-in-time).
"""
from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.exchanges import exchange_for  # noqa: E402
from engine.fx import fetch_fx_to_usd  # noqa: E402
from engine.verify import classify_row, yahoo_bars, yahoo_info  # noqa: E402
from engine.watchlists import all_tickers, membership, read  # noqa: E402

COLUMNS = ["ticker", "lists", "name", "yahoo_long_name", "sector", "country", "currency", "market_cap_eur",
           "first_bar", "last_bar", "bar_count", "status", "detail"]


def main() -> int:
    cfg = read()
    lists = {k: list(v["tickers"]) for k, v in cfg.items()}
    names = {t: n for v in cfg.values() for t, n in v["tickers"].items()}
    member, tickers = membership(lists), all_tickers(lists)
    ccys = {exchange_for(t).currency for t in tickers if exchange_for(t)} | {"EUR"}
    rates = fetch_fx_to_usd(ccys)
    bars = yahoo_bars(tickers)
    rows, bad = [], 0
    for t in tickers:
        info = yahoo_info(t)
        b = bars.get(t)
        row = classify_row(t, names[t], info, b if b else ({} if info is not None else None), date.today(), rates=rates)
        row.update(lists=";".join(member[t]), name=names[t], sector=(info or {}).get("sector") or "",
                   country=(info or {}).get("country") or "")
        rows.append({c: row.get(c, "") for c in COLUMNS})
        bad += row["status"] != "ok"
        print(f"{t:<12} {row['status']:<20} {row['detail']}")
    out = ROOT / "config" / "watchlists_verified.csv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows) - bad} of {len(rows)} tickers ok -> {out.relative_to(ROOT)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
