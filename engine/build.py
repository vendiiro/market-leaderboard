"""The pipeline: inputs -> leaderboard, movers, portfolio, meta -> schema check -> files.

    python -m engine build                 live data (Yahoo) into web/public/data
    python -m engine build --demo          synthetic data, no network
    python -m engine build --out DIR --asof 2026-11-10

Exit codes: 0 written; 2 too few tickers had usable data, the previous files are kept; 1 any other error (previous
files are kept as well: nothing is renamed into place before every file has been computed, checked and written).
Educational research tool: the output describes screen results and exposure, never advice."""
from __future__ import annotations

import csv
import json
import math
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from jsonschema import Draft202012Validator

from . import demo, leaderboard, movers, portfolio, watchlists
from .config import ROOT, Settings, load_settings
from .returns import PERIODS

SCHEMA_VERSION = 1
FILES = ("leaderboard", "movers", "portfolio", "meta")        # meta last: it is the file the page reads first
SCHEMAS = ROOT / "schemas"
DEFAULT_OUT = ROOT / "web" / "public" / "data"
NOTES = [
    "Educational research tool: screen results and exposure views, not investment advice.",
    "Prices are daily adjusted closes from Yahoo Finance, pulled after the close; fundamentals are current values, not point-in-time.",
    "Returns and 1-year volatility are in each stock's own currency.",
    "Mix risk numbers use weekly returns in EUR over the last 104 complete weeks; they are estimates, not forecasts.",
    "The dip flag and the quality score are untested screen rules.",
]


def live_inputs(root: Path = ROOT) -> dict:
    """Fetch everything the build needs from Yahoo. Only tickers that passed verification are used."""
    from .data import fetch_fundamentals, fetch_prices, pull_prices
    from .fx import fetch_fx_to_usd, fx_history_eur

    cfg = watchlists.read(root / "config" / "watchlists.toml")
    lists = {k: list(v["tickers"]) for k, v in cfg.items()}
    member = watchlists.membership(lists)
    names = {t: n for v in cfg.values() for t, n in v["tickers"].items()}
    with (root / "config" / "watchlists_verified.csv").open(encoding="utf-8", newline="") as fh:
        verified = {r["ticker"]: r for r in csv.DictReader(fh)}
    meta, reasons = {}, {}
    for t in watchlists.all_tickers(lists):
        v = verified.get(t)
        meta[t] = {"name": names[t], "lists": member[t], "currency": (v or {}).get("currency") or None,
                   "sector": (v or {}).get("sector") or None, "country": (v or {}).get("country") or None}
        if not v or v["status"] != "ok":
            reasons[t] = "not verified against Yahoo (run scripts/verify_watchlists.py)"
    ok = [t for t in meta if t not in reasons]
    prices, _ = pull_prices(ok, lambda batch: fetch_prices(batch, period="3y"), reasons=reasons)
    fund = fetch_fundamentals(ok, root / "data" / "fundamentals.json")
    ccys = {meta[t]["currency"] for t in ok}
    start = str(date.today() - timedelta(days=3 * 366))
    return {"cfg": cfg, "meta": meta, "prices": {t: prices[t] for t in ok if t in prices}, "fund": fund,
            "rates_usd": fetch_fx_to_usd(ccys | {"EUR"}), "fx": fx_history_eur(ccys, start), "reasons": reasons}


def compute(inp: dict, settings: Settings, asof: date | None = None, built_at: str | None = None,
            is_demo: bool = False) -> dict[str, dict]:
    """{file stem: payload} for the four output files."""
    prices = inp["prices"]
    last_bars = [p[0].dropna().index[-1].date() for p in prices.values() if len(p[0].dropna())]
    if not last_bars:
        raise RuntimeError("no price data at all")
    asof = asof or max(last_bars)
    rows, failures = leaderboard.rows(prices, inp["fund"], inp["meta"], settings, asof, inp["rates_usd"])
    for f in failures:
        f["reason"] = inp["reasons"].get(f["ticker"], f["reason"])
    head = {"schema_version": SCHEMA_VERSION, "asof": str(asof)}

    live = {r["ticker"] for r in rows}
    weekly, no_risk = portfolio.weekly_eur_returns({t: prices[t][0] for t in live},
                                                   {t: inp["meta"][t]["currency"] for t in live}, inp["fx"], asof)
    cov = portfolio.covariance(weekly)
    vol = {t: math.sqrt(cov.loc[t, t]) for t in cov.index}
    out = {
        "leaderboard": head | {"periods": list(PERIODS), "lists": leaderboard.lists(rows, inp["cfg"])},
        "movers": head | movers.movers(rows),
        "portfolio": head | {
            "window": {"start": str(weekly.index[0].date()) if len(weekly) else None,
                       "end": str(weekly.index[-1].date()) if len(weekly) else None, "weeks": len(weekly)},
            "tickers": [{k: r[k] for k in ("ticker", "name", "lists", "sector", "country", "currency")}
                        | {"vol_eur": round(vol[r["ticker"]], 4) if r["ticker"] in vol else None} for r in rows],
            "risk_tickers": list(cov.index),
            "cov": np.round(cov.to_numpy(), 8).tolist(),
            "corr": np.round(portfolio.correlation(cov).to_numpy(), 4).tolist(),
            "no_risk_data": [{"ticker": t, "reason": why} for t, why in sorted(no_risk.items())],
        },
        "meta": head | {
            "built_at": built_at or datetime.now(timezone.utc).isoformat(timespec="seconds"), "demo": is_demo,
            "tickers": len(inp["meta"]), "usable": len(rows),
            "lists": [{"key": k, "name": v["name"], "count": len(v["tickers"]),
                       "usable": sum(t in live for t in v["tickers"])} for k, v in inp["cfg"].items()],
            "failures": failures, "notes": NOTES,
        },
    }
    return {k: _plain(v) for k, v in out.items()}


def _plain(x):
    """JSON-ready copy: numpy numbers become Python numbers, NaN and infinity become None."""
    if isinstance(x, dict):
        return {k: _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return float(x) if math.isfinite(x) else None
    return x


def _dump(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def validate(payloads: dict[str, dict]) -> None:
    for stem in FILES:
        schema = json.loads((SCHEMAS / f"{stem}.schema.json").read_text(encoding="utf-8"))
        errors = sorted(Draft202012Validator(schema).iter_errors(payloads[stem]), key=lambda e: list(e.path))
        if errors:
            e = errors[0]
            raise ValueError(f"{stem}.json does not match its schema at {'/'.join(map(str, e.path)) or '(root)'}: {e.message}")


def write(payloads: dict[str, dict], out_dir: Path) -> None:
    """Write every file to a temp name first, then rename them into place, so an error while serialising or writing
    leaves the previous files untouched."""
    out_dir.mkdir(parents=True, exist_ok=True)
    tmps = []
    try:
        for stem in FILES:
            tmp = out_dir / f"{stem}.json.{os.getpid()}.tmp"
            tmps.append((tmp, out_dir / f"{stem}.json"))
            tmp.write_text(_dump(payloads[stem]), encoding="utf-8", newline="\n")
        for tmp, final in tmps:
            os.replace(tmp, final)
    finally:
        for tmp, _ in tmps:
            tmp.unlink(missing_ok=True)


def build(out_dir: Path | str = DEFAULT_OUT, asof: date | None = None, *, is_demo: bool = False,
          inputs: dict | None = None, settings: Settings | None = None) -> int:
    settings = settings or load_settings()
    inp = inputs or (demo.inputs() if is_demo else live_inputs())
    payloads = compute(inp, settings, asof, built_at="2026-11-11T00:00:00+00:00" if is_demo else None, is_demo=is_demo)
    m = payloads["meta"]
    if m["usable"] < settings.data.min_screened_fraction * m["tickers"]:
        print(f"only {m['usable']} of {m['tickers']} tickers had usable data: previous files kept")
        return 2
    validate(payloads)
    write(payloads, Path(out_dir))
    print(f"data as of {m['asof']}: {m['usable']} of {m['tickers']} tickers, {len(m['failures'])} without data -> {out_dir}")
    return 0
