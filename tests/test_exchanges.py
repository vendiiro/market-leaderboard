# Copied from dip-dashboard tests/test_exchanges.py at commit f14d55c: only the registry tests (views of other modules not copied).
"""Exchange registry."""
from engine.exchanges import suffix_of


def test_suffix_of():
    assert suffix_of("AAPL") == ""
    assert suffix_of("BRK-B") == ""
    assert suffix_of("NOKIA.HE") == ".HE"
    assert suffix_of("nokia.he") == ".HE"




def test_london_trades_in_pence_and_unknown_suffix_is_none():
    from engine.exchanges import exchange_for
    assert exchange_for("SHEL.L").currency == "GBp"
    assert exchange_for("AAPL").currency == "USD" and exchange_for("X.ZZ") is None
