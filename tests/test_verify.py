# Adapted from dip-dashboard tests/test_universe.py at commit f14d55c (the pure-logic tests of the row check).
from datetime import date

from engine import verify as vu

TODAY = date(2026, 11, 4)  # a Wednesday
RATES = {"EUR": 1.1, "SEK": 0.1}
OK_INFO = {"longName": "Apple Inc.", "quoteType": "EQUITY", "exchange": "NMS", "currency": "USD", "marketCap": 3e12}
OK_BARS = {"first": date(2021, 11, 4), "last": date(2026, 11, 3), "count": 1250}


def classify(ticker="AAPL", name="Apple", info=OK_INFO, bars=OK_BARS, **kw):
    kw.setdefault("rates", RATES)
    return vu.classify_row(ticker, name, info, bars, TODAY, **kw)


def test_ok_row():
    r = classify()
    assert r["status"] == "ok" and r["market_cap_eur"] == round(3e12 / 1.1) and r["bar_count"] == 1250


def test_every_status_value_can_be_produced():
    produced = {
        "ok": classify(),
        "no_bars": classify(bars={}),
        "few_bars": classify(bars={**OK_BARS, "count": 249}),
        "stale": classify(bars={**OK_BARS, "last": date(2026, 10, 20)}),
        "not_equity": classify(info={**OK_INFO, "quoteType": "ETF"}),
        "name_mismatch": classify(name="Zzzz Qqqq"),
        "currency_mismatch": classify(info={**OK_INFO, "currency": "EUR"}),
        "under_cap": classify(info={**OK_INFO, "marketCap": 5e9}, min_cap_eur=20e9),
        "fetch_error": classify(info=None, bars=None),
    }
    assert set(produced) == set(vu.STATUSES)
    for status, row in produced.items():
        assert status in row["status"].split(";"), (status, row["status"])
    assert produced["ok"]["status"] == "ok"


def test_flags_are_joined_with_semicolons():
    r = classify(info={**OK_INFO, "quoteType": "ETF", "marketCap": 1e9}, bars={}, min_cap_eur=20e9)
    assert set(r["status"].split(";")) == {"not_equity", "under_cap", "no_bars"}


def test_no_size_check_by_default_and_missing_cap_is_not_a_flag():
    assert classify(info={**OK_INFO, "marketCap": 5e9})["status"] == "ok"
    r = classify("SAP.DE", "SAP", {**OK_INFO, "longName": "SAP SE", "currency": "EUR", "marketCap": 15e9})
    assert r["market_cap_eur"] == 15_000_000_000 and r["status"] == "ok"
    r = classify(info={**OK_INFO, "marketCap": None})
    assert r["status"] == "ok" and "market cap unavailable" in r["detail"]


def test_unknown_exchange_suffix_is_flagged():
    r = classify("XXX.ZZ", "Apple")
    assert r["status"] == "currency_mismatch" and "not in the registry" in r["detail"]


def test_name_score_threshold():
    assert vu.name_score("Apple", "Apple Inc.") == 1.0
    assert vu.name_score("Mercedes-Benz", "Mercedes-Benz Group AG") == 1.0
    assert vu.name_score("Apple", "Banana Republic") < 0.6


UK_INFO = {"longName": "Shell plc", "quoteType": "EQUITY", "exchange": "LSE", "currency": "GBp", "marketCap": 110e9}


def test_london_ticker_must_report_pence():
    r = classify("SHEL.L", "Shell", UK_INFO, rates={"EUR": 1.1, "GBP": 1.32})
    assert r["status"] == "ok" and r["market_cap_eur"] == 132_000_000_000     # marketCap is in pounds, not pence
    assert classify("SHEL.L", "Shell", {**UK_INFO, "currency": "GBX"})["status"] == "ok"
    assert classify("SHEL.L", "Shell", {**UK_INFO, "currency": "USD"})["status"] == "currency_mismatch"


def test_market_cap_is_reported_in_eur():
    r = classify("AAPL", "Apple", {**OK_INFO, "marketCap": 110e9})
    assert r["market_cap_eur"] == 100_000_000_000          # 110B USD at 1.1 USD per EUR
    assert classify("SAP.DE", "SAP", {**OK_INFO, "longName": "SAP SE", "currency": "EUR", "marketCap": 15e9})["market_cap_eur"] == 15e9
    assert "under_cap" in classify(info={**OK_INFO, "marketCap": 110e9}, min_cap_eur=200e9)["status"]
