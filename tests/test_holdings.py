from pathlib import Path

import pytest

from engine import holdings as H

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "config" / "portfolio.example.toml"

GOOD = """
label = "Test"
[[holding]]
ticker = "AAA"
name = "Alpha"
kind = "stock"
quantity = 10
cost_price = 5.0
"""


def write(tmp_path, text):
    p = tmp_path / "portfolio.toml"
    p.write_text(text, encoding="utf-8")
    return p


# ---- Task 1: the file reader -------------------------------------------------------------------------------

def test_reads_the_example_file():
    h = H.read_holdings(EXAMPLE)
    assert h is not None and h.label
    by_kind = {}
    for x in h.holdings:
        by_kind.setdefault(x.kind, []).append(x)
    assert any(x.cost_eur_total is not None for x in by_kind["stock"])
    assert by_kind["etf"]
    fund = by_kind["fund"][0]
    assert fund.ticker is None and fund.value_eur is not None
    assert len({x.ticker for x in h.holdings if x.ticker}) == len([x for x in h.holdings if x.ticker])


def test_missing_default_file_is_none(tmp_path, monkeypatch):
    monkeypatch.setattr(H, "DEFAULT_PATH", tmp_path / "nope.toml")
    assert H.read_holdings() is None


def test_explicit_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        H.read_holdings(tmp_path / "nope.toml")


def test_reads_one_holding_and_history_path(tmp_path):
    p = write(tmp_path, 'history_csv = "x.csv"\n' + GOOD)       # a top-level key must come before the first [[holding]]
    h = H.read_holdings(p)
    assert h.holdings[0] == H.Holding(name="Alpha", kind="stock", ticker="AAA", quantity=10, cost_price=5.0,
                                      cost_eur_total=None, value_eur=None, group=None)
    assert h.history_csv == Path("x.csv")


@pytest.mark.parametrize("body, message", [
    ('[[holding]]\nticker="A"\nname="A"\nkind="bond"\nquantity=1\ncost_price=1\n', "kind"),
    ('[[holding]]\nticker="A"\nname="A"\nkind="stock"\nquantity=1\ncost_price=1\n'
     '[[holding]]\nticker="A"\nname="B"\nkind="stock"\nquantity=1\ncost_price=1\n', "duplicate"),
    ('[[holding]]\nticker="A"\nname="A"\nkind="stock"\ncost_price=1\n', "quantity"),
    ('[[holding]]\nticker="A"\nname="A"\nkind="stock"\nquantity=1\n', "cost_price"),
    ('[[holding]]\nname="F"\nkind="fund"\n', "value_eur"),
    ('[[holding]]\nticker="A"\nname="A"\nkind="stock"\nquantity=-1\ncost_price=1\n', "quantity"),
    ('[[holding]]\nticker="A"\nname="A"\nkind="stock"\nquantity=1\ncost_price=1\nbogus=2\n', "bogus"),
])
def test_rejects_bad_files(tmp_path, body, message):
    with pytest.raises(ValueError, match=message) as e:
        H.read_holdings(write(tmp_path, 'label = "T"\n' + body))
    assert "portfolio.toml" in str(e.value)


# ---- Task 4: positions, totals, ETF rows, the basket reference ---------------------------------------------

import math  # noqa: E402

import pandas as pd  # noqa: E402

from synth import dates, flat, geometric  # noqa: E402


def fxs(**rates):
    return {c: pd.Series([r] * 260, index=dates(260)) for c, r in rates.items()}


def hold(**kw):
    base = dict(name="A", kind="stock", ticker="AAA", quantity=10.0, cost_price=40.0, cost_eur_total=None,
                value_eur=None, group=None)
    return H.Holding(**{**base, **kw})


def rows_for(items, prices, currency, fx, risk=()):
    h = H.Holdings(label="t", holdings=list(items), history_csv=None)
    return H.position_rows(h, prices, currency, {}, fx, set(risk))


def test_usd_holding_value_uses_the_eur_rate():
    [r] = rows_for([hold()], {"AAA": flat(260, 50.0)}, {"AAA": "USD"}, fxs(USD=0.9))
    assert r["value_eur"] == pytest.approx(450.0) and r["price"] == 50.0
    assert r["return_local"] == pytest.approx(0.25) and r["weight"] == pytest.approx(1.0) and r["note"] is None


def test_gbp_pence_holding():
    [r] = rows_for([hold(cost_price=800.0)], {"AAA": flat(260, 1000.0)}, {"AAA": "GBp"}, fxs(GBP=1.2))
    assert r["value_eur"] == pytest.approx(120.0)             # 10 x 1000 pence x 1.2 / 100
    assert r["cost_eur"] == pytest.approx(96.0) and r["result_eur"] == pytest.approx(24.0)


def test_cost_eur_total_wins_and_is_not_approximate():
    [r] = rows_for([hold(cost_eur_total=380.0)], {"AAA": flat(260, 50.0)}, {"AAA": "USD"}, fxs(USD=0.9))
    assert r["cost_eur"] == 380.0 and r["cost_approx"] is False and r["result_eur"] == pytest.approx(70.0)


def test_cost_is_approximate_without_cost_eur_total():
    [r] = rows_for([hold()], {"AAA": flat(260, 50.0)}, {"AAA": "USD"}, fxs(USD=0.9))
    assert r["cost_eur"] == pytest.approx(360.0) and r["cost_approx"] is True and r["result_eur"] == pytest.approx(90.0)


def test_fund_with_manual_value_counts_in_value_not_in_risk():
    fund = hold(name="Fund", kind="fund", ticker=None, quantity=None, cost_price=None, value_eur=300.0)
    [r] = rows_for([fund], {}, {}, {})
    assert r["key"] == "fund:Fund" and r["value_eur"] == 300.0 and r["has_risk"] is False
    assert r["cost_eur"] is None and r["result_eur"] is None and r["return_local"] is None


def test_unpriced_holding_is_left_out_of_totals():
    rows = rows_for([hold(), hold(name="B", ticker="BBB")], {"AAA": flat(260, 50.0)}, {"AAA": "USD", "BBB": "USD"},
                    fxs(USD=0.9), risk={"AAA"})
    a, b = rows
    assert b["value_eur"] is None and b["weight"] is None and b["note"] == "no price tonight" and b["has_risk"] is False
    t = H.totals(rows)
    assert t["unpriced"] == 1 and t["value_eur"] == pytest.approx(450.0) and a["weight"] == pytest.approx(1.0)


def test_totals_top3_tech_and_risk_share():
    def p(key, value, group=None, risk=True, result=None, kind="stock"):
        return {"key": key, "value_eur": value, "group": group, "has_risk": risk, "result_eur": result, "kind": kind}
    rows = [p("a", 400.0, "technology", result=40.0), p("b", 300.0, result=-10.0), p("c", 200.0, risk=False, result=5.0),
            p("d", 100.0, "technology", result=1.0), p("e", None, result=None)]
    t = H.totals(rows)
    assert t["value_eur"] == 1000.0 and t["result_eur"] == pytest.approx(36.0) and t["unpriced"] == 1
    assert t["top3_share"] == pytest.approx(0.9) and t["tech_share"] == pytest.approx(0.5)
    assert t["risk_covered"] == pytest.approx(0.8) and t["result_complete"] is False   # "e" is a priced-less stock


def test_totals_of_nothing_are_zero_not_nan():
    t = H.totals([])
    assert t["value_eur"] == 0.0 and t["top3_share"] == 0.0 and t["result_eur"] is None and t["unpriced"] == 0


CFG_ETF = {"etf_core": {"name": "Core", "kind": "etf", "tickers": {"E1": "One", "E2": "Two"}, "groups": {"E1": "technology"}}}


def test_etf_rows_full_and_short_history():
    prices = {"E1": (geometric(300, 0.0005), None), "E2": (geometric(30, 0.0005), None)}
    rows = {r["ticker"]: r for r in H.etf_rows(CFG_ETF, prices, {"E1": "EUR", "E2": "EUR"})}
    assert rows["E1"]["list"] == "etf_core" and rows["E1"]["group"] == "technology" and rows["E1"]["ret_1y"] > 0
    assert rows["E1"]["vol_1y"] is not None and rows["E1"]["dd52"] is not None
    assert rows["E2"]["price"] is None and rows["E2"]["ret_1y"] is None and rows["E2"]["vol_1y"] is None


def test_etf_without_prices_has_empty_metrics():
    [r] = H.etf_rows({"x": {"name": "X", "kind": "etf", "tickers": {"E3": "Three"}, "groups": {}}}, {}, {})
    assert r["price"] is None and r["group"] is None


def test_reference_baskets_are_self_consistent():
    ref = H.reference_baskets()
    first = ref["baskets"][0]
    assert first["items"] == [] and first["expected"]["total"] == pytest.approx(1000.0)
    for b in ref["baskets"]:
        e = b["expected"]
        assert sum(e["weights"].values()) == pytest.approx(1.0) and math.isfinite(e["vol"])
        assert 0 < e["volCovered"] <= 1
    # one risky name only: its vol equals its own volatility (AAA 0.30)
    solo = H.evaluate_basket([{"key": "AAA", "ticker": "AAA", "value_eur": 100.0, "group": None}], {}, H._reference_cov(), set())
    assert solo["vol"] == pytest.approx(0.30)
