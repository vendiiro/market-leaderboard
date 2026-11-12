#!/usr/bin/env python3
"""Run the pre-registered test of the trend and steadiness measures (docs/backtests/2026-11-12-measures-spec.json).

Needs network and yfinance:   uv run python scripts/backtest_measures.py

Writes docs/backtests/2026-11-12-measures-result.md and config/measure_evidence.json (the text the page shows).
One run per measure. Do not change engine/evidence.py or the spec after looking at a result: write a new dated
spec instead. Educational: a past difference between groups says nothing certain about the future.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.evidence import monthly_panels, spreads, verdict  # noqa: E402
from engine.fmt import pct  # noqa: E402
from engine.research import region_index  # noqa: E402
from engine.watchlists import all_tickers, load_watchlists  # noqa: E402

NAMES = {"trend": "long-term trend", "steady": "steadiness"}
UNTESTED = {"status": "untested", "text": "Not tested: free data has today's fundamentals only, not what was known at past dates."}


def sentence(name: str, v: dict) -> str:
    return (f"Tested on these companies' own price history ({v['months']} month-ends, {v['first']} to {v['last']}): the third ranked "
            f"highest by {name} returned {pct(v['mean'])} compared with the lowest third over the following 12 months, with a 90% "
            f"interval of {pct(v['lo'])} to {pct(v['hi'])}. "
            + ("The interval is above zero. " if v["status"] == "supported" else "The interval includes zero or lies below it: no reliable difference. ")
            + "The companies are today's survivors, which flatters the past.")


def main() -> int:
    import yfinance as yf

    tickers = all_tickers(load_watchlists())
    df = yf.download(tickers + ["^GSPC", "^STOXX"], period="max", interval="1d", auto_adjust=True, progress=False, threads=True)["Close"]
    panels = {t: monthly_panels(df[t], df[region_index(t)]) for t in tickers if df[t].notna().sum() > 0}
    result, evidence = {}, {"value": UNTESTED, "quality": UNTESTED}
    for m in NAMES:
        s = spreads(pd.DataFrame({t: p[m] for t, p in panels.items()}), pd.DataFrame({t: p["outcome"] for t, p in panels.items()}))
        result[m] = verdict(s)
        evidence[m] = {"status": result[m]["status"], "text": sentence(NAMES[m], result[m])}
    (ROOT / "config" / "measure_evidence.json").write_text(json.dumps(evidence, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    lines = ["# Test of the trend and steadiness measures: result\n", f"Run on {date.today()} with {len(panels)} tickers. Spec: `2026-11-12-measures-spec.json` (written before the run).\n",
             "| Measure | Month-ends | Period | Top third minus bottom third, next 12 months | 90% interval | Verdict |", "|---|---|---|---|---|---|"]
    for m, v in result.items():
        lines.append(f"| {NAMES[m]} | {v['months']} | {v['first']} to {v['last']} | {pct(v['mean'])} | {pct(v['lo'])} to {pct(v['hi'])} | {v['status']} |")
    lines += ["", "Read with the limits in the spec: today's survivors only, few independent observations, hand-picked companies.",
              "The page shows the sentences in `config/measure_evidence.json`."]
    (ROOT / "docs" / "backtests" / "2026-11-12-measures-result.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
