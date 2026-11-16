"""The owner's holdings: the private file reader, position and total maths, ETF rows and the basket reference fixture.

The holdings file (config/portfolio.toml) is private and gitignored: the repository is public. Tests and the demo use
config/portfolio.example.toml, which holds invented values. Educational research tool: nothing here is advice."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config import CONFIG_DIR
from .metrics import compute_metrics
from .portfolio import eur_prices, portfolio_vol, risk_contribution
from .returns import windows

DEFAULT_PATH = CONFIG_DIR / "portfolio.toml"
KINDS = ("stock", "etf", "etn", "fund")
_TOP_KEYS = {"label", "history_csv", "holding"}
_HOLDING_KEYS = {"name", "kind", "ticker", "quantity", "cost_price", "cost_eur_total", "value_eur", "group"}


@dataclass(frozen=True)
class Holding:
    name: str
    kind: str                       # one of KINDS
    ticker: str | None              # Yahoo ticker; None for a fund without one
    quantity: float | None
    cost_price: float | None        # per unit, in the quote currency
    cost_eur_total: float | None    # optional: the EUR cost from the broker's report
    value_eur: float | None         # manual value, for a fund without a Yahoo ticker
    group: str | None               # owner's free-text tag, for example "technology"


@dataclass(frozen=True)
class Holdings:
    label: str
    holdings: list[Holding]
    history_csv: Path | None


def _number(raw: dict, key: str, where: str, *, positive: bool = True) -> float | None:
    if key not in raw:
        return None
    v = raw[key]
    if isinstance(v, bool) or not isinstance(v, (int, float)) or (positive and v <= 0) or v < 0:
        raise ValueError(f"{where}: {key} must be a number above zero" if positive else f"{where}: {key} must be a number")
    return float(v)


def _holding(raw: dict, n: int, file: str) -> Holding:
    name = raw.get("name")
    where = f"{file} holding {n}" + (f" ({name})" if isinstance(name, str) else "")
    unknown = set(raw) - _HOLDING_KEYS
    if unknown:
        raise ValueError(f"{where}: unknown key(s) {sorted(unknown)}; expected {sorted(_HOLDING_KEYS)}")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"{where}: needs a name")
    kind = raw.get("kind")
    if kind not in KINDS:
        raise ValueError(f"{where}: kind must be one of {list(KINDS)}, got {kind!r}")
    ticker = raw.get("ticker")
    if ticker is not None and (not isinstance(ticker, str) or not ticker.strip()):
        raise ValueError(f"{where}: ticker must be text")
    qty, cost = _number(raw, "quantity", where), _number(raw, "cost_price", where)
    cost_eur, value = _number(raw, "cost_eur_total", where), _number(raw, "value_eur", where)
    if ticker is None:
        if kind != "fund" or value is None:
            raise ValueError(f"{where}: a holding without a ticker must be a fund with value_eur")
    else:
        if qty is None:
            raise ValueError(f"{where}: quantity is required when there is a ticker")
        if cost is None:
            raise ValueError(f"{where}: cost_price is required when there is a ticker")
    group = raw.get("group")
    if group is not None and not isinstance(group, str):
        raise ValueError(f"{where}: group must be text")
    return Holding(name=name, kind=kind, ticker=ticker, quantity=qty, cost_price=cost, cost_eur_total=cost_eur,
                   value_eur=value, group=group)


def read_holdings(path: Path | str | None = None) -> Holdings | None:
    """The holdings file, or None when the default file does not exist (the build then has no portfolio).
    A path given explicitly that does not exist raises FileNotFoundError."""
    explicit = path is not None
    p = Path(path) if explicit else DEFAULT_PATH
    if not p.exists():
        if explicit:
            raise FileNotFoundError(p)
        return None
    raw = tomllib.loads(p.read_text(encoding="utf-8"))
    unknown = set(raw) - _TOP_KEYS
    if unknown:
        raise ValueError(f"{p.name}: unknown key(s) {sorted(unknown)}; expected {sorted(_TOP_KEYS)}")
    items = [_holding(r, i + 1, p.name) for i, r in enumerate(raw.get("holding", []))]
    seen: set[str] = set()
    for h in items:
        if h.ticker:
            if h.ticker in seen:
                raise ValueError(f"{p.name}: duplicate ticker {h.ticker}")
            seen.add(h.ticker)
    hist = raw.get("history_csv")
    return Holdings(label=str(raw.get("label") or "Portfolio"), holdings=items, history_csv=Path(hist) if hist else None)


# ---- positions, totals, ETF rows -----------------------------------------------------------------------------

def _empty_position(h: Holding, key: str, **kw) -> dict:
    base = {"key": key, "ticker": h.ticker, "name": h.name, "kind": h.kind, "group": h.group, "currency": None,
            "sector": None, "quantity": h.quantity, "price": None, "value_eur": None, "cost_eur": None,
            "cost_approx": False, "result_eur": None, "return_local": None, "weight": None, "has_risk": False,
            "note": None}
    return base | kw


def position_rows(h: Holdings, prices: dict[str, pd.Series], currency: dict[str, str | None],
                  sector: dict[str, str | None], fx: dict[str, pd.Series], risk_tickers: set[str]) -> list[dict]:
    """One row per holding, in file order. Value = quantity x latest close converted to EUR (pence lines included).
    A holding without a price tonight keeps a row with value None and a note; it is left out of weights and totals."""
    rows = []
    for x in h.holdings:
        if x.ticker is None:                       # a fund without a Yahoo ticker: value typed by hand
            cost = x.cost_eur_total
            rows.append(_empty_position(x, f"fund:{x.name}", currency="EUR", value_eur=x.value_eur, cost_eur=cost,
                                        result_eur=None if cost is None else x.value_eur - cost))
            continue
        close = prices.get(x.ticker)
        close = close.dropna() if close is not None else None
        ccy = currency.get(x.ticker)
        row = _empty_position(x, x.ticker, currency=ccy, sector=sector.get(x.ticker))
        if close is None or not len(close) or float(close.iloc[-1]) <= 0:
            rows.append(row | {"note": "no price tonight"})
            continue
        eur = eur_prices(close, ccy, fx)
        if eur is None or not len(eur):
            rows.append(row | {"note": f"no EUR exchange rate for {ccy or 'an unknown currency'}"})
            continue
        price, eur_last = float(close.iloc[-1]), float(eur.iloc[-1])
        value = x.quantity * eur_last
        approx = x.cost_eur_total is None
        cost = x.quantity * x.cost_price * (eur_last / price) if approx else x.cost_eur_total
        rows.append(row | {"price": round(price, 4), "value_eur": value, "cost_eur": cost, "cost_approx": approx,
                           "result_eur": value - cost, "return_local": price / x.cost_price - 1,
                           "has_risk": x.ticker in risk_tickers})
    total = sum(r["value_eur"] for r in rows if r["value_eur"] is not None)
    for r in rows:
        r["weight"] = r["value_eur"] / total if r["value_eur"] is not None and total > 0 else None
    return rows


def totals(positions: list[dict], tech_group: str = "technology") -> dict:
    """Sums over priced positions. result_complete is False when any position has no result (an unpriced holding, or a fund
    typed in by hand without a cost), because the summed result then leaves it out."""
    priced = [p for p in positions if p["value_eur"] is not None]
    total = sum(p["value_eur"] for p in priced)
    w = (lambda p: p["value_eur"] / total) if total > 0 else (lambda p: 0.0)
    results = [p["result_eur"] for p in priced if p["result_eur"] is not None]
    return {"value_eur": total, "result_eur": sum(results) if results else None,
            "result_complete": all(p["result_eur"] is not None for p in positions),
            "top3_share": sum(sorted((w(p) for p in priced), reverse=True)[:3]),
            "tech_share": sum(w(p) for p in priced if p["group"] == tech_group),
            "risk_covered": sum(w(p) for p in priced if p["has_risk"]),
            "unpriced": len(positions) - len(priced)}


def etf_rows(cfg_etf: dict[str, dict], prices: dict[str, tuple], currency: dict[str, str | None]) -> list[dict]:
    """One row per ETF candidate (ETF lists only). Metrics are None for a ticker without 60 daily closes."""
    rows = []
    for key, v in cfg_etf.items():
        for t, name in v["tickers"].items():
            close, volume = prices.get(t, (None, None))
            m = compute_metrics(close, volume) if close is not None else None
            w = windows(close) if m is not None else {}
            rows.append({"ticker": t, "name": name, "list": key, "group": v.get("groups", {}).get(t),
                         "currency": currency.get(t), "price": m["price"] if m else None,
                         "ret_1y": w.get("ret_1y"), "dd52": m["dd52"] if m else None, "vol_1y": w.get("vol_1y")})
    return rows


# ---- the basket maths, in Python: web/src/lib/basket.ts must match -------------------------------------------

def _reference_cov() -> pd.DataFrame:
    vols = {"AAA": 0.30, "BBB": 0.20, "CCC": 0.25}
    corr = {("AAA", "BBB"): 0.5, ("AAA", "CCC"): 0.2, ("BBB", "CCC"): -0.1}
    names = list(vols)
    return pd.DataFrame([[vols[a] * vols[b] * (1.0 if a == b else corr.get((a, b), corr.get((b, a)))) for b in names]
                         for a in names], index=names, columns=names)


def evaluate_basket(positions: list[dict], basket: dict[str, float], cov: pd.DataFrame,
                    tech_tickers: set[str]) -> dict:
    """Before and after in one function: positions keep their EUR value (locked); `basket` {ticker: EUR} is added,
    to an existing position of the same ticker or as a new one. Volatility is over the part with risk data,
    weights renormalised; volCovered is that part's share of total value."""
    values = {p["key"]: p["value_eur"] for p in positions if p["value_eur"] is not None}
    info = {p["key"]: p for p in positions}
    for t, amount in basket.items():
        values[t] = values.get(t, 0.0) + amount
        info.setdefault(t, {"ticker": t, "group": None})
    total = sum(values.values())
    weights = {k: v / total for k, v in values.items()}
    tech = sum(w for k, w in weights.items() if info[k].get("group") == "technology" or info[k].get("ticker") in tech_tickers)
    risky = [k for k in values if info[k].get("ticker") in cov.index]
    out = {"total": total, "weights": weights, "top3": sum(sorted(weights.values(), reverse=True)[:3]), "tech": tech,
           "vol": None, "volCovered": 0.0, "topRisk": None}
    if risky:
        sub_cov = cov.loc[risky, risky]
        sub = {k: values[k] for k in risky}
        contribution = risk_contribution(sub, sub_cov)
        top = max(contribution, key=contribution.get)
        out |= {"vol": portfolio_vol(sub, sub_cov), "volCovered": sum(values[k] for k in risky) / total,
                "topRisk": {"key": top, "share": contribution[top]}}
    return out


def reference_baskets() -> dict:
    """Small fixed inputs and their results, written to web/src/fixtures/basket_reference.json for the TypeScript tests."""
    cov = _reference_cov()
    positions = [
        {"key": "AAA", "ticker": "AAA", "value_eur": 600.0, "group": "technology", "has_risk": True},
        {"key": "BBB", "ticker": "BBB", "value_eur": 300.0, "group": None, "has_risk": True},
        {"key": "fund:F", "ticker": None, "value_eur": 100.0, "group": None, "has_risk": False},
    ]
    tech = {"CCC"}
    baskets = []
    for items in ({}, {"CCC": 100.0}, {"BBB": 200.0}, {"CCC": 50.0, "AAA": 50.0}):
        baskets.append({"items": [{"ticker": t, "amountEur": a} for t, a in items.items()],
                        "expected": evaluate_basket(positions, items, cov, tech)})
    return {"tickers": list(cov.index), "cov": cov.to_numpy().tolist(), "positions": positions,
            "tech_tickers": sorted(tech), "baskets": baskets}


if __name__ == "__main__":      # python -m engine.holdings [OUT_DIR]: write the basket reference fixture
    import json
    import sys

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else CONFIG_DIR.parent / "web" / "src" / "fixtures"
    (out / "basket_reference.json").write_text(json.dumps(reference_baskets(), indent=1), encoding="utf-8", newline="\n")
    print(f"wrote {out / 'basket_reference.json'}")
