# Copied from dip-dashboard tests/test_exchanges.py at commit f14d55c: only the registry tests (views of other modules not copied).
"""Exchange registry."""
from engine.exchanges import suffix_of


def test_suffix_of():
    assert suffix_of("AAPL") == ""
    assert suffix_of("BRK-B") == ""
    assert suffix_of("NOKIA.HE") == ".HE"
    assert suffix_of("nokia.he") == ".HE"


