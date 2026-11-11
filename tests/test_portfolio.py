import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine.portfolio import (correlation, covariance, effective_n, eur_prices, exposure, portfolio_vol,
                              reference_mixes, risk_contribution, weekly_eur_returns)

ASOF = date(2026, 11, 6)                       # a Friday
DAYS = pd.bdate_range(end="2026-11-06", periods=800)
RNG = np.random.default_rng(7)
FIXTURE = Path(__file__).resolve().parents[1] / "web" / "src" / "fixtures" / "mix_reference.json"


def walk(scale=0.01, n=800):
    return pd.Series(100 * np.exp(np.cumsum(RNG.normal(0, scale, n))), index=DAYS[-n:])


def cov2(v1, v2, rho):
    return pd.DataFrame([[v1 * v1, rho * v1 * v2], [rho * v1 * v2, v2 * v2]], index=["A", "B"], columns=["A", "B"])


# ---- weekly EUR returns --------------------------------------------------------------------------------------

def test_a_flat_usd_price_moves_in_eur_when_the_dollar_moves():
    flat_usd = pd.Series(100.0, index=DAYS)
    usdeur = pd.Series(np.linspace(0.80, 0.95, len(DAYS)), index=DAYS)
    weekly, reasons = weekly_eur_returns({"US": flat_usd, "FI": flat_usd}, {"US": "USD", "FI": "EUR"}, {"USD": usdeur}, ASOF)
    assert reasons == {} and weekly.shape == (104, 2)
    assert (weekly["US"] > 0).all() and (weekly["FI"] == 0).all()
    assert weekly.index[-1] == pd.Timestamp("2026-11-06") and weekly.index[0] == pd.Timestamp("2024-11-15")


def test_pence_prices_use_the_pound_rate_divided_by_100():
    eur = eur_prices(pd.Series(250.0, index=DAYS[-5:]), "GBp", {"GBP": pd.Series(1.2, index=DAYS)})
    assert eur.tolist() == pytest.approx([3.0] * 5)


def test_fx_gaps_are_filled_for_at_most_three_days():
    rate = pd.Series(1.0, index=DAYS).drop(DAYS[-6:-1])                 # five business days without a rate
    eur = eur_prices(pd.Series(10.0, index=DAYS[-8:]), "USD", {"USD": rate})
    assert len(eur) == 6                                                # 2 before the gap, 3 filled, 1 after


def test_short_history_missing_fx_and_the_current_partial_week():
    prices = {"OK": walk(), "SHORT": walk(n=103 * 5 + 2), "NOFX": walk()}
    weekly, reasons = weekly_eur_returns(prices, {"OK": "EUR", "SHORT": "EUR", "NOFX": "SEK"}, {}, ASOF)
    assert list(weekly.columns) == ["OK"]
    assert "103 of 104 weekly returns" in reasons["SHORT"] and "SEK" in reasons["NOFX"]
    midweek, _ = weekly_eur_returns({"OK": prices["OK"]}, {"OK": "EUR"}, {}, date(2026, 11, 4))   # a Wednesday
    assert midweek.index[-1] == pd.Timestamp("2026-10-30")              # the unfinished week is not used


def test_covariance_is_symmetric_and_positive_semi_definite_even_with_more_names_than_weeks():
    weekly = pd.DataFrame(RNG.normal(0, 0.03, (104, 120)), columns=[f"T{i}" for i in range(120)])
    cov = covariance(weekly)
    assert np.allclose(cov, cov.T) and np.linalg.eigvalsh(cov.to_numpy()).min() >= -1e-12
    assert cov.iloc[0, 0] == pytest.approx(weekly["T0"].var() * 52)
    corr = correlation(cov)
    assert np.allclose(np.diag(corr), 1) and corr.to_numpy().max() <= 1 + 1e-12


# ---- the four formulas ---------------------------------------------------------------------------------------

def test_one_name_mix_has_that_names_volatility():
    assert portfolio_vol({"A": 5}, pd.DataFrame([[0.09]], index=["A"], columns=["A"])) == pytest.approx(0.30)


def test_perfectly_correlated_and_uncorrelated_pairs():
    assert portfolio_vol({"A": 0.25, "B": 0.75}, cov2(0.3, 0.2, 1.0)) == pytest.approx(0.25 * 0.3 + 0.75 * 0.2)
    assert portfolio_vol({"A": 1, "B": 1}, cov2(0.2, 0.2, 0.0)) == pytest.approx(0.2 / 2 ** 0.5)


def test_the_worked_check_from_the_spec():
    w, cov = {"A": 0.6, "B": 0.4}, cov2(0.30, 0.20, 0.5)
    assert portfolio_vol(w, cov) == pytest.approx(0.230651, abs=1e-6)
    rc = risk_contribution(w, cov)
    assert rc["A"] == pytest.approx(0.744361, abs=1e-6) and rc["B"] == pytest.approx(0.255639, abs=1e-6)
    assert sum(rc.values()) == pytest.approx(1) and effective_n(w) == pytest.approx(1.923077, abs=1e-6)


def test_weights_are_normalised_and_bad_weights_rejected():
    assert effective_n({"A": 2, "B": 2, "C": 2, "D": 2}) == pytest.approx(4)
    assert portfolio_vol({"A": 60, "B": 40}, cov2(0.3, 0.2, 0.5)) == pytest.approx(0.230651, abs=1e-6)
    for bad in ({"A": 0, "B": 0}, {"A": 2, "B": -1}):
        with pytest.raises(ValueError):
            effective_n(bad)


def test_exposure_sums_to_one_and_a_two_list_name_counts_on_both():
    meta = reference_mixes()["meta"]
    w = {"AAA": 50, "BBB": 30, "CCC": 20}
    assert exposure(w, meta, "sector") == pytest.approx({"Technology": 0.5, "Energy": 0.5})
    assert sum(exposure(w, meta, "country").values()) == pytest.approx(1)
    assert exposure(w, meta, "lists") == pytest.approx({"us_big_tech": 0.5, "eu_energy": 0.3, "nordic_energy": 0.5})


def test_the_typescript_fixture_is_current():
    """web/src/fixtures/mix_reference.json must equal reference_mixes(); regenerate with
    uv run python -c "import json; from engine.portfolio import reference_mixes; print(json.dumps(reference_mixes(), indent=1))" """
    def same(x, y):                      # floats differ in the last bit between machines (linear algebra library)
        if isinstance(x, dict):
            return isinstance(y, dict) and x.keys() == y.keys() and all(same(x[k], y[k]) for k in x)
        if isinstance(x, list):
            return isinstance(y, list) and len(x) == len(y) and all(same(i, j) for i, j in zip(x, y))
        return x == pytest.approx(y, abs=1e-12) if isinstance(x, float) else x == y

    assert same(json.loads(FIXTURE.read_text(encoding="utf-8")), json.loads(json.dumps(reference_mixes())))
