"""Mix maths: weekly EUR returns, covariance, and the reference versions of the four formulas the page computes.

Why weekly and EUR: European markets close before the US session, so same-day daily returns understate correlation
between regions; a week makes that timing gap small. The owner's base currency is EUR, so currency moves are part
of the risk. See docs/spec.md ("Mix maths"). Estimates from two years of data, not forecasts. No network."""
from __future__ import annotations

import math
from datetime import date

import numpy as np
import pandas as pd

from .fx import PENCE

WEEKS = 104
FX_GAP_DAYS = 3


def eur_prices(close: pd.Series, ccy: str | None, fx: dict[str, pd.Series]) -> pd.Series | None:
    """Daily closes in EUR, or None when the currency's EUR rate history is missing.
    `fx` is {currency: EUR per 1 unit}; a pence price uses the GBP rate / 100."""
    c = close.dropna()
    c.index = pd.DatetimeIndex(c.index).tz_localize(None).normalize()
    if ccy == "EUR":
        return c
    rate = fx.get("GBP" if ccy in PENCE else ccy) if ccy else None
    if rate is None or not len(rate):
        return None
    r = rate.copy()
    r.index = pd.DatetimeIndex(r.index).tz_localize(None).normalize()
    r = r[~r.index.duplicated(keep="last")].sort_index()
    both = r.reindex(r.index.union(c.index)).ffill(limit=FX_GAP_DAYS).reindex(c.index)
    return (c * both / (100 if ccy in PENCE else 1)).dropna()


def weekly_eur_returns(prices: dict[str, pd.Series], currency: dict[str, str | None], fx: dict[str, pd.Series],
                       asof: date, weeks: int = WEEKS) -> tuple[pd.DataFrame, dict[str, str]]:
    """(returns, reasons). `returns` has one column per ticker with all of the last `weeks` complete weekly returns
    (weeks end on Friday; the week containing `asof` counts only if asof is its Friday or later). Tickers without
    the full window are left out and get a plain reason, so every column shares one window."""
    labels = pd.date_range(end=pd.Timestamp(asof), periods=weeks + 1, freq="W-FRI")
    cols, reasons = {}, {}
    for t, close in sorted(prices.items()):
        eur = eur_prices(close, currency.get(t), fx)
        if eur is None:
            reasons[t] = f"no EUR exchange rate history for {currency.get(t) or 'an unknown currency'}"
            continue
        r = eur.resample("W-FRI").last().reindex(labels).pct_change().iloc[1:]
        if r.isna().any():
            reasons[t] = f"only {int(r.notna().sum())} of {weeks} weekly returns (needs the full window)"
            continue
        cols[t] = r
    return pd.DataFrame(cols, index=labels[1:]), reasons


def covariance(weekly: pd.DataFrame) -> pd.DataFrame:
    """Annualised sample covariance (x 52). Positive semi-definite because all columns share one window."""
    return weekly.cov() * 52


def correlation(cov: pd.DataFrame) -> pd.DataFrame:
    sd = np.sqrt(np.diag(cov))
    with np.errstate(divide="ignore", invalid="ignore"):
        return pd.DataFrame(cov.to_numpy() / np.outer(sd, sd), index=cov.index, columns=cov.columns)


# ---- reference versions of the page's formulas (web/src/lib/mix.ts must match these) ---------------------------

def normalise(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    if total <= 0 or any(w < 0 for w in weights.values()):
        raise ValueError("weights must be non-negative and sum to more than 0")
    return {t: w / total for t, w in weights.items()}


def exposure(weights: dict[str, float], meta: dict[str, dict], key: str) -> dict[str, float]:
    """Share of the mix per group. `key` is sector, country, currency or lists (a ticker on two lists counts in both)."""
    out: dict[str, float] = {}
    for t, w in normalise(weights).items():
        groups = meta[t][key] if isinstance(meta[t][key], list) else [meta[t][key] or "Unknown"]
        for g in groups:
            out[g] = out.get(g, 0.0) + w
    return out


def _vector(weights: dict[str, float], cov: pd.DataFrame) -> np.ndarray:
    return np.array([normalise(weights)[t] for t in cov.index])


def portfolio_vol(weights: dict[str, float], cov: pd.DataFrame) -> float:
    """sqrt(w' S w) for a mix whose tickers are exactly the rows of `cov`."""
    w = _vector(weights, cov)
    return math.sqrt(float(w @ cov.to_numpy() @ w))


def risk_contribution(weights: dict[str, float], cov: pd.DataFrame) -> dict[str, float]:
    """w_i (S w)_i / (w' S w): each name's share of the mix variance; sums to 1."""
    w = _vector(weights, cov)
    sw = cov.to_numpy() @ w
    return dict(zip(cov.index, (w * sw / float(w @ sw)).tolist()))


def effective_n(weights: dict[str, float]) -> float:
    """1 / sum(w_i^2): 1 for a single name, n for n equal weights."""
    return 1 / sum(w * w for w in normalise(weights).values())


def reference_mixes() -> dict:
    """Small fixed inputs and their results, written to web/src/fixtures/mix_reference.json for the TypeScript tests."""
    vols = {"AAA": 0.30, "BBB": 0.20, "CCC": 0.25}
    corr = {("AAA", "BBB"): 0.5, ("AAA", "CCC"): 0.2, ("BBB", "CCC"): -0.1}
    names = list(vols)
    cov = pd.DataFrame([[vols[a] * vols[b] * (1.0 if a == b else corr.get((a, b), corr.get((b, a)))) for b in names]
                        for a in names], index=names, columns=names)
    meta = {"AAA": {"sector": "Technology", "country": "United States", "currency": "USD", "lists": ["us_big_tech"]},
            "BBB": {"sector": "Energy", "country": "Norway", "currency": "NOK", "lists": ["eu_energy", "nordic_energy"]},
            "CCC": {"sector": "Energy", "country": "Finland", "currency": "EUR", "lists": ["nordic_energy"]}}
    mixes = []
    for weights in ({"AAA": 0.6, "BBB": 0.4}, {"AAA": 50, "BBB": 30, "CCC": 20}, {"CCC": 1}):
        sub = cov.loc[list(weights), list(weights)]
        mixes.append({"weights": weights, "vol": portfolio_vol(weights, sub),
                      "risk_contribution": risk_contribution(weights, sub), "effective_n": effective_n(weights),
                      "exposure": {k: exposure(weights, meta, k) for k in ("sector", "country", "currency", "lists")}})
    return {"tickers": names, "meta": meta, "cov": cov.to_numpy().tolist(), "mixes": mixes}
