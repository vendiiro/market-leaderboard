"""Research view: valuation facts, four measures, the candidate shortlist and the sentences on the cards.

Pure functions, no network. Design: docs/superpowers/specs/2026-11-12-research-workstation-design.md.
The measures (value, business quality, long-term trend, steadiness) have a long published record on large samples
and are NOT shown to work on this universe: see `evidence` in the output. Nothing here is advice; every sentence is
a fixed template filled with facts."""
from __future__ import annotations

from datetime import date

import pandas as pd

from .fmt import pct
from .fx import PENCE
from .quality import NOT_APPLICABLE

MEASURES = ("value", "quality", "trend", "steady")
LABELS = {"value": "Value", "quality": "Business quality", "trend": "Long-term trend", "steady": "Steadiness"}
SHORTLIST_MAX, SHORTLIST_SHARE = 15, 0.2
BIG_MOVE, CALM_INDEX, STEADY_BARS, STEADY_MIN_BARS = 0.05, 0.02, 756, 500
LOW, HIGH = -0.15, 0.15                       # P/E against its own past: beyond these it is "low" or "high for it"


def region_index(ticker: str) -> str:
    """Index a share's calm days are judged against: S&P 500 for US lines, STOXX 600 for all others."""
    return "^STOXX" if "." in ticker else "^GSPC"


def gate(net_income: dict[str, float | None]) -> dict:
    """Profit in the latest fiscal year and in at least 3 of the last 4. Fewer than 3 years on record: 'short'."""
    years = [v for _, v in sorted(net_income.items(), reverse=True) if v is not None][:4]
    profit = sum(v > 0 for v in years)
    status = "short" if len(years) < 3 else "pass" if years[0] > 0 and profit >= 3 else "fail"
    return {"status": status, "profit_years": profit, "years": len(years)}


def _eur_per(ccy: str, day: pd.Timestamp, fx: dict[str, pd.Series]) -> float | None:
    if ccy == "EUR":
        return 1.0
    s = fx.get(ccy)
    if s is None:
        return None
    s = s[s.index <= day]
    return float(s.iloc[-1]) if len(s) and (day - s.index[-1]).days <= 10 else None


def year_end_pes(raw_close: pd.Series, eps: dict[str, float | None], trade_ccy: str | None, report_ccy: str | None,
                 fx: dict[str, pd.Series]) -> list[dict]:
    """[{year, pe}] newest first: the share price on the last trading day of each fiscal year over that year's
    diluted EPS, with EPS converted from the reporting currency to the trading currency at that day's rate.
    A pence line is priced in pence, so its EPS in pounds is multiplied by 100. Years with a loss, without a
    price near the date or without a rate are left out; a wrong currency must never produce a 'cheap' P/E."""
    c = raw_close.dropna()
    c.index = pd.DatetimeIndex(c.index).tz_localize(None).normalize()
    trade = "GBP" if trade_ccy in PENCE else trade_ccy
    report = report_ccy or trade
    out = []
    for d, e in sorted(eps.items(), reverse=True):
        day = pd.Timestamp(d)
        before = c[c.index <= day]
        if not e or e <= 0 or not len(before) or (day - before.index[-1]).days > 10 or not trade:
            continue
        rate = 1.0
        if report != trade:
            a, b = _eur_per(report, day, fx), _eur_per(trade, day, fx)
            if not a or not b:
                continue
            rate = a / b
        out.append({"year": day.year, "pe": round(float(before.iloc[-1]) / (e * rate * (100 if trade_ccy in PENCE else 1)), 2)})
    return out


def big_own_days(close: pd.Series, index_close: pd.Series | None) -> int | None:
    """Days in the last 756 bars on which the share moved 5 % or more while its region's index moved under 2 %."""
    r = close.dropna().pct_change().dropna().iloc[-STEADY_BARS:]
    if len(r) < STEADY_MIN_BARS or index_close is None:
        return None
    r.index = pd.DatetimeIndex(r.index).tz_localize(None).normalize()
    idx = index_close.dropna().pct_change()
    idx.index = pd.DatetimeIndex(idx.index).tz_localize(None).normalize()
    calm = idx.reindex(r.index).abs() < CALM_INDEX          # a day the index has no bar for is not counted as calm
    return int(((r.abs() >= BIG_MOVE) & calm).sum())


def momentum(close: pd.Series) -> float | None:
    """Return from 12 months ago to 1 month ago (bar T-252 to T-21)."""
    c = close.dropna()
    return float(c.iloc[-22] / c.iloc[-253] - 1) if len(c) > 253 else None


def _num(v) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if x == x and abs(x) != float("inf") else None


def facts(ticker: str, fund: dict, stmt: dict, close: pd.Series, raw_close: pd.Series | None, trade_ccy: str | None,
          fx: dict[str, pd.Series], indices: dict[str, pd.Series]) -> dict:
    """Everything known about one company before ranking. Inconsistent figures are named in `inconsistent`
    and set aside from the measures (they stay visible)."""
    f = {k: _num(fund.get(k)) for k in ("trailingPE", "forwardPE", "enterpriseToEbitda", "priceToBook", "profitMargins",
                                        "operatingMargins", "returnOnEquity", "debtToEquity", "revenueGrowth", "earningsGrowth")}
    own = year_end_pes(raw_close if raw_close is not None else close, stmt.get("eps", {}), trade_ccy,
                       fund.get("financialCurrency"), fx)
    pe, fwd = f["trailingPE"], f["forwardPE"]
    bad = []
    if pe is not None and not 0 < pe <= 300:
        bad.append("pe")
    if fwd is not None and not 0 < fwd <= 300:
        bad.append("fwd_pe")
    if pe and fwd and "pe" not in bad and "fwd_pe" not in bad and not 0.4 <= fwd / pe <= 2.5:
        bad.append("fwd_pe")
    own_mid = float(pd.Series([x["pe"] for x in own]).median()) if len(own) >= 3 else None
    vs_own = pe / own_mid - 1 if pe and own_mid and "pe" not in bad else None
    if vs_own is not None and not -0.8 <= vs_own <= 4.0:
        bad.append("vs_own")
    eps = [v for _, v in sorted(stmt.get("eps", {}).items()) if v]
    return {
        "pe": pe, "fwd_pe": fwd, "ev_ebitda": f["enterpriseToEbitda"], "pb": f["priceToBook"], "margin": f["profitMargins"],
        "op_margin": f["operatingMargins"], "roe": f["returnOnEquity"], "debt_equity": f["debtToEquity"],
        "revenue_growth": f["revenueGrowth"], "earnings_growth": f["earningsGrowth"],
        "own_pes": own, "own_mid": own_mid, "vs_own": vs_own, "inconsistent": sorted(set(bad)),
        "momentum": momentum(close), "big_days": big_own_days(close, indices.get(region_index(ticker))),
        "gate": gate(stmt.get("net_income", {})), "report_currency": fund.get("financialCurrency") or None,
        "eps_growth_window": eps[-1] / eps[0] if len(eps) >= 2 and eps[0] > 0 and eps[-1] > 0 else None,
    }


def _rank(values: dict[str, float | None], low_is_good: bool = False) -> dict[str, float]:
    """Percentile rank 0..1 within the companies that have a value; 1 = best. Ties share the mean rank."""
    s = pd.Series({t: v for t, v in values.items() if v is not None}, dtype=float)
    if not len(s):
        return {}
    return (s.rank(ascending=not low_is_good) / len(s)).to_dict()


def _mean(xs: list[float | None]) -> float | None:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def measures(all_facts: dict[str, dict], sector: dict[str, str | None]) -> dict[str, dict]:
    """{ticker: {value, quality, trend, steady, place-related inputs}}; ranks within the whole universe."""
    ok = {t: f for t, f in all_facts.items()}
    use = {t: lambda k, f=f: None if k in f["inconsistent"] else f.get(k) for t, f in ok.items()}
    by_sector: dict[str, list[float]] = {}
    for t, f in ok.items():
        if use[t]("fwd_pe"):
            by_sector.setdefault(sector.get(t) or "", []).append(f["fwd_pe"])
    everyone = sorted(x for xs in by_sector.values() for x in xs)
    marks, mids = {}, {}
    for t in ok:
        peers = by_sector.get(sector.get(t) or "", [])
        peers = sorted(peers) if len(peers) >= 5 else everyone
        marks[t], mids[t] = peers, (float(pd.Series(peers).median()) if peers else None)
    vs_sector = {t: (f["fwd_pe"] / mids[t] - 1 if use[t]("fwd_pe") and mids[t] else None) for t, f in ok.items()}
    r_own = _rank({t: use[t]("vs_own") for t in ok}, low_is_good=True)
    r_sec = _rank(vs_sector, low_is_good=True)
    r_ev = _rank({t: (f["ev_ebitda"] if f["ev_ebitda"] and f["ev_ebitda"] > 0 else None) for t, f in ok.items()}, low_is_good=True)
    r_roe = _rank({t: (f["roe"] if f["roe"] is not None and f["roe"] <= 1 else None) for t, f in ok.items()})
    r_margin = _rank({t: f["margin"] for t, f in ok.items()})
    no_debt_check = {s for s, keys in NOT_APPLICABLE.items() if "debtToEquity" in keys}
    r_debt = _rank({t: (None if (sector.get(t) or "").casefold() in no_debt_check else f["debt_equity"]) for t, f in ok.items()},
                   low_is_good=True)
    r_trend = _rank({t: f["momentum"] for t, f in ok.items()})
    r_steady = _rank({t: f["big_days"] for t, f in ok.items()}, low_is_good=True)
    out = {}
    for t in ok:
        m = {"value": _mean([r_own.get(t), r_sec.get(t), r_ev.get(t)]),
             "quality": _mean([r_roe.get(t), r_margin.get(t), r_debt.get(t)]),
             "trend": r_trend.get(t), "steady": r_steady.get(t)}
        have = [v for v in m.values() if v is not None]
        out[t] = m | {"score": sum(have) / len(have) if len(have) >= 3 else None, "vs_sector": vs_sector[t],
                      "sector_mid": mids[t], "sector_marks": marks[t]}
    return out


def shortlist(all_facts: dict[str, dict], ms: dict[str, dict]) -> list[str]:
    """Tickers that pass the gate, best average rank first: 15, or a fifth of the gate-passers if that is fewer."""
    passed = [t for t, f in all_facts.items() if f["gate"]["status"] == "pass" and ms[t]["score"] is not None]
    n = min(SHORTLIST_MAX, max(1, int(len(passed) * SHORTLIST_SHARE))) if passed else 0
    return sorted(passed, key=lambda t: (-ms[t]["score"], t))[:n]


def _pos(values: dict[str, float | None], t: str, low_is_good: bool = False) -> str:
    have = sorted((k for k, v in values.items() if v is not None), key=lambda k: (values[k] if low_is_good else -values[k], k))
    return f"{have.index(t) + 1} of {len(have)}"


def sentence(measure: str, t: str, all_facts: dict[str, dict], ms: dict[str, dict]) -> str | None:
    """One fixed-template sentence stating the fact behind a measure. Facts only: no judgement words."""
    f, m = all_facts[t], ms[t]
    if measure == "value":
        if f["vs_own"] is not None:
            return f"P/E {f['pe']:.1f} against a middle of {f['own_mid']:.1f} over its last {len(f['own_pes'])} fiscal year-ends"
        if m["vs_sector"] is not None:
            return f"Forward P/E {f['fwd_pe']:.1f} against a middle of {m['sector_mid']:.1f} for comparable companies"
        if f["ev_ebitda"] and f["ev_ebitda"] > 0:
            return f"EV/EBITDA {f['ev_ebitda']:.1f}"
    if measure == "quality" and f["margin"] is not None:
        return f"Profit margin {pct(f['margin'], 0, sign=False)}, place {_pos({k: v['margin'] for k, v in all_facts.items()}, t)}"
    if measure == "trend" and f["momentum"] is not None:
        return (f"{pct(f['momentum'], 0)} over 12 months excluding the latest month, "
                f"place {_pos({k: v['momentum'] for k, v in all_facts.items()}, t)}")
    if measure == "steady" and f["big_days"] is not None:
        return (f"{f['big_days']} days in three years with a move of 5% or more while its market index was calm, "
                f"place {_pos({k: v['big_days'] for k, v in all_facts.items()}, t, low_is_good=True)}")
    return None


def case(t: str, all_facts: dict[str, dict], ms: dict[str, dict]) -> tuple[list[str], list[str]]:
    """(why look closer, what argues against): the two highest measures at or above the middle and the two lowest
    below it, each as its sentence."""
    ranked = sorted((k for k in MEASURES if ms[t][k] is not None), key=lambda k: -ms[t][k])
    strong = [k for k in ranked if ms[t][k] >= 0.5][:2]
    weak = [k for k in reversed(ranked) if ms[t][k] < 0.5][:2]
    return ([s for k in strong if (s := sentence(k, t, all_facts, ms))], [s for k in weak if (s := sentence(k, t, all_facts, ms))])


def caveats(f: dict, trade_ccy: str | None) -> list[str]:
    out = []
    g = f["eps_growth_window"]
    if g is not None and g > 5:
        out.append(f"Profit per share grew {g:.0f}-fold across the statement years: a P/E below its own past reflects that growth, not a fall in price")
    if f["pe"] and f["fwd_pe"] and "fwd_pe" not in f["inconsistent"] and f["fwd_pe"] < 0.6 * f["pe"]:
        out.append("Forward P/E is far below trailing P/E: it rests on analyst estimates of strong profit growth")
    if "fwd_pe" in f["inconsistent"] or "pe" in f["inconsistent"] or "vs_own" in f["inconsistent"]:
        out.append("Some valuation figures look inconsistent and are left out of the value measure")
    if f["roe"] is not None and f["roe"] > 1:
        out.append("Return on equity above 100% looks distorted and is left out of the quality measure")
    report = f["report_currency"]
    if report and trade_ccy and report != ("GBP" if trade_ccy in PENCE else trade_ccy):
        out.append(f"The company reports in {report} and trades in {trade_ccy}: past profit per share is converted at each year-end rate")
    if f["gate"]["years"] < 4:
        out.append(f"Only {f['gate']['years']} fiscal years of statements are available")
    out.append("Fundamentals are current values, not what was known at past dates; the value and quality measures are untested")
    return out


def valuation_word(vs_own: float | None) -> str:
    return "no data" if vs_own is None else "low for it" if vs_own <= LOW else "high for it" if vs_own >= HIGH else "typical"


def build(rows: list[dict], fund: dict, statements: dict, prices: dict, raw_closes: dict, fx: dict, indices: dict,
          headlines: dict[str, list[dict]], evidence: dict, asof: date, dip_move: float = 0.04) -> dict:
    """The body of research.json. `rows` are the leaderboard rows (one per ticker with data tonight)."""
    by = {r["ticker"]: r for r in rows}
    all_facts = {t: facts(t, fund.get(t) or {}, statements.get(t) or {}, prices[t][0], raw_closes.get(t), by[t]["currency"],
                          fx, indices) for t in by}
    ms = measures(all_facts, {t: by[t]["sector"] for t in by})
    short = shortlist(all_facts, ms)
    companies = []
    for t, r in by.items():
        f, m = all_facts[t], ms[t]
        why, against = case(t, all_facts, ms)
        news = headlines.get(t, [])
        events = ([f"Moved {pct(r['ret_1d'])} on its last trading day"] if r["ret_1d"] is not None and abs(r["ret_1d"]) >= dip_move else [])
        events += ["Dip flag (untested screen rule)"] if r["dip"] else []
        events += ["Headline in the last 2 days"] if any(h["days_old"] is not None and h["days_old"] <= 2 for h in news) else []
        companies.append({
            **{k: r[k] for k in ("ticker", "name", "lists", "sector", "country", "currency", "last_bar", "stale", "price",
                                 "ret_1d", "ret_1y", "dd52", "vol_1y", "spark")},
            **{k: f[k] for k in ("pe", "fwd_pe", "ev_ebitda", "pb", "margin", "op_margin", "roe", "debt_equity", "revenue_growth",
                                 "earnings_growth", "own_pes", "own_mid", "vs_own", "inconsistent", "momentum", "big_days",
                                 "report_currency")},
            "vs_sector": m["vs_sector"], "sector_mid": m["sector_mid"], "sector_marks": [round(x, 2) for x in m["sector_marks"]],
            "gate": f["gate"], "measures": {k: (None if m[k] is None else round(m[k] * 100)) for k in MEASURES},
            "place": short.index(t) + 1 if t in short else None, "valuation": valuation_word(f["vs_own"]),
            "why": why, "against": against, "caveats": caveats(f, r["currency"]), "events": events, "headlines": news,
        })
    return {"shortlist": short, "gate_passed": sum(f["gate"]["status"] == "pass" for f in all_facts.values()),
            "labels": LABELS, "evidence": evidence, "companies": companies}
