"""Synthetic inputs for `python -m engine build --demo`: no network, seeded, the same output every run.

The universe is invented (no real company) and small, and it contains every state the page must handle: a stale
row (FINB.HE), a ticker without data (FIND.HE), a ticker on two lists (ENGA.OL), a recent listing without the full
risk window (DEFC.PA), a pence-quoted line (DEFB.L, ENGC.L) and a row the dip rule flags (DEMD)."""
from __future__ import annotations

import numpy as np
import pandas as pd

END = "2026-11-10"          # a Tuesday
BARS = 800
SEED = 20261111

# ticker: (name, sector, country, currency, yearly drift, yearly volatility)
STOCKS = {
    "DEMA": ("Demo Chips", "Technology", "United States", "USD", 0.30, 0.42),
    "DEMB": ("Demo Software", "Technology", "United States", "USD", 0.15, 0.26),
    "DEMC": ("Demo Devices", "Technology", "United States", "USD", 0.08, 0.24),
    "DEMD": ("Demo Search", "Communication Services", "United States", "USD", 0.12, 0.30),
    "DEFA.DE": ("Demo Armour", "Industrials", "Germany", "EUR", 0.35, 0.40),
    "DEFB.L": ("Demo Aerospace", "Industrials", "United Kingdom", "GBp", 0.18, 0.25),
    "DEFC.PA": ("Demo Avionics", "Industrials", "France", "EUR", 0.10, 0.28),
    "ENGA.OL": ("Demo Offshore", "Energy", "Norway", "NOK", 0.05, 0.30),
    "ENGB.MC": ("Demo Grid", "Utilities", "Spain", "EUR", 0.07, 0.18),
    "ENGC.L": ("Demo Petroleum", "Energy", "United Kingdom", "GBp", 0.04, 0.24),
    "NRDA.HE": ("Demo Refining", "Energy", "Finland", "EUR", -0.10, 0.36),
    "NRDB.CO": ("Demo Wind", "Industrials", "Denmark", "DKK", -0.05, 0.44),
    "FINA.HE": ("Demo Paper", "Basic Materials", "Finland", "EUR", 0.02, 0.27),
    "FINB.HE": ("Demo Retail", "Consumer Cyclical", "Finland", "EUR", 0.06, 0.22),
    "FINC.HE": ("Demo Instruments", "Technology", "Finland", "EUR", 0.11, 0.29),
    "FIND.HE": ("Demo Housing", "Real Estate", "Finland", "EUR", 0.00, 0.20),
}
LISTS = {
    "us_big_tech": ("US big tech", ["DEMA", "DEMB", "DEMC", "DEMD"]),
    "eu_defence": ("European defence", ["DEFA.DE", "DEFB.L", "DEFC.PA"]),
    "eu_energy": ("European energy", ["ENGA.OL", "ENGB.MC", "ENGC.L"]),
    "nordic_energy": ("Nordic energy", ["NRDA.HE", "ENGA.OL", "NRDB.CO"]),
    "fi_small": ("Finnish smaller companies", ["FINA.HE", "FINB.HE", "FINC.HE", "FIND.HE"]),
}
EUR_PER = {"USD": 0.92, "GBP": 1.17, "NOK": 0.086, "DKK": 0.134}     # level of each synthetic exchange rate


def inputs() -> dict:
    """The same keys as build.live_inputs(): cfg, meta, prices, fund, rates_usd, fx, reasons."""
    rng = np.random.default_rng(SEED)
    days = pd.bdate_range(end=END, periods=BARS)
    market = rng.normal(0, 0.008, BARS)
    prices = {}
    for t, (_, _, _, _, drift, vol) in STOCKS.items():
        daily = drift / 252 + 0.6 * market + rng.normal(0, vol / 252 ** 0.5 * 0.8, BARS)
        close = pd.Series(np.round(50 * np.exp(np.cumsum(daily)), 4), index=days)
        volume = pd.Series(rng.integers(200_000, 900_000, BARS).astype(float), index=days)
        prices[t] = (close, volume)
    close, volume = prices["DEMD"]
    close.iloc[-1] = round(close.iloc[-2] * 0.94, 4)                  # a 6% one-day fall: flagged by the dip rule
    prices["FINB.HE"] = tuple(s.iloc[:-10] for s in prices["FINB.HE"])   # last bar 10 sessions old: stale
    prices["DEFC.PA"] = tuple(s.iloc[-300:] for s in prices["DEFC.PA"])  # listed 300 sessions ago: no full risk window
    del prices["FIND.HE"]                                             # nothing came back tonight

    fx = {c: pd.Series(np.round(level * np.exp(np.cumsum(rng.normal(0, 0.004, BARS))), 6), index=days)
          for c, level in EUR_PER.items()}
    usd_per_eur = 1 / float(fx["USD"].iloc[-1])
    rates_usd = {"EUR": usd_per_eur} | {c: float(s.iloc[-1]) * usd_per_eur for c, s in fx.items() if c != "USD"}

    fund = {}
    for i, (t, s) in enumerate(STOCKS.items()):
        fund[t] = {"returnOnEquity": 0.05 + 0.03 * (i % 7), "profitMargins": -0.02 + 0.03 * (i % 6),
                   "debtToEquity": 40.0 + 25 * (i % 5), "freeCashflow": (i % 4 - 0.5) * 4e8, "revenueGrowth": -0.03 + 0.02 * (i % 8),
                   "marketCap": (2 + 30 * (i % 5)) * 1e9, "forwardPE": 12.0 + i, "trailingPE": 15.0 + i,
                   "currency": s[3]}
    fund["FINC.HE"] = {"marketCap": 9e8, "currency": "EUR"}           # thin fundamentals: no score
    del fund["ENGB.MC"]                                               # no fundamentals at all

    # ---- research view: statements, valuation ratios, region indices, headlines ----
    index = pd.Series(np.round(100 * np.exp(np.cumsum(0.6 * market)), 4), index=days)
    statements, raw_closes = {}, {t: p[0] for t, p in prices.items()}
    for i, (t, s) in enumerate(STOCKS.items()):
        close = prices[t][0] if t in prices else None
        ccy = s[3]
        report = "USD" if t == "ENGA.OL" else "GBP" if ccy == "GBp" else ccy      # ENGA.OL reports in dollars, trades in kroner
        eps, income = {}, {}
        for y in (2025, 2024, 2023, 2022):
            day = pd.Timestamp(f"{y}-12-31")
            before = close[close.index <= day] if close is not None else []
            px = float(before.iloc[-1]) if len(before) else 40.0
            pe_y = (10 + 3 * (i % 6)) * (1 + 0.15 * ((i + y) % 3 - 1))
            e = px / pe_y * (0.125 * 2 ** (y - 2022) if t == "DEMA" else 1)      # DEMA: profit per share grows 8-fold
            if report == "GBP":
                e /= 100                                                          # pence price, pounds per share
            elif report != ccy:
                e *= float(fx[ccy][fx[ccy].index <= day].iloc[-1] / fx[report][fx[report].index <= day].iloc[-1]) if len(before) else 0.09
            eps[f"{y}-12-31"] = round(e, 4)
            income[f"{y}-12-31"] = round(e * 1e8)
        if t == "NRDA.HE":                                                        # two loss years: fails the gate
            income |= {"2025-12-31": -3e7, "2024-12-31": -1e7}
            eps |= {"2025-12-31": -0.3, "2024-12-31": -0.1}
        if t == "FINC.HE":                                                        # two years on record: not enough history
            eps, income = dict(list(eps.items())[:2]), dict(list(income.items())[:2])
        statements[t] = {"eps": eps, "net_income": income}
        if t in fund and close is not None:
            trade_eps = eps["2025-12-31"] * (100 if report == "GBP" else 1)
            if report not in (ccy, "GBP"):
                trade_eps = float(close[close.index <= pd.Timestamp("2025-12-31")].iloc[-1]) / ((10 + 3 * (i % 6)) * (1 + 0.15 * ((i + 2025) % 3 - 1)))
            pe = float(close.iloc[-1]) / trade_eps if trade_eps > 0 else None
            fund[t] |= {"trailingPE": pe, "forwardPE": None if pe is None else pe * {"DEMA": 0.5, "FINA.HE": 3.0}.get(t, 0.85),
                        "enterpriseToEbitda": 6.0 + 1.5 * (i % 7), "priceToBook": 1.2 + 0.8 * (i % 5),
                        "operatingMargins": 0.04 + 0.03 * (i % 6), "earningsGrowth": -0.1 + 0.06 * (i % 7), "financialCurrency": report}
    headlines = {
        "DEMD": [{"title": "Demo Search shares fall after its quarterly report", "source": "Demo Wire",
                  "url": "https://example.com/demo-search", "date": END, "days_old": 0}],
        "DEMA": [{"title": "Demo Chips opens a second plant", "source": "Demo Wire", "url": None,
                  "date": "2026-11-03", "days_old": 7}],
    }

    member: dict[str, list[str]] = {}
    for key, (_, tickers) in LISTS.items():
        for t in tickers:
            member.setdefault(t, []).append(key)
    return {
        "cfg": {k: {"name": name, "tickers": {t: STOCKS[t][0] for t in tickers}} for k, (name, tickers) in LISTS.items()},
        "meta": {t: {"name": s[0], "lists": member[t], "currency": s[3], "sector": s[1], "country": s[2]}
                 for t, s in STOCKS.items()},
        "prices": prices, "fund": fund, "rates_usd": rates_usd, "fx": fx,
        "reasons": {"FIND.HE": "Yahoo returned no rows for this ticker"},
        "statements": statements, "raw_closes": raw_closes, "indices": {"^GSPC": index, "^STOXX": index},
        "headlines": headlines,
    }
