"""holdings.json, the ETF candidates and the covariance extension (docs/superpowers/specs/2026-11-15-portfolio-page-design.md).
All demo data is invented; nothing here reads config/portfolio.toml."""
import json
from pathlib import Path

import pytest

from engine import build as B
from engine import demo
from engine import holdings as H

ROOT = Path(__file__).resolve().parents[1]


def read(folder, stem):
    return json.loads((folder / f"{stem}.json").read_text(encoding="utf-8"))


@pytest.fixture()
def out(tmp_path):
    assert B.build(tmp_path, is_demo=True) == 0
    return tmp_path


def test_holdings_json_tells_the_demo_story(out):
    h = read(out, "holdings")
    pos = {p["key"]: p for p in h["positions"]}
    assert pos["DEMA"]["value_eur"] > 0 and pos["DEMA"]["cost_approx"] is False and pos["DEMA"]["has_risk"] is True
    assert pos["DEFA.DE"]["cost_approx"] is True
    assert pos["DEMETF.DE"]["kind"] == "etf" and pos["DEMETF.DE"]["value_eur"] > 0
    assert pos["fund:Demo Balanced Fund"]["value_eur"] == 300.0 and pos["fund:Demo Balanced Fund"]["has_risk"] is False
    assert pos["DEMX.HE"]["value_eur"] is None and pos["DEMX.HE"]["note"] == "no price tonight"
    assert h["totals"]["unpriced"] == 1 and h["totals"]["value_eur"] > 0
    assert abs(sum(p["weight"] for p in h["positions"] if p["weight"] is not None) - 1) < 1e-9
    assert h["history_note"] is None and {"since_start", "month", "ytd", "max_drawdown"} <= set(h["history"]["summary"])
    assert h["history"]["points"][-1]["date"] <= demo.END


def test_etf_rows_are_in_holdings_json_and_not_in_the_share_files(out):
    h = read(out, "holdings")
    etfs = {e["ticker"]: e for e in h["etfs"]}
    assert set(etfs) == {"DEMETF.DE", "DEMETG.DE"} and etfs["DEMETF.DE"]["group"] == "technology"
    assert etfs["DEMETF.DE"]["ret_1y"] is not None and etfs["DEMETG.DE"]["vol_1y"] is not None
    shares = json.dumps([read(out, "leaderboard"), read(out, "research"), read(out, "movers"), read(out, "meta")])
    for t in ("DEMETF.DE", "DEMETG.DE", "DEMX.HE"):
        assert t not in shares, t
    assert [x["key"] for x in read(out, "leaderboard")["lists"]] == list(demo.LISTS)


def test_extras_are_in_the_covariance_matrix_or_have_a_reason(out):
    p = read(out, "portfolio")
    assert "DEMETF.DE" in p["risk_tickers"] and "DEMETG.DE" not in p["risk_tickers"]
    assert any(x["ticker"] == "DEMETG.DE" and "weekly returns" in x["reason"] for x in p["no_risk_data"])
    entries = {t["ticker"]: t for t in p["tickers"]}
    assert entries["DEMETF.DE"]["lists"] == ["etf_core", "holdings"] and entries["DEMETG.DE"]["vol_eur"] is None
    assert "DEMX.HE" not in entries                                   # no prices at all: not in the matrix


def test_a_ticker_on_a_watchlist_and_in_holdings_appears_once(out):
    p = read(out, "portfolio")
    assert [t["ticker"] for t in p["tickers"]].count("DEMA") == 1
    assert next(t for t in p["tickers"] if t["ticker"] == "DEMA")["lists"] == ["us_big_tech"]


def test_missing_history_does_not_fail_the_build(tmp_path):
    inputs = demo.inputs()
    inputs["history"], inputs["history_note"] = None, "Nordnet history file: export.csv is empty"
    assert B.build(tmp_path, is_demo=True, inputs=inputs) == 0
    h = read(tmp_path, "holdings")
    assert h["history"] is None and "empty" in h["history_note"]


def test_no_holdings_file_writes_an_empty_holdings_json(tmp_path):
    inputs = demo.inputs()
    inputs["holdings"], inputs["history"] = None, None
    assert B.build(tmp_path, is_demo=True, inputs=inputs) == 0
    h = read(tmp_path, "holdings")
    assert h["positions"] == [] and h["totals"]["value_eur"] == 0.0 and h["history"] is None


def test_basket_reference_fixture_is_current():
    """web/src/fixtures/basket_reference.json must equal reference_baskets(); regenerate with
    uv run python -m engine.holdings"""
    fixture = json.loads((ROOT / "web" / "src" / "fixtures" / "basket_reference.json").read_text(encoding="utf-8"))
    assert fixture == json.loads(json.dumps(H.reference_baskets()))


def test_etf_and_holding_prices_do_not_change_the_share_research():
    """ETFs and holding-only tickers must never act as peers: the share views must equal a build without them."""
    from datetime import date
    from engine.config import load_settings
    full, bare = demo.inputs(), demo.inputs()
    for t in ("DEMETF.DE", "DEMETG.DE"):
        del bare["prices"][t]
    bare["extra"], bare["holdings"], bare["history"] = {}, None, None
    a = B.compute(full, load_settings(), date.fromisoformat(demo.END), built_at="x", is_demo=True)
    b = B.compute(bare, load_settings(), date.fromisoformat(demo.END), built_at="x", is_demo=True)
    for stem in ("research", "leaderboard", "movers"):
        assert a[stem] == b[stem], stem
