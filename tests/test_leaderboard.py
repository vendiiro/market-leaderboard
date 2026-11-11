import math
from datetime import date

import pandas as pd
import pytest

from engine.config import Settings
from engine.leaderboard import lists, ranked, rows, summary
from engine.returns import rank_table, windows
from engine.screen import dip_reasons
from engine.metrics import compute_metrics
from synth import END, flat, geometric, slide

ASOF = date(2026, 10, 29)        # synth.END, a Thursday
S = Settings()


def meta(*tickers, lists_=("eu_energy",)):
    return {t: {"name": f"{t} Corp", "lists": list(lists_), "currency": "USD", "sector": "Energy", "country": "X"} for t in tickers}


def bars(close):
    return close, None


# ---- returns.windows -----------------------------------------------------------------------------------------

def test_each_window_has_its_known_value():
    c = geometric(300, 0.01)
    w = windows(c)
    assert w["ret_1d"] == pytest.approx(0.01, abs=1e-4)
    assert w["ret_1w"] == pytest.approx(1.01 ** 5 - 1, abs=1e-4)
    assert w["ret_1m"] == pytest.approx(1.01 ** 21 - 1, abs=1e-4)
    assert w["ret_1y"] == pytest.approx(1.01 ** 252 - 1, abs=1e-4)


def test_ytd_starts_from_the_last_bar_of_the_previous_year():
    c = geometric(300, 0.001)
    base = c[c.index.year == 2025].iloc[-1]
    assert windows(c)["ret_ytd"] == pytest.approx(c.iloc[-1] / base - 1, abs=1e-4)
    assert windows(c[c.index.year == 2026])["ret_ytd"] is None          # no bar before this year


def test_missing_history_is_none_not_zero():
    w = windows(geometric(30, 0.01))
    assert w["ret_1m"] is not None and w["ret_1y"] is None and w["vol_1y"] is None
    assert all(v is None for v in windows(flat(1)).values())


def test_vol_is_annualised_daily_standard_deviation():
    assert windows(geometric(300, 0.01))["vol_1y"] == pytest.approx(0, abs=1e-6)       # constant return: no volatility
    c = 100 * pd.Series([1.02 if i % 2 else 0.99 for i in range(300)], index=flat(300).index).cumprod()
    daily = c.pct_change().dropna().iloc[-252:]
    assert windows(c)["vol_1y"] == pytest.approx(daily.std() * math.sqrt(252), abs=1e-4)
    assert windows(c.iloc[:126])["vol_1y"] is None and windows(c.iloc[:127])["vol_1y"] is not None   # needs 126 returns


def test_rank_is_descending_with_ties_by_ticker_and_none_unranked():
    assert rank_table({"B": 0.1, "A": 0.1, "C": 0.3, "D": None, "E": -0.2}) == {"C": 1, "A": 2, "B": 3, "E": 4}


# ---- leaderboard.rows ----------------------------------------------------------------------------------------

def test_row_fields_dip_rule_and_spark():
    prices = {"UP": bars(geometric(300, 0.001)), "DROP": bars(slide())}
    out, failures = rows(prices, {}, meta("UP", "DROP"), S, ASOF)
    by = {r["ticker"]: r for r in out}
    assert failures == [] and [r["ticker"] for r in out] == ["DROP", "UP"]
    assert not by["UP"]["dip"] and by["UP"]["dip_reasons"] == []
    assert by["DROP"]["dip"] and by["DROP"]["dip_reasons"] == dip_reasons(compute_metrics(slide(), None), S.dip)
    assert len(by["UP"]["spark"]) == 60 and by["UP"]["spark"][0] == 100 and by["UP"]["spark"][-1] > 100
    assert by["UP"]["last_bar"] == END and by["UP"]["stale"] is False and by["UP"]["stale_reason"] is None
    assert by["UP"]["q_score"] is None and by["UP"]["q_scored"] == 0            # no fundamentals: no score, not zero


def test_stale_row_is_marked_and_never_flagged():
    old = slide(end="2026-10-20")                                    # 7 weekdays before ASOF
    out, _ = rows({"OLD": bars(old), "EDGE": bars(geometric(300, 0.001, end="2026-10-23"))}, {}, meta("OLD", "EDGE"), S, ASOF)
    by = {r["ticker"]: r for r in out}
    assert by["OLD"]["stale"] and "7 weekdays old" in by["OLD"]["stale_reason"] and not by["OLD"]["dip"]
    assert by["EDGE"]["stale"] is False                              # exactly 4 weekdays old is still fresh


def test_missing_or_short_series_is_a_failure_with_a_reason():
    out, failures = rows({"SHORT": bars(geometric(30, 0.01))}, {}, meta("SHORT", "GONE"), S, ASOF)
    assert out == [] and {f["ticker"]: f["reason"] for f in failures} == {
        "GONE": "no price data tonight", "SHORT": "fewer than 60 daily bars"}


def test_quality_uses_pounds_for_a_pence_line():
    fund = {"returnOnEquity": 0.2, "profitMargins": 0.1, "debtToEquity": 50, "freeCashflow": 1e9, "revenueGrowth": 0.05,
            "marketCap": 50e9, "currency": "GBp"}
    m = meta("BA.L")
    m["BA.L"]["currency"] = "GBp"
    out, _ = rows({"BA.L": bars(geometric(300, 0.001))}, {"BA.L": fund}, m, S, ASOF, rates_usd={"GBP": 1.3})
    assert out[0]["q_score"] == 100 and out[0]["q_passed"] == out[0]["q_scored"] == 6     # 65B USD passes the size check


# ---- ranks and summaries -------------------------------------------------------------------------------------

def three():
    prices = {"A": bars(geometric(300, 0.003)), "B": bars(geometric(300, 0.002)), "C": bars(geometric(300, 0.001)),
              "OLD": bars(geometric(300, 0.01, end="2026-10-01"))}
    return rows(prices, {}, meta("A", "B", "C", "OLD"), S, ASOF)[0]


def test_rank_per_period_and_stale_rows_unranked():
    r = ranked(three(), ["A", "B", "C", "OLD"])
    assert [r[t]["1m"]["rank"] for t in "ABC"] == [1, 2, 3] and "OLD" not in r
    assert r["A"]["1m"] == {"rank": 1, "rank_prev": 1, "rank_delta": 0}
    assert ranked(three(), ["B", "C"])["B"]["1y"]["rank"] == 1                    # ranks are within the list


def test_rank_prev_is_the_rank_one_bar_earlier():
    up = geometric(300, 0.001)
    jump = geometric(300, 0.0005)
    jump.iloc[-1] *= 1.10                                             # was behind yesterday, leads today
    out, _ = rows({"JUMP": bars(jump), "UP": bars(up)}, {}, meta("JUMP", "UP"), S, ASOF)
    r = ranked(out, ["JUMP", "UP"])
    assert r["JUMP"]["1w"] == {"rank": 1, "rank_prev": 2, "rank_delta": 1}
    assert r["UP"]["1w"] == {"rank": 2, "rank_prev": 1, "rank_delta": -1}
    cut = {"JUMP": bars(jump.iloc[:-1]), "UP": bars(up.iloc[:-1])}
    yesterday = ranked(rows(cut, {}, meta("JUMP", "UP"), S, date(2026, 10, 28))[0], ["JUMP", "UP"])
    assert {t: r[t]["1w"]["rank_prev"] for t in r} == {t: yesterday[t]["1w"]["rank"] for t in r}


def test_summary_is_the_equal_weight_mean_of_fresh_rows():
    s = summary(three(), ["A", "B", "C", "OLD"])
    expected = sum(1.0 + d for d in (0.003, 0.002, 0.001)) / 3 - 1
    assert s["periods"]["1d"]["mean"] == pytest.approx(expected, abs=1e-4)
    assert s["periods"]["1d"] | {"mean": 0} == {"mean": 0, "n": 3, "top": "A", "bottom": "C"}
    assert s["count"] == 4 and s["stale"] == 1 and s["flags"] == 0
    assert summary([], ["A"])["periods"]["1m"] == {"mean": None, "n": 0, "top": None, "bottom": None}


def test_lists_output_has_rank_and_no_private_fields():
    cfg = {"eu_energy": {"name": "European energy", "tickers": {"A": "A", "OLD": "Old"}},
           "nordic_energy": {"name": "Nordic energy", "tickers": {"A": "A", "B": "B"}}}
    out = lists(three(), cfg)
    assert [x["key"] for x in out] == ["eu_energy", "nordic_energy"] and out[0]["name"] == "European energy"
    a1, old = out[0]["rows"]
    assert a1["rank"]["1m"]["rank"] == 1 and old["rank"] is None and "_prev" not in a1
    assert [r["ticker"] for r in out[1]["rows"]] == ["A", "B"]         # A is on both lists
