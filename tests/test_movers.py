import importlib.util
from pathlib import Path

from engine.movers import movers

_spec = importlib.util.spec_from_file_location("check_wording", Path(__file__).resolve().parents[1] / "scripts" / "check_wording.py")
check_wording = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_wording)


def row(ticker, r1, stale=False, dip=False, lists=("eu_energy",)):
    return {"ticker": ticker, "name": f"{ticker} Corp", "lists": list(lists), "currency": "EUR", "last_bar": "2026-11-10",
            "ret_1d": r1, "stale": stale, "dip": dip, "dip_reasons": ["1-day −5.0% (rule: −4%)"] if dip else [],
            "q_passed": 4, "q_scored": 6}


ROWS = [row("UP2", 0.02), row("UP1", 0.02), row("BIG", 0.05, lists=("eu_energy", "nordic_energy")), row("FLAT", 0.0),
        row("DOWN", -0.05, dip=True), row("WORSE", -0.07), row("OLD", 0.30, stale=True), row("OLDDIP", -0.30, stale=True, dip=True),
        row("NODATA", None)]


def test_gainers_and_losers_are_ordered_with_ties_by_ticker():
    m = movers(ROWS)
    assert [r["ticker"] for r in m["gainers"]] == ["BIG", "UP1", "UP2"]
    assert [r["ticker"] for r in m["losers"]] == ["WORSE", "DOWN"]
    assert [r["ticker"] for r in movers(ROWS, n=1)["gainers"]] == ["BIG"]


def test_stale_flat_and_missing_rows_are_not_movers():
    listed = {r["ticker"] for k in ("gainers", "losers", "alerts") for r in movers(ROWS)[k]}
    assert listed.isdisjoint({"OLD", "OLDDIP", "FLAT", "NODATA"})


def test_a_ticker_on_two_lists_appears_once_with_both_lists():
    big = [r for r in movers(ROWS)["gainers"] if r["ticker"] == "BIG"]
    assert len(big) == 1 and big[0]["lists"] == ["eu_energy", "nordic_energy"]


def test_alerts_carry_reasons_the_untested_label_and_pass_the_wording_check():
    alerts = movers(ROWS)["alerts"]
    assert [a["ticker"] for a in alerts] == ["DOWN"]
    assert alerts[0]["label"] == "untested screen rule" and alerts[0]["reasons"] == ["1-day −5.0% (rule: −4%)"]
    assert check_wording.scan_text(" ".join(alerts[0]["reasons"] + [alerts[0]["label"]])) == []


def test_nothing_moved_gives_empty_lists():
    assert movers([row("FLAT", 0.0)]) == {"gainers": [], "losers": [], "alerts": []}
