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
