"""Nightly step: for tonight's shortlist, ask the last30days engine what people said in the last 30 days.

Writes web/public/data/sentiment.json (git-ignored). One slow or failing ticker never stops the rest.
Needs the last30days skill (`npx skills add mvanhorn/last30days-skill -g`) and Python 3.12 through uv.
Only keyless sources are used: Reddit, Hacker News, Polymarket, GitHub and the web. Usage:
    uv run python scripts/sentiment.py [--tickers A,B] [--limit 6] [--timeout 150]"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.sentiment import SOURCES, extract_json, summarize  # noqa: E402

SKILL = Path(os.environ.get("LAST30DAYS_DIR", Path.home() / ".agents" / "skills" / "last30days"))
OUT = ROOT / "web" / "public" / "data" / "sentiment.json"


def run_engine(ticker: str, name: str, timeout: int) -> dict:
    base = ticker.split(".")[0]
    cmd = ["uv", "run", "--python", "3.12", "python", str(SKILL / "scripts" / "last30days.py"), "--research-only", "--quick",
           "--emit", "json", "--ticker", f"{base}:{name}", "--search", ",".join(SOURCES), "--days", "30", f"{name} {base} stock"]
    env = {**os.environ, "LAST30DAYS_ALLOW_ENGINE_PLAN": "1"}   # headless run: the engine plans its own queries
    done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=timeout, env=env, cwd=SKILL)
    return extract_json(done.stdout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", help="comma list; default is tonight's shortlist")
    ap.add_argument("--limit", type=int, default=6)
    ap.add_argument("--timeout", type=int, default=150)
    a = ap.parse_args()
    research = json.loads((ROOT / "web" / "public" / "data" / "research.json").read_text(encoding="utf-8"))
    names = {c["ticker"]: c["name"] for c in research["companies"]}
    tickers = [t.strip() for t in a.tickers.split(",")] if a.tickers else research["shortlist"][: a.limit]
    asof, companies, failed = date.today().isoformat(), [], []
    for t in tickers:
        try:
            name = names.get(t, t)
            words = tuple(w for w in [t.split(".")[0], name.split()[0]] if len(w) >= 3)
            companies.append(summarize(run_engine(t, name, a.timeout), t, asof, terms=words))
        except (subprocess.TimeoutExpired, ValueError, OSError) as e:
            failed.append({"ticker": t, "reason": type(e).__name__})
    OUT.write_text(json.dumps({"schema_version": 1, "asof": asof, "companies": companies, "failed": failed}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"sentiment: {len(companies)} ok, {len(failed)} failed -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
