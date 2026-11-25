"""Test of the two price-based measures (long-term trend, steadiness) on the universe's own price history.

Pure functions; scripts/backtest_measures.py does the fetching and writes the result. The design is fixed in
docs/backtests/2026-11-12-measures-spec.json before any result is seen: one run per measure, no tuning.
The universe is today's watchlists, so companies that failed or were delisted are missing (survivorship): the
result flatters the past and can only be read as weak evidence either way."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .research import BIG_MOVE, CALM_INDEX, STEADY_BARS

HORIZON, MIN_NAMES = 252, 12


def monthly_panels(close: pd.Series, index_close: pd.Series) -> pd.DataFrame:
    """Per month-end for one share: trend, steady (higher = steadier) and the return over the next 252 bars.
    A measure is missing until the share has 756 bars of history; the outcome is missing in the last 252 bars."""
    c = close.dropna()
    c.index = pd.DatetimeIndex(c.index).tz_localize(None).normalize()
    r = c.pct_change()
    idx = index_close.dropna().pct_change()
    idx.index = pd.DatetimeIndex(idx.index).tz_localize(None).normalize()
    big = ((r.abs() >= BIG_MOVE) & (idx.reindex(r.index).abs() < CALM_INDEX)).astype(float)
    enough = pd.Series(np.arange(len(c)) >= STEADY_BARS, index=c.index)
    daily = pd.DataFrame({
        "trend": (c.shift(21) / c.shift(252) - 1).where(enough),
        "steady": (-big.rolling(STEADY_BARS).sum()).where(enough),
        "outcome": c.shift(-HORIZON) / c - 1,
    })
    return daily.groupby(daily.index.to_period("M")).last()


def spreads(measure: pd.DataFrame, outcome: pd.DataFrame) -> pd.Series:
    """Per formation month: mean outcome of the top third by the measure minus the bottom third.
    Months with fewer than 12 companies that have both a measure and an outcome are left out."""
    out = {}
    for month in measure.index:
        m, o = measure.loc[month], outcome.loc[month]
        ok = m.notna() & o.notna()
        if ok.sum() < MIN_NAMES:
            continue
        order = m[ok].sort_values(kind="mergesort")
        k = len(order) // 3
        out[month] = float(o[order.index[-k:]].mean() - o[order.index[:k]].mean())
    return pd.Series(out, dtype=float)


def block_interval(x: pd.Series, block: int = 12, draws: int = 5000, level: float = 0.90, seed: int = 20261112) -> tuple[float, float]:
    """Interval for the mean of a monthly series from a moving-block bootstrap (blocks of `block` months), because
    12-month outcomes of neighbouring months overlap and are far from independent."""
    v = x.to_numpy()
    n = len(v)
    if n < 2 * block:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n - block + 1, size=(draws, -(-n // block)))
    means = np.array([np.concatenate([v[s:s + block] for s in row])[:n].mean() for row in starts])
    lo, hi = np.quantile(means, [(1 - level) / 2, (1 + level) / 2])
    return float(lo), float(hi)


def verdict(x: pd.Series) -> dict:
    """{months, first, last, mean, lo, hi, status}. 'supported' only when the whole 90 % interval is above zero."""
    lo, hi = block_interval(x)
    return {"months": int(len(x)), "first": str(x.index[0]) if len(x) else None, "last": str(x.index[-1]) if len(x) else None,
            "mean": float(x.mean()) if len(x) else None, "lo": lo, "hi": hi,
            "status": "supported" if lo == lo and lo > 0 else "not supported"}
