# Copied from dip-dashboard src/dipdash/fx.py at commit f14d55c (imports renamed to engine).
"""Currency conversion to USD for size thresholds. Rates come from Yahoo FX pairs (e.g. SEKUSD=X)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Iterable

if TYPE_CHECKING:
    import pandas as pd

PENCE = {"GBp", "GBX"}


def usd_value(amount, ccy: str | None, rates: dict[str, float]) -> float | None:
    """Convert amount in ccy to USD; None if the amount, currency or rate is unusable."""
    try:
        x = float(amount)
    except (TypeError, ValueError):
        return None
    if not ccy or x != x:
        return None
    if ccy == "USD":
        return x
    if ccy in PENCE:
        r = rates.get("GBP")
        return x / 100 * r if r else None
    r = rates.get(ccy)
    return x * r if r else None


def fetch_fx_to_usd(ccys: Iterable[str | None], fetch_last: Callable[[str], float | None] | None = None) -> dict[str, float]:
    """USD per 1 unit of each currency. Currencies whose rate cannot be fetched are omitted."""
    want = {("GBP" if c in PENCE else c) for c in ccys if c and c != "USD"}
    fetch_last = fetch_last or _yahoo_last_close
    out: dict[str, float] = {}
    for c in sorted(want):
        r = fetch_last(f"{c}USD=X")
        if r and r > 0:
            out[c] = float(r)
    return out


def _yahoo_last_close(symbol: str) -> float | None:
    import yfinance as yf

    try:
        h = yf.Ticker(symbol).history(period="5d")
        return float(h["Close"].dropna().iloc[-1])
    except Exception:
        return None


# ---- added in market-leaderboard (not in the dip-dashboard source) ----------------------------------------------

def cap_currency(ccy: str | None) -> str | None:
    """Currency of Yahoo's `marketCap` for a quote currency: pounds for a pence-quoted line (checked live 2026-11-11
    for BA.L, SHEL.L, BP.L: marketCap = price in pence x shares / 100; see docs/decisions.md)."""
    return "GBP" if ccy in PENCE else ccy


def eur_value(amount, ccy: str | None, rates_usd: dict[str, float]) -> float | None:
    """Convert amount in ccy to EUR through USD (`rates_usd` = USD per 1 unit, as from fetch_fx_to_usd).
    None if the amount, currency or a needed rate is unusable. An EUR amount needs no rate."""
    if ccy == "EUR":
        usd, eur = usd_value(amount, "USD", {}), 1.0      # reuse the amount checks only
    else:
        usd, eur = usd_value(amount, ccy, rates_usd), rates_usd.get("EUR")
    return usd / eur if usd is not None and eur else None


def fx_history_eur(ccys: Iterable[str | None], start: str,
                   fetch: Callable[[str, str], "pd.Series | None"] | None = None) -> dict:
    """Daily EUR value of 1 unit of each currency since `start` ({ccy: Series}), from Yahoo pairs such as USDEUR=X.
    Pence currencies are returned under GBP (divide a pence price by 100 at use). EUR itself and pairs that
    cannot be fetched are omitted."""
    fetch = fetch or _yahoo_history
    out = {}
    for c in sorted({("GBP" if c in PENCE else c) for c in ccys if c and c != "EUR"}):
        s = fetch(f"{c}EUR=X", start)
        if s is not None and len(s):
            out[c] = s
    return out


def _yahoo_history(symbol: str, start: str):
    import yfinance as yf

    try:
        return yf.Ticker(symbol).history(start=start)["Close"].dropna()
    except Exception:
        return None
