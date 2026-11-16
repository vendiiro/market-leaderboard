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
import tomllib
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from jsonschema import Draft202012Validator

from . import demo, history, holdings, leaderboard, movers, portfolio, research, watchlists
from .config import ROOT, Settings, load_settings
from .metrics import MIN_BARS
from .returns import PERIODS

SCHEMA_VERSION = 3
FILES = ("leaderboard", "movers", "portfolio", "research", "holdings", "meta")        # meta last: it is the file the page reads first
SCHEMAS = ROOT / "schemas"
DEFAULT_OUT = ROOT / "web" / "public" / "data"
NOTES = [
    "Educational research tool: screen results and exposure views, not investment advice.",
    "Prices are daily adjusted closes from Yahoo Finance, pulled after the close; fundamentals are current values, not point-in-time.",
    "Returns and 1-year volatility are in each stock's own currency.",
    "Mix risk numbers use weekly returns in EUR over the last 104 complete weeks; they are estimates, not forecasts.",
    "The dip flag and the quality score are untested screen rules.",
    "Candidates are picked by three published measures (value, business quality, long-term trend); steadiness is shown but not used. They are not shown to work on these companies; see the evidence note on the Candidates page.",
    "Headlines are Yahoo's text, shown as received.",
    "Portfolio values use Yahoo closes converted to EUR and can differ slightly from the broker's report; risk figures are estimates.",
]


def load_history(path: Path | str) -> tuple[list[dict] | None, str | None]:
    """(points, None) or (None, note): a bad history file never fails the build."""
    try:
        return history.read_nordnet_csv(path), None
    except Exception as e:                                       # noqa: BLE001 - whatever is wrong with the file, the build goes on
        note = str(e) if isinstance(e, ValueError) else f"Nordnet history file: could not be read ({type(e).__name__})"
        print(f"warning: {note}")
        return None, note


def load_holdings(path: Path | str) -> tuple[holdings.Holdings | None, str | None]:
    """(holdings, None); (None, None) when there is no file; (None, note) when the file cannot be read, so a typo in the
    private file does not stop the nightly build."""
    p = Path(path)
    if not p.exists():
        return None, None
    try:
        return holdings.read_holdings(p), None
    except (ValueError, tomllib.TOMLDecodeError) as e:
        note = f"config/portfolio.toml could not be read: {e}"
        print(f"warning: {note}")
        return None, note


def live_inputs(root: Path = ROOT) -> dict:
    """Fetch everything the build needs from Yahoo. Only tickers that passed verification are used."""
    from .data import fetch_fundamentals, fetch_prices, pull_prices
    from .fetch import fetch_headlines, fetch_indices, fetch_raw_closes, fetch_statements
    from .fx import fetch_fx_to_usd, fx_history_eur

    from .exchanges import exchange_for
    from .verify import yahoo_info

    cfg = watchlists.read(root / "config" / "watchlists.toml")
    stock_cfg, etf_cfg = watchlists.split_by_kind(cfg)             # ETF lists are candidates for the portfolio page only
    lists = {k: list(v["tickers"]) for k, v in stock_cfg.items()}
    member = watchlists.membership(lists)
    names = {t: n for v in stock_cfg.values() for t, n in v["tickers"].items()}
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

    # The owner's holdings and the ETF candidates that are not on a share list ("extras"): priced like any ticker, kept
    # out of the share views, added to the covariance matrix. An unverified ETF is skipped with a reason.
    owned, holdings_note = load_holdings(root / "config" / "portfolio.toml")
    extra: dict[str, dict] = {}
    for key, v in etf_cfg.items():
        for t, name in v["tickers"].items():
            row = verified.get(t)
            if not row or row["status"] != "ok":
                reasons[t] = "not verified against Yahoo (run scripts/verify_watchlists.py)"
                continue
            extra.setdefault(t, {"name": name, "lists": [], "currency": row.get("currency") or None, "sector": None, "country": None})["lists"].append(key)
    for x in (owned.holdings if owned else []):
        if x.ticker and x.ticker not in meta and x.ticker not in extra:
            info = yahoo_info(x.ticker) or {}
            ex = exchange_for(x.ticker)
            extra[x.ticker] = {"name": x.name, "lists": [], "currency": info.get("currency") or (ex.currency if ex else None),
                               "sector": info.get("sector") or None, "country": info.get("country") or None}
    priced = ok + [t for t in extra if t not in ok]
    prices, _ = pull_prices(priced, lambda batch: fetch_prices(batch, period="3y"), reasons=reasons)
    fund = fetch_fundamentals(ok, root / "data" / "fundamentals.json")
    ccys = ({meta[t]["currency"] for t in ok} | {m["currency"] for m in extra.values()}
            | {f.get("financialCurrency") for f in fund.values()}) - {None}
    start = str(date.today() - timedelta(days=6 * 366))      # year-end P/Es need rates back to the oldest statement

    points, history_note = None, holdings_note
    if owned and owned.history_csv:
        points, history_note = load_history(owned.history_csv)
    elif owned:
        history_note = "history_csv is not set in config/portfolio.toml"
    return {"cfg": cfg, "meta": meta, "prices": {t: prices[t] for t in priced if t in prices}, "fund": fund,
            "rates_usd": fetch_fx_to_usd(ccys | {"EUR"}), "fx": fx_history_eur(ccys, start), "reasons": reasons,
            "statements": fetch_statements(ok, root / "data" / "statements.json"), "raw_closes": fetch_raw_closes(ok),
            "indices": fetch_indices(["^GSPC", "^STOXX"]), "headlines": fetch_headlines,
            "extra": extra, "holdings": owned, "history": points, "history_note": history_note}


def compute(inp: dict, settings: Settings, asof: date | None = None, built_at: str | None = None,
            is_demo: bool = False) -> dict[str, dict]:
    """{file stem: payload} for the five output files."""
    prices = inp["prices"]
    last_bars = [p[0].dropna().index[-1].date() for p in prices.values() if len(p[0].dropna())]
    if not last_bars:
        raise RuntimeError("no price data at all")
    asof = asof or max(last_bars)
    stock_cfg, etf_cfg = watchlists.split_by_kind(inp["cfg"])      # ETF lists never reach the share views
    rows, failures = leaderboard.rows(prices, inp["fund"], inp["meta"], settings, asof, inp["rates_usd"])
    for f in failures:
        f["reason"] = inp["reasons"].get(f["ticker"], f["reason"])
    head = {"schema_version": SCHEMA_VERSION, "asof": str(asof)}

    live = {r["ticker"] for r in rows}
    owned = inp.get("holdings")
    held = {x.ticker for x in owned.holdings if x.ticker} if owned else set()
    for x in (owned.holdings if owned else []):               # a holding with no usable prices is reported on the data page
        if x.ticker and x.ticker not in inp["meta"] and not (x.ticker in prices and len(prices[x.ticker][0].dropna()) >= MIN_BARS):
            failures.append({"ticker": x.ticker, "name": x.name, "lists": ["holdings"],
                             "reason": inp["reasons"].get(x.ticker, "no price data tonight")})
    # Holdings and ETF candidates that are not on a watchlist ("extras") join the covariance matrix when they have prices.
    extra = {t: m for t, m in (inp.get("extra") or {}).items()
             if t not in inp["meta"] and t in prices and len(prices[t][0].dropna()) >= MIN_BARS}
    currency = {t: inp["meta"][t]["currency"] for t in live} | {t: m["currency"] for t, m in extra.items()}
    weekly, no_risk = portfolio.weekly_eur_returns({t: prices[t][0] for t in sorted(live | set(extra))}, currency,
                                                   inp["fx"], asof)
    cov = portfolio.covariance(weekly)
    vol = {t: math.sqrt(cov.loc[t, t]) for t in cov.index}
    mv = movers.movers(rows)
    evidence_file = ROOT / "config" / "measure_evidence.json"
    evidence = json.loads(evidence_file.read_text(encoding="utf-8")) if evidence_file.exists() else {}

    def study(headlines: dict) -> dict:
        return research.build(rows, inp["fund"], inp.get("statements", {}), prices, inp.get("raw_closes", {}), inp["fx"],
                              inp.get("indices", {}), headlines, evidence, asof, settings.dip.drop_1d)

    news = inp.get("headlines", {})
    if callable(news):       # live: fetch only for tonight's candidates and movers (about 30 calls)
        wanted = study({})["shortlist"] + [m["ticker"] for k in ("gainers", "losers", "alerts") for m in mv[k]]
        news = news(list(dict.fromkeys(wanted)), asof)
    sector = {r["ticker"]: r["sector"] for r in rows} | {t: m.get("sector") for t, m in (inp.get("extra") or {}).items()}
    held_currency = currency | {t: m.get("currency") for t, m in (inp.get("extra") or {}).items()}
    positions = (holdings.position_rows(owned, {t: p[0] for t, p in prices.items()}, held_currency, sector, inp["fx"],
                                        set(cov.index)) if owned else [])
    pts = inp.get("history")
    out = {
        "leaderboard": head | {"periods": list(PERIODS), "lists": leaderboard.lists(rows, stock_cfg)},
        "movers": head | mv,
        "research": head | study(news),
        "portfolio": head | {
            "window": {"start": str(weekly.index[0].date()) if len(weekly) else None,
                       "end": str(weekly.index[-1].date()) if len(weekly) else None, "weeks": len(weekly)},
            "tickers": [{k: r[k] for k in ("ticker", "name", "lists", "sector", "country", "currency")}
                        | {"vol_eur": round(vol[r["ticker"]], 4) if r["ticker"] in vol else None} for r in rows]
                       + [{"ticker": t, "name": m["name"], "lists": list(m["lists"]) + (["holdings"] if t in held else []),
                           "sector": m.get("sector"), "country": m.get("country"), "currency": m.get("currency"),
                           "vol_eur": round(vol[t], 4) if t in vol else None} for t, m in sorted(extra.items())],
            "risk_tickers": list(cov.index),
            "cov": np.round(cov.to_numpy(), 8).tolist(),
            "corr": np.round(portfolio.correlation(cov).to_numpy(), 4).tolist(),
            "no_risk_data": [{"ticker": t, "reason": why} for t, why in sorted(no_risk.items())],
        },
        "holdings": head | {
            "label": owned.label if owned else "Portfolio", "positions": positions, "totals": holdings.totals(positions),
            "history": {"points": pts, "summary": history.summarise(pts, str(asof))} if pts else None,
            "history_note": None if pts else inp.get("history_note"),
            "etfs": holdings.etf_rows(etf_cfg, prices, {t: m.get("currency") for t, m in (inp.get("extra") or {}).items()}),
        },
        "meta": head | {
            "built_at": built_at or datetime.now(timezone.utc).isoformat(timespec="seconds"), "demo": is_demo,
            "tickers": len(inp["meta"]), "usable": len(rows),
            "lists": [{"key": k, "name": v["name"], "count": len(v["tickers"]),
                       "usable": sum(t in live for t in v["tickers"])} for k, v in stock_cfg.items()],
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
