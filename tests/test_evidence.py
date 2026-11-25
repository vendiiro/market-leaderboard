import numpy as np
import pandas as pd
import pytest

from engine.evidence import block_interval, monthly_panels, spreads, verdict

MONTHS = pd.period_range("2015-01", periods=96, freq="M")
RNG = np.random.default_rng(3)


def panel(effect: float, names: int = 30) -> tuple[pd.DataFrame, pd.DataFrame]:
    measure = pd.DataFrame(RNG.normal(0, 1, (len(MONTHS), names)), index=MONTHS, columns=[f"T{i}" for i in range(names)])
    outcome = effect * measure + RNG.normal(0, 0.3, measure.shape)
    return measure, outcome


def test_a_measure_that_drives_the_outcome_is_supported_and_noise_is_not():
    strong = verdict(spreads(*panel(0.2)))
    assert strong["status"] == "supported" and strong["lo"] > 0 and strong["months"] == 96
    noise = verdict(spreads(*panel(0.0)))
    assert noise["status"] == "not supported" and noise["lo"] < 0 < noise["hi"]
    assert verdict(spreads(*panel(-0.2)))["status"] == "not supported"            # the wrong sign is not support


def test_spread_is_top_third_minus_bottom_third_and_thin_months_are_skipped():
    measure = pd.DataFrame([list(range(12))], index=MONTHS[:1], columns=list("ABCDEFGHIJKL"), dtype=float)
    outcome = measure * 0.01
    assert spreads(measure, outcome).iloc[0] == pytest.approx(np.mean([0.08, 0.09, 0.10, 0.11]) - np.mean([0.0, 0.01, 0.02, 0.03]))
    outcome.iloc[0, 0] = np.nan                                                   # 11 companies left: below the minimum
    assert spreads(measure, outcome).empty


def test_interval_needs_two_blocks_and_is_reproducible():
    x = pd.Series(RNG.normal(0.02, 0.05, 60))
    assert block_interval(x) == block_interval(x) and block_interval(x)[0] < x.mean() < block_interval(x)[1]
    assert np.isnan(block_interval(x.iloc[:20])[0]) and verdict(x.iloc[:20])["status"] == "not supported"


def test_monthly_panels_start_after_three_years_and_stop_a_year_before_the_end():
    days = pd.bdate_range("2015-01-01", periods=1500)
    close = pd.Series(100 * 1.0005 ** np.arange(1500), index=days)
    p = monthly_panels(close, pd.Series(100.0, index=days))
    assert p["trend"].first_valid_index() == days[756].to_period("M") and p["outcome"].last_valid_index() < days[-252].to_period("M") + 1
    assert p["trend"].dropna().iloc[0] == pytest.approx(1.0005 ** 231 - 1) and (p["steady"].dropna() == 0).all()
    assert p["outcome"].dropna().iloc[0] == pytest.approx(1.0005 ** 252 - 1)
