from datetime import date

import pandas as pd

from engine.evidence import spreads
from engine.newsbacktest import MIN_STORIES, measures, month_bounds, month_counts, month_ends, month_url, next_month_returns

P = pd.Period


def test_months_and_url_cover_exactly_one_calendar_month():
    ms = month_ends("2024-01", "2024-03")
    assert [str(m) for m in ms] == ["2024-01", "2024-02", "2024-03"]
    assert month_bounds(P("2024-02")) == (date(2024, 2, 1), date(2024, 2, 29))
    u = month_url("Acme Corp", "ACME.HE", date(2024, 2, 1), date(2024, 2, 29))
    assert "after%3A2024-02-01" in u and "before%3A2024-03-01" in u and "ACME" in u and ".HE" not in u


def test_month_counts_use_the_live_tone_function():
    items = [{"title": t} for t in ("Acme wins new contract", "Acme shares plunge", "Acme CEO interview", "Acme record revenue")]
    assert month_counts(items) == {"n": 4, "up": 2, "down": 1}


def test_measures_apply_the_pre_registered_eligibility():
    m = P("2024-01")
    counts = {
        "A": {m: {"n": 6, "up": 3, "down": 1}},     # counts for both
        "B": {m: {"n": MIN_STORIES - 1, "up": 3, "down": 0}},   # too few stories: neither
        "C": {m: {"n": 8, "up": 1, "down": 0}},     # share yes, balance no (only 1 toned story)
    }
    out = measures(counts)
    assert out["upbeat_share"].loc[m].dropna().to_dict() == {"A": 0.5, "C": 0.125}
    assert out["balance"].loc[m].dropna().to_dict() == {"A": 0.5}


def test_next_month_return_is_month_end_to_month_end():
    idx = pd.to_datetime(["2024-01-30", "2024-01-31", "2024-02-28", "2024-02-29", "2024-03-29"])
    r = next_month_returns(pd.Series([90.0, 100.0, 105.0, 110.0, 99.0], index=idx))
    assert abs(r.loc[P("2024-01")] - 0.10) < 1e-12 and abs(r.loc[P("2024-02")] - (-0.1)) < 1e-12 and P("2024-03") not in r.index


def test_a_measure_that_ranks_winners_first_gives_a_positive_spread():
    months = [P("2024-01") + i for i in range(3)]
    tick = [f"T{i}" for i in range(12)]
    measure = pd.DataFrame({t: {m: float(i) for m in months} for i, t in enumerate(tick)})
    outcome = pd.DataFrame({t: {m: i / 100 for m in months} for i, t in enumerate(tick)})
    s = spreads(measure, outcome)
    assert len(s) == 3 and (s > 0).all()
