"""Watchlists (config/watchlists.toml) and the rule that builds the Finnish smaller-companies list. No network.

A ticker may be in several lists: it is shown on each list's page, but fetched and counted once (`all_tickers`)."""
from __future__ import annotations

import tomllib
from pathlib import Path

from .config import CONFIG_DIR
from .fx import cap_currency, eur_value
from .verify import normalize_name

LIST_KEYS = ("us_big_tech", "eu_defence", "eu_energy", "nordic_energy", "fi_small")


def read(path: Path | str | None = None) -> dict[str, dict]:
    """{list key: {"name": display name, "tickers": {ticker: company name}}} in LIST_KEYS order.
    The company name is what verification compares with Yahoo's name, so a wrong ticker is caught."""
    p = Path(path) if path else CONFIG_DIR / "watchlists.toml"
    raw = tomllib.loads(p.read_text(encoding="utf-8"))
    if unknown := set(raw) - set(LIST_KEYS):
        raise ValueError(f"{p.name}: unknown list(s) {sorted(unknown)}; expected {list(LIST_KEYS)}")
    if missing := set(LIST_KEYS) - set(raw):
        raise ValueError(f"{p.name}: missing list(s) {sorted(missing)}")
    for k in LIST_KEYS:
        if not raw[k].get("name") or not isinstance(raw[k].get("tickers", {}), dict):
            raise ValueError(f"{p.name} [{k}]: needs a name and a [{k}.tickers] table")
        for t, company in raw[k].get("tickers", {}).items():
            if not isinstance(company, str) or not company.strip():
                raise ValueError(f"{p.name} [{k}]: {t} needs a company name")
    return {k: {"name": raw[k]["name"], "tickers": dict(raw[k].get("tickers", {}))} for k in LIST_KEYS}


def load_watchlists(path: Path | str | None = None) -> dict[str, list[str]]:
    return {k: list(v["tickers"]) for k, v in read(path).items()}


def all_tickers(lists: dict[str, list[str]]) -> list[str]:
    return sorted({t for tickers in lists.values() for t in tickers})


def membership(lists: dict[str, list[str]]) -> dict[str, list[str]]:
    """{ticker: [list keys it belongs to]}."""
    out: dict[str, list[str]] = {}
    for k, tickers in lists.items():
        for t in tickers:
            out.setdefault(t, []).append(k)
    return out


def fi_smallcap_rows(candidates: list[str], info: dict[str, dict], bars: dict, rates: dict[str, float],
                     lo: float = 0.3e9, hi: float = 5.0e9, min_traded: float = 0.5e6, min_bars: int = 250) -> list[dict]:
    """One row per candidate: ticker, company, cap_eur, traded_eur (median close x volume, last 60 bars), keep, reason.

    Kept: market cap within [lo, hi] EUR, traded value at least min_traded, at least min_bars daily closes (the
    same history rule as verification), and for a company with several share
    classes only the most traded class. `bars` is {ticker: (close, volume)}; `rates` is USD per unit (fx)."""
    rows = []
    for t in candidates:
        i, b = info.get(t), bars.get(t)
        row = {"ticker": t, "company": (i or {}).get("longName") or "", "cap_eur": None, "traded_eur": None,
               "keep": False, "reason": ""}
        rows.append(row)
        if not i or not b or b[1] is None:
            row["reason"] = "no data from Yahoo (info, prices or volume)"
            continue
        ccy = i.get("currency")
        cap = eur_value(i.get("marketCap"), cap_currency(ccy), rates)
        traded = eur_value(float((b[0] * b[1]).dropna().iloc[-60:].median()), ccy, rates)
        row.update(cap_eur=cap, traded_eur=traded)
        n_bars = int(b[0].notna().sum())
        if cap is None:
            row["reason"] = "market cap unavailable"
        elif n_bars < min_bars:
            row["reason"] = f"only {n_bars} daily bars, need {min_bars}"
        elif cap < lo:
            row["reason"] = f"market cap {cap / 1e9:.2f}B EUR is below {lo / 1e9:g}B"
        elif cap > hi:
            row["reason"] = f"market cap {cap / 1e9:.2f}B EUR is above {hi / 1e9:g}B"
        elif traded is None or traded < min_traded:
            row["reason"] = f"median traded value {(traded or 0) / 1e6:.2f}M EUR a day is under {min_traded / 1e6:g}M"
        else:
            row["keep"] = True
    best: dict[str, dict] = {}
    for row in (r for r in rows if r["keep"]):
        key = normalize_name(row["company"]) or row["ticker"]
        if key not in best or row["traded_eur"] > best[key]["traded_eur"]:
            best[key] = row
    for row in (r for r in rows if r["keep"]):
        winner = best[normalize_name(row["company"]) or row["ticker"]]
        if winner is not row:
            row.update(keep=False, reason=f"another share class of the same company is traded more ({winner['ticker']})")
    return rows


def build_fi_smallcaps(candidates: list[str], info: dict[str, dict], bars: dict, rates: dict[str, float],
                       lo: float = 0.3e9, hi: float = 5.0e9, min_traded: float = 0.5e6, min_bars: int = 250) -> list[str]:
    return sorted(r["ticker"] for r in fi_smallcap_rows(candidates, info, bars, rates, lo, hi, min_traded, min_bars) if r["keep"])
