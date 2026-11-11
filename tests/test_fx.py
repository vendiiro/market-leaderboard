import pytest

from engine.fx import fetch_fx_to_usd, usd_value

R = {"EUR": 1.1, "GBP": 1.3, "SEK": 0.1}


@pytest.mark.parametrize("amount, ccy, expected", [
    (100, "USD", 100), (100, "EUR", 110), (100, "SEK", 10),
    (100, "GBp", 1.3), (100, "GBX", 1.3),          # pence: 100p = 1 GBP
])
def test_usd_value(amount, ccy, expected):
    assert usd_value(amount, ccy, R) == pytest.approx(expected)


@pytest.mark.parametrize("amount, ccy", [(100, "NOK"), (100, None), (100, ""), (None, "EUR"), ("n/a", "EUR"), (float("nan"), "EUR")])
def test_usd_value_is_none_when_anything_is_unusable(amount, ccy):
    assert usd_value(amount, ccy, R) is None


def test_fetch_fx_asks_once_per_currency_and_skips_usd_and_failures():
    asked = []

    def fake(sym):
        asked.append(sym)
        return None if sym.startswith("NOK") else 0.5

    out = fetch_fx_to_usd(["USD", "EUR", "EUR", "NOK", None, "GBp"], fake)
    assert out == {"EUR": 0.5, "GBP": 0.5}
    assert sorted(asked) == ["EURUSD=X", "GBPUSD=X", "NOKUSD=X"]


# ---- EUR conversion (new in market-leaderboard) --------------------------------------------------------------
from engine.fx import eur_value, fx_history_eur  # noqa: E402

RU = {"EUR": 1.25, "GBP": 1.5, "SEK": 0.1}       # USD per 1 unit


@pytest.mark.parametrize("amount, ccy, expected", [
    (100, "USD", 80), (100, "EUR", 100), (100, "SEK", 8), (250, "GBp", 3.0), (250, "GBX", 3.0), (100, "GBP", 120),
])
def test_eur_value(amount, ccy, expected):
    assert eur_value(amount, ccy, RU) == pytest.approx(expected)


def test_eur_value_is_none_when_anything_is_unusable():
    assert eur_value(100, "NOK", RU) is None and eur_value(None, "USD", RU) is None and eur_value(100, None, RU) is None
    assert eur_value(100, "USD", {"SEK": 0.1}) is None        # no EUR rate: cannot cross
    assert eur_value(100, "EUR", {}) == 100                   # EUR needs no rate


def test_fx_history_eur_one_series_per_foreign_currency():
    import pandas as pd
    asked = []

    def fake(symbol, start):
        asked.append((symbol, start))
        return None if symbol.startswith("NOK") else pd.Series([0.9, 0.91], index=pd.to_datetime(["2026-01-02", "2026-01-05"]))

    out = fx_history_eur(["USD", "EUR", "GBp", "GBP", "NOK", None], "2026-01-01", fake)
    assert sorted(out) == ["GBP", "USD"] and out["USD"].iloc[-1] == 0.91      # pence map to GBP; EUR and failures omitted
    assert sorted(asked) == [("GBPEUR=X", "2026-01-01"), ("NOKEUR=X", "2026-01-01"), ("USDEUR=X", "2026-01-01")]
