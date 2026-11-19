"""Leaderboard rows (one per ticker), ranks per list and period, and list summaries. Pure functions, no network.

The dip flag and the quality score reuse the dip-dashboard rules unchanged. They are untested screen rules
(that backtest did not support them) and every output that carries them says so."""
from __future__ import annotations

from datetime import date
from statistics import fmean

from .config import Settings
from .fx import cap_currency
from .metrics import compute_metrics
from .quality import quality_detail
from .returns import PERIODS, rank_table, windows
from .screen import dip_reasons, is_stale, trading_days_old

UNTESTED = "untested screen rule"
SPARK_BARS = 60


def rows(prices: dict, fund: dict, meta: dict[str, dict], settings: Settings, asof: date,
         rates_usd: dict[str, float] | None = None) -> tuple[list[dict], list[dict]]:
    """(rows, failures). One row per ticker in `meta` that has at least 60 closes; the rest are failures with a reason.

    prices: {ticker: (close, volume)}; fund: {ticker: Yahoo fundamentals}; meta: {ticker: {name, lists, currency,
    sector, country}}; rates_usd: USD per unit of each currency (for the size check of the quality score).
    `_prev` holds the same returns one bar earlier (for the rank change) and is not part of the output files."""
    out, failures = [], []
    for t, m in sorted(meta.items()):
        close = prices[t][0].dropna() if t in prices else None
        metrics = compute_metrics(close, prices[t][1]) if close is not None else None
        if metrics is None:
            failures.append({"ticker": t, "name": m["name"], "lists": m["lists"],
                             "reason": "no price data tonight" if close is None or not len(close) else "fewer than 60 daily bars"})
            continue
        last_bar = close.index[-1].date()
        stale = is_stale(last_bar, asof, settings.data.max_stale_trading_days)
        f = dict(fund.get(t) or {})
        f["currency"] = cap_currency(f.get("currency") or m.get("currency"))   # Yahoo market cap of a pence line is in pounds
        q = quality_detail(f, settings.quality, rates_usd, m.get("sector"), settings.quality.must_pass,
                           settings.quality.distorted_roe_above)
        reasons = [] if stale else dip_reasons(metrics, settings.dip)
        spark = close.iloc[-SPARK_BARS:]
        out.append({
            "ticker": t, "name": m["name"], "lists": m["lists"], "currency": m.get("currency"),
            "sector": m.get("sector") or None, "country": m.get("country") or None,
            "last_bar": str(last_bar), "stale": stale,
            "stale_reason": f"last bar is {trading_days_old(last_bar, asof)} weekdays old" if stale else None,
            "price": metrics["price"], **windows(close), "dd52": metrics["dd52"],
            "q_score": q.score, "q_passed": q.passed, "q_scored": q.scored,
            "pe": _positive(f.get("trailingPE")), "fwd_pe": _positive(f.get("forwardPE")),
            "dip": bool(reasons), "dip_reasons": reasons,
            "spark": [round(float(x) / float(spark.iloc[0]) * 100, 2) for x in spark],
            "_prev": windows(close.iloc[:-1]),
        })
    return out, failures


def _positive(v) -> float | None:
    """A P/E as Yahoo gives it, or None when missing or not above zero (a loss has no P/E)."""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return round(x, 2) if x == x and 0 < x < float("inf") else None


def ranked(all_rows: list[dict], members: list[str]) -> dict[str, dict]:
    """{ticker: {period: {rank, rank_prev, rank_delta}}} within one list. Stale rows and missing values get no rank;
    rank_delta = rank_prev - rank (positive = moved up) or None when either rank is missing."""
    live = [r for r in all_rows if r["ticker"] in members and not r["stale"]]
    out: dict[str, dict] = {r["ticker"]: {} for r in live}
    for p in PERIODS:
        now = rank_table({r["ticker"]: r[f"ret_{p}"] for r in live})
        prev = rank_table({r["ticker"]: r["_prev"][f"ret_{p}"] for r in live})
        for t in out:
            a, b = now.get(t), prev.get(t)
            out[t][p] = {"rank": a, "rank_prev": b, "rank_delta": b - a if a and b else None}
    return out


def summary(all_rows: list[dict], members: list[str]) -> dict:
    """Equal-weight mean return per period over the list's non-stale rows (each in its own currency), the top and
    bottom ticker per period, and counts."""
    mine = [r for r in all_rows if r["ticker"] in members]
    live = [r for r in mine if not r["stale"]]
    periods = {}
    for p in PERIODS:
        vals = {r["ticker"]: r[f"ret_{p}"] for r in live if r[f"ret_{p}"] is not None}
        order = list(rank_table(vals))
        periods[p] = {"mean": round(fmean(vals.values()), 4) if vals else None, "n": len(vals),
                      "top": order[0] if order else None, "bottom": order[-1] if order else None}
    return {"periods": periods, "count": len(mine), "stale": len(mine) - len(live), "flags": sum(r["dip"] for r in live)}


def lists(all_rows: list[dict], cfg: dict[str, dict]) -> list[dict]:
    """The `lists` array of leaderboard.json: for each watchlist its name, summary and rows (with `rank`)."""
    out = []
    for key, v in cfg.items():
        members = list(v["tickers"])
        ranks = ranked(all_rows, members)
        out.append({"key": key, "name": v["name"], "summary": summary(all_rows, members),
                    "rows": [{k: x for k, x in r.items() if k != "_prev"} | {"rank": ranks.get(r["ticker"])}
                             for r in all_rows if r["ticker"] in members]})
    return out
