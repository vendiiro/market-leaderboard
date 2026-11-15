"""The owner's holdings: the private file reader, position and total maths, ETF rows and the basket reference fixture.

The holdings file (config/portfolio.toml) is private and gitignored: the repository is public. Tests and the demo use
config/portfolio.example.toml, which holds invented values. Educational research tool: nothing here is advice."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .config import CONFIG_DIR

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
