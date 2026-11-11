# Adapted from dip-dashboard scripts/verify_universe.py at commit f14d55c: the pure row check and the two Yahoo
# calls. Changed here: expected currency comes from the exchange registry, the size check is optional (`under_cap`),
# a minimum bar count is checked (`few_bars`), and the duplicate-name check and the CSV driver are not copied.
"""Check one watchlist ticker against what Yahoo returns. `classify_row` is pure; the Yahoo calls are at the bottom.

Statuses (several are joined by ';'): ok, no_bars, few_bars, stale, not_equity, name_mismatch, currency_mismatch,
under_cap, fetch_error. Market cap is today's value (not point-in-time); educational screen only.
"""
from __future__ import annotations

import difflib
import re
import time
from datetime import date

from .exchanges import exchange_for
from .fx import usd_value
from .screen import trading_days_old

COLUMNS = ["ticker", "csv_name", "yahoo_long_name", "name_score", "quote_type", "exchange", "currency",
           "expected_currency", "first_bar", "last_bar", "bar_count", "market_cap_usd", "status", "detail"]
STATUSES = ["ok", "no_bars", "few_bars", "stale", "not_equity", "name_mismatch", "currency_mismatch", "under_cap",
            "fetch_error"]

_LEGAL = {"inc", "incorporated", "corp", "corporation", "co", "company", "plc", "ag", "se", "sa", "nv", "ltd",
          "limited", "llc", "lp", "group", "holding", "holdings", "spa", "ab", "asa", "oyj", "as", "the", "de"}


def normalize_name(name: str) -> str:
    """Lowercase, drop punctuation and legal suffixes (Inc, plc, AG, ...). Used for the name check."""
    words = re.sub(r"[^a-z0-9 ]", "", re.sub(r"[-/]", " ", (name or "").lower().replace("&", " and "))).split()
    kept = [w for w in words if w not in _LEGAL]
    return " ".join(kept or words)


def name_score(csv_name: str, yahoo_name: str | None) -> float:
    """0..1 similarity between our short name and Yahoo's long name (1.0 if one contains the other)."""
    a, b = normalize_name(csv_name), normalize_name(yahoo_name or "")
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 1.0
    return round(difflib.SequenceMatcher(None, a, b).ratio(), 3)


def classify_row(ticker: str, csv_name: str, info: dict | None, bars: dict | None, today: date, *,
                 rates: dict[str, float], min_cap_usd: float | None = None, min_bars: int = 250,
                 max_stale: int = 4, name_threshold: float = 0.6) -> dict:
    """Pure: build one output row from fetched info and bar summary.

    info: Yahoo info dict (longName, quoteType, exchange, currency, marketCap) or None if the fetch failed.
    bars: {"first": date, "last": date, "count": int} or None/empty count when no bars came back.
    """
    ex = exchange_for(ticker)
    expected = ex.currency if ex else None
    row = {c: "" for c in COLUMNS}
    row.update(ticker=ticker, csv_name=csv_name, expected_currency=expected or "")
    flags: list[str] = []
    notes: list[str] = []

    if info is None and bars is None:
        row.update(status="fetch_error", detail="no data returned (network or Yahoo error)")
        return row

    if info is None:
        flags.append("fetch_error")
        notes.append("info call failed")
    else:
        row.update(yahoo_long_name=info.get("longName") or info.get("shortName") or "",
                   quote_type=info.get("quoteType") or "", exchange=info.get("exchange") or "",
                   currency=info.get("currency") or "")
        if row["quote_type"] != "EQUITY":
            flags.append("not_equity")
            notes.append(f"quoteType={row['quote_type'] or 'missing'}")
        if row["yahoo_long_name"]:
            sc = name_score(csv_name, row["yahoo_long_name"])
            row["name_score"] = sc
            if sc < name_threshold:
                flags.append("name_mismatch")
                notes.append(f"'{csv_name}' vs '{row['yahoo_long_name']}'")
        if ex is None:
            flags.append("currency_mismatch")
            notes.append("exchange suffix not in the registry")
        elif row["currency"] and expected and row["currency"] != expected:
            flags.append("currency_mismatch")
            notes.append(f"{row['currency']} != {expected}")
        cap = usd_value(info.get("marketCap"), row["currency"] or expected, rates)
        if cap is None:
            notes.append("market cap unavailable")
        else:
            row["market_cap_usd"] = round(cap)
            if min_cap_usd is not None and cap < min_cap_usd:
                flags.append("under_cap")
                notes.append(f"market cap {cap / 1e9:.1f}B USD")

    if not bars or not bars.get("count"):
        flags.append("no_bars")
    else:
        row.update(first_bar=bars["first"], last_bar=bars["last"], bar_count=bars["count"])
        if bars["count"] < min_bars:
            flags.append("few_bars")
            notes.append(f"{bars['count']} daily bars, need {min_bars}")
        age = trading_days_old(bars["last"], today)
        if age > max_stale:
            flags.append("stale")
            notes.append(f"last bar {age} trading days old")

    row["status"] = ";".join(dict.fromkeys(flags)) or "ok"
    row["detail"] = "; ".join(notes)
    return row


# ---- network layer (not exercised offline) ------------------------------------------------------------------

def yahoo_bars(tickers: list[str]) -> dict[str, dict]:
    """One batched yf.download; returns {ticker: {first, last, count}} (missing tickers are absent)."""
    import yfinance as yf

    df = yf.download(tickers, period="5y", interval="1d", auto_adjust=True, group_by="ticker",
                     progress=False, threads=True)
    out: dict[str, dict] = {}
    for t in tickers:
        try:
            close = (df[t]["Close"] if hasattr(df.columns, "levels") else df["Close"]).dropna()
        except (KeyError, TypeError):
            continue
        if len(close):
            out[t] = {"first": close.index[0].date(), "last": close.index[-1].date(), "count": int(len(close))}
    return out


def yahoo_info(ticker: str, retries: int = 3, sleep: float = 2.0) -> dict | None:
    import yfinance as yf

    for i in range(retries):
        try:
            info = yf.Ticker(ticker).info
            if info and (info.get("quoteType") or info.get("longName")):
                return info
        except Exception:
            pass
        time.sleep(sleep * (2 ** i))
    return None
