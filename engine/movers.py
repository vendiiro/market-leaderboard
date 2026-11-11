"""Daily movers across all watchlists and the dip alerts. Pure functions on leaderboard rows (one row per ticker)."""
from __future__ import annotations

from .leaderboard import UNTESTED

KEEP = ("ticker", "name", "lists", "currency", "last_bar", "ret_1d")


def movers(rows: list[dict], n: int = 10) -> dict:
    """{gainers, losers, alerts}. Stale rows and rows without a 1-day return are never listed. Gainers are the n
    largest positive 1-day returns, losers the n most negative; ties are broken by ticker. Alerts are the rows the
    copied dip rule flags, with its reasons; the rule is an untested screen rule and each alert says so."""
    live = [r for r in rows if not r["stale"]]
    moved = [r for r in live if r["ret_1d"] is not None]

    def pick(rs):
        return [{k: r[k] for k in KEEP} for r in rs[:n]]

    return {
        "gainers": pick(sorted((r for r in moved if r["ret_1d"] > 0), key=lambda r: (-r["ret_1d"], r["ticker"]))),
        "losers": pick(sorted((r for r in moved if r["ret_1d"] < 0), key=lambda r: (r["ret_1d"], r["ticker"]))),
        "alerts": [{k: r[k] for k in KEEP} | {"reasons": r["dip_reasons"], "label": UNTESTED, "q_passed": r["q_passed"],
                                               "q_scored": r["q_scored"]}
                   for r in sorted(live, key=lambda r: r["ticker"]) if r["dip"]],
    }
