import importlib.util
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine import research as R
from engine.fetch import fetch_statements, parse_headlines

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("check_wording", ROOT / "scripts" / "check_wording.py")
check_wording = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_wording)

DAYS = pd.bdate_range(end="2026-11-10", periods=1300)


def flat(v=100.0):
    return pd.Series(v, index=DAYS)


# ---- gate --------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("income, status, profit", [
    ({"2025": 5, "2024": 4, "2023": 3, "2022": 2}, "pass", 4),
    ({"2025": 5, "2024": 4, "2023": 3, "2022": -2}, "pass", 3),          # one old loss year (Amazon 2022)
    ({"2025": -1, "2024": 4, "2023": 3, "2022": 2}, "fail", 3),          # the latest year must show a profit
    ({"2025": 5, "2024": -4, "2023": -3, "2022": 2}, "fail", 2),
    ({"2025": 5, "2024": 4, "2023": 3}, "pass", 3),                      # three years on record, all profitable
    ({"2025": 5, "2024": 4}, "short", 2),
    ({"2025": 5, "2024": 4, "2023": None, "2022": None}, "short", 2),    # missing years are unknown, not losses
    ({}, "short", 0),
])
def test_gate(income, status, profit):
    assert R.gate(income) == {"status": status, "profit_years": profit, "years": len([v for v in income.values() if v is not None][:4])}


# ---- P/E at past year-ends, in the right currency -----------------------------------------------------------------

def test_year_end_pe_uses_the_price_on_the_last_trading_day_of_the_fiscal_year():
    close = pd.Series(np.linspace(50, 150, len(DAYS)), index=DAYS)
    out = R.year_end_pes(close, {"2025-12-31": 5.0, "2024-12-31": 4.0, "2023-12-31": -1.0, "2010-12-31": 2.0}, "EUR", "EUR", {})
    assert [x["year"] for x in out] == [2025, 2024]                       # a loss year and a year without prices are left out
    assert R.year_end_pes(close, {"2025-12-31": 0.01}, "EUR", "EUR", {}) == []   # a near-zero profit: P/E in the thousands
    assert out[0]["pe"] == pytest.approx(float(close[close.index <= "2025-12-31"].iloc[-1]) / 5.0, abs=0.01)


def test_a_dollar_reporter_trading_in_kroner_is_converted_not_read_as_cheap():
    close = flat(300.0)                                                   # NOK
    fx = {"USD": flat(0.9), "NOK": flat(0.09)}                            # EUR per unit: 1 USD = 10 NOK
    out = R.year_end_pes(close, {"2025-12-31": 3.0}, "NOK", "USD", fx)    # 3 USD = 30 NOK per share
    assert out == [{"year": 2025, "pe": 10.0}]                            # unconverted it would read 100
    zoned = {k: s.tz_localize("Europe/London") for k, s in fx.items()}    # what Yahoo's rate history looks like
    assert R.year_end_pes(close, {"2025-12-31": 3.0}, "NOK", "USD", zoned) == out
    assert R.year_end_pes(close, {"2025-12-31": 3.0}, "NOK", "USD", {"NOK": flat(0.09)}) == []   # no rate: no figure, never a guess


def test_a_pence_line_reporting_in_pounds_or_dollars():
    close = flat(2000.0)                                                  # pence = 20 pounds
    assert R.year_end_pes(close, {"2025-12-31": 2.0}, "GBp", "GBP", {}) == [{"year": 2025, "pe": 10.0}]
    fx = {"USD": flat(0.9), "GBP": flat(1.2)}                             # 1 USD = 0.75 GBP
    assert R.year_end_pes(close, {"2025-12-31": 4.0}, "GBp", "USD", fx)[0]["pe"] == pytest.approx(2000 / (4 * 0.75 * 100), abs=0.01)


# ---- price measures -----------------------------------------------------------------------------------------------

def test_big_own_days_ignores_days_when_the_market_also_moved():
    r = pd.Series(0.001, index=DAYS)
    r.iloc[[-10, -20, -30]] = [0.07, -0.06, 0.08]
    idx = pd.Series(0.0005, index=DAYS)
    idx.iloc[-30] = 0.04                                                  # a market-wide day: does not count against the share
    close, index = (1 + r).cumprod() * 100, (1 + idx).cumprod() * 100
    assert R.big_own_days(close, index) == 2
    assert R.big_own_days(close.iloc[-300:], index) is None and R.big_own_days(close, None) is None


def test_momentum_skips_the_latest_month():
    c = pd.Series(np.r_[np.full(1000, 100.0), np.linspace(100, 120, 279), np.full(21, 200.0)], index=DAYS)
    assert R.momentum(c) == pytest.approx(c.iloc[-22] / c.iloc[-253] - 1) and R.momentum(c) < 0.25    # the late jump is not in it
    assert R.momentum(c.iloc[-200:]) is None
    assert R.region_index("NVDA") == "^GSPC" and R.region_index("EQNR.OL") == "^STOXX"


# ---- facts, consistency, ranks, shortlist -------------------------------------------------------------------------

def fund(pe=20.0, fwd=18.0, **kw):
    return {"trailingPE": pe, "forwardPE": fwd, "enterpriseToEbitda": 10.0, "profitMargins": 0.1, "returnOnEquity": 0.15,
            "debtToEquity": 50.0, "financialCurrency": "EUR"} | kw


STMT = {"eps": {"2025-12-31": 5.0, "2024-12-31": 4.0, "2023-12-31": 4.0, "2022-12-31": 2.0},
        "net_income": {"2025-12-31": 5e8, "2024-12-31": 4e8, "2023-12-31": 4e8, "2022-12-31": 2e8}}


def one(f=None, stmt=STMT, close=None):
    return R.facts("AAA.HE", f or fund(), stmt, flat() if close is None else close, None, "EUR", {}, {"^STOXX": flat(50.0)})


def test_facts_compare_pe_with_its_own_past():
    f = one()
    assert [x["pe"] for x in f["own_pes"]] == [20.0, 25.0, 25.0, 50.0] and f["own_mid"] == 25.0
    assert f["vs_own"] == pytest.approx(-0.2) and f["inconsistent"] == [] and f["gate"]["status"] == "pass"
    assert R.valuation_word(f["vs_own"]) == "low for it" and R.valuation_word(0.0) == "typical"
    assert R.valuation_word(0.3) == "high for it" and R.valuation_word(None) == "no data"


@pytest.mark.parametrize("f, flagged", [
    (fund(pe=-5.0), ["pe"]), (fund(pe=900.0), ["pe"]), (fund(fwd=60.0), ["fwd_pe"]), (fund(fwd=5.0), ["fwd_pe"]),
    (fund(pe=2.0, fwd=2.0), ["vs_own"]),                                 # 92 % under its own past: a data problem, not a bargain
])
def test_inconsistent_figures_are_named_and_kept_out_of_the_comparison(f, flagged):
    out = one(f)
    assert out["inconsistent"] == flagged
    if "pe" in flagged:
        assert out["vs_own"] is None


def universe(n=20):
    """n companies; AAA is cheapest and steadiest, later tickers are worse on every fact."""
    facts, sector = {}, {}
    for i in range(n):
        t = f"T{i:02d}"
        f = one(fund(pe=10.0 + i, fwd=9.0 + i, enterpriseToEbitda=5.0 + i, profitMargins=0.3 - 0.01 * i, returnOnEquity=0.3 - 0.01 * i,
                     debtToEquity=20.0 + 5 * i))
        f |= {"momentum": 0.5 - 0.03 * i, "big_days": i}
        facts[t], sector[t] = f, "Industrials"
    return facts, sector


def test_ranks_run_from_best_to_worst_and_the_shortlist_is_a_fifth_of_the_gate_passers():
    facts, sector = universe()
    ms = R.measures(facts, sector)
    assert ms["T00"]["value"] == pytest.approx(1.0) and ms["T19"]["value"] == pytest.approx(0.05)
    assert all(ms["T00"][k] > ms["T10"][k] > ms["T19"][k] for k in R.MEASURES)
    assert R.shortlist(facts, ms) == ["T00", "T01", "T02", "T03"]                    # 20 pass the gate: a fifth is 4
    facts["T00"]["gate"] = {"status": "fail", "profit_years": 1, "years": 4}
    assert R.shortlist(facts, ms)[0] == "T01" and len(R.shortlist(facts, ms)) == 3   # 19 pass: 3
    big, bs = universe(100)
    assert len(R.shortlist(big, R.measures(big, bs))) == 15                          # never more than 15


def test_a_company_with_fewer_than_three_measures_has_no_score_and_small_sectors_use_everyone():
    facts, sector = universe()
    facts["T05"] |= {"momentum": None, "big_days": None}
    sector["T19"] = "Utilities"                                                      # alone in its sector
    ms = R.measures(facts, sector)
    assert ms["T05"]["score"] is None and "T05" not in R.shortlist(facts, ms)
    assert len(ms["T19"]["sector_marks"]) == 20


def test_roe_above_100_percent_is_left_out_of_quality_and_named():
    facts, sector = universe()
    facts["T10"] |= {"roe": 1.2}
    assert "Return on equity above 100%" in " ".join(R.caveats(facts["T10"], "EUR"))
    assert R.measures(facts, sector)["T10"]["quality"] == pytest.approx(0.5, abs=0.03)   # as the top ROE it would be 0.67


# ---- sentences ----------------------------------------------------------------------------------------------------

def test_the_case_states_facts_from_the_strongest_and_weakest_measures():
    facts, sector = universe()
    ms = R.measures(facts, sector)
    why, against = R.case("T00", facts, ms)
    assert len(why) == 2 and against == []                                           # best on everything: nothing argues against
    assert any("place 1 of 20" in s for s in why)
    why, against = R.case("T19", facts, ms)
    assert why == [] and len(against) == 2 and any("place 20 of 20" in s for s in against)
    assert R.sentence("value", "T00", facts, ms) == "P/E 10.0 against a middle of 25.0 over its last 4 fiscal year-ends"


def test_a_fact_always_points_the_same_way_as_its_heading():
    """A good overall quality rank built on low debt must not list a poor profit margin as a reason to look closer."""
    facts, sector = universe()
    facts["T10"] |= {"margin": -0.02, "roe": 0.5, "debt_equity": 1.0}          # worst margin, best return on equity and debt
    ms = R.measures(facts, sector)
    assert ms["T10"]["quality"] > 0.5
    good, bad = R.sentence("quality", "T10", facts, ms, True), R.sentence("quality", "T10", facts, ms, False)
    assert good.startswith(("Return on equity", "Debt to equity")) and "place 1 of 20" in good
    assert bad == "Profit margin \u22122%, place 20 of 20"
    assert R.sentence("trend", "T00", facts, ms, False) is None and R.sentence("trend", "T19", facts, ms, True) is None
    why, against = R.case("T10", facts, ms)
    assert not any("Profit margin" in s for s in why)


def test_caveats_follow_their_rules():
    grown = one(fund(pe=20.0, fwd=10.0, financialCurrency="USD"),
                {"eps": {"2025-12-31": 8.0, "2024-12-31": 4.0, "2023-12-31": 1.0}, "net_income": {"2025-12-31": 8.0, "2024-12-31": 4.0, "2023-12-31": 1.0}})
    text = " | ".join(R.caveats(grown, "EUR"))
    for part in ("grew 8-fold", "analyst estimates", "reports in USD and trades in EUR", "Only 3 fiscal years", "untested"):
        assert part in text
    assert R.caveats(one(), "EUR") == ["Fundamentals are current values, not what was known at past dates; the value and quality measures are untested"]
    assert "reports in" not in " ".join(R.caveats(one(fund(financialCurrency="GBP")), "GBp"))      # pence and pounds are one currency


def test_every_sentence_in_the_demo_output_passes_the_wording_check():
    data = json.loads((ROOT / "web" / "src" / "fixtures" / "research.json").read_text(encoding="utf-8"))
    for c in data["companies"]:
        for s in c["why"] + c["against"] + c["caveats"] + c["events"]:
            assert check_wording.scan_text(s) == [], s


def test_demo_research_covers_the_states_the_page_must_handle():
    data = json.loads((ROOT / "web" / "src" / "fixtures" / "research.json").read_text(encoding="utf-8"))
    by = {c["ticker"]: c for c in data["companies"]}
    assert by["NRDA.HE"]["gate"]["status"] == "fail" and by["FINC.HE"]["gate"]["status"] == "short"
    assert by["ENGA.OL"]["report_currency"] == "USD" and 5 < by["ENGA.OL"]["own_pes"][0]["pe"] < 60     # converted, not 10x off
    assert by["FINA.HE"]["inconsistent"] == ["fwd_pe"] and by["ENGB.MC"]["pe"] is None
    assert by["DEMD"]["headlines"] and "Headline in the last 2 days" in by["DEMD"]["events"]
    assert all(by[t]["place"] == i + 1 for i, t in enumerate(data["shortlist"])) and data["shortlist"]
    assert all(by[t]["gate"]["status"] == "pass" for t in data["shortlist"])


# ---- network layer, without the network ---------------------------------------------------------------------------

def test_headlines_keep_recent_items_and_only_web_links():
    items = [
        {"content": {"title": " Fresh news ", "pubDate": "2026-11-09T10:00:00Z", "provider": {"displayName": "Wire"},
                     "canonicalUrl": {"url": "https://example.com/a"}}},
        {"content": {"title": "Old news", "pubDate": "2026-05-13T10:00:00Z"}},
        {"title": "Flat format", "providerPublishTime": 1794300000, "publisher": "Desk", "link": "javascript:alert(1)"},
        {"content": {"title": "", "pubDate": "2026-11-09T10:00:00Z"}}, {"content": {"title": "No date"}},
    ]
    out = parse_headlines(items, date(2026, 11, 10))
    by = {h["title"]: h for h in out}
    assert sorted(by) == ["Flat format", "Fresh news"] and out == sorted(out, key=lambda h: h["days_old"])
    assert by["Fresh news"] == {"title": "Fresh news", "source": "Wire", "url": "https://example.com/a", "date": "2026-11-09", "days_old": 1}
    assert by["Flat format"]["url"] is None and by["Flat format"]["source"] == "Desk"      # a script link is dropped


def test_statements_are_cached_for_a_month_and_a_failed_fetch_keeps_the_old_entry(tmp_path):
    calls = []

    def fetch(t):
        calls.append(t)
        if t == "BAD":
            raise RuntimeError("down")
        return {"eps": {"2025-12-31": 1.0}}

    path = tmp_path / "statements.json"
    kw = {"fetch": fetch, "pace": 0, "sleep": lambda s: None}
    assert fetch_statements(["AAA", "BAD"], path, now=0.0, **kw) == {"AAA": {"eps": {"2025-12-31": 1.0}}}
    fetch_statements(["AAA", "BAD"], path, now=86400.0 * 10, **kw)
    assert calls == ["AAA", "BAD", "BAD"]                                           # AAA came from the cache
    fetch_statements(["AAA"], path, now=86400.0 * 31, **kw)
    assert calls[-1] == "AAA"                                                       # a month later it is fetched again
    path.write_text("{broken")
    assert fetch_statements(["AAA"], path, now=0.0, **kw) == {"AAA": {"eps": {"2025-12-31": 1.0}}}
