"""Return windows, 1-year volatility and ranks from daily adjusted closes. Pure functions, no network.

Definitions are in docs/spec.md ("Definitions"). Missing history gives None, never 0."""
from __future__ import annotations

import math

import pandas as pd

from .metrics import clean

PERIODS = {"1d": 1, "1w": 5, "1m": 21, "ytd": None, "1y": 252}     # bars back; ytd = last bar of the previous year
MIN_VOL_RETURNS = 126


def windows(close: pd.Series) -> dict:
    """{ret_1d, ret_1w, ret_1m, ret_ytd, ret_1y, vol_1y} for one stock, in its own currency."""
    c = close.dropna()
    out = {f"ret_{p}": None for p in PERIODS} | {"vol_1y": None}
    if len(c) < 2:
        return out
    last = float(c.iloc[-1])
    for p, n in PERIODS.items():
        if n is None:
            before = c[c.index.year < c.index[-1].year]
            base = float(before.iloc[-1]) if len(before) else None
        else:
            base = float(c.iloc[-1 - n]) if len(c) > n else None
        out[f"ret_{p}"] = clean(last / base - 1) if base else None
    daily = c.pct_change().dropna().iloc[-252:]
    if len(daily) >= MIN_VOL_RETURNS:
        out["vol_1y"] = clean(float(daily.std()) * math.sqrt(252))
    return out


def rank_table(values: dict[str, float | None]) -> dict[str, int]:
    """Rank 1 = highest value; ties broken by ticker; tickers without a value are left out."""
    ordered = sorted((t for t, v in values.items() if v is not None), key=lambda t: (-values[t], t))
    return {t: i for i, t in enumerate(ordered, start=1)}
