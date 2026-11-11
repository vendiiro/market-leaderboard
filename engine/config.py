# Copied from dip-dashboard src/dipdash/config.py at commit f14d55c (imports renamed to engine).
"""Settings (config/settings.toml) loading."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"


@dataclass(frozen=True)
class DipSettings:
    drop_1d: float = 0.04
    drop_5d: float = 0.07
    drawdown_20d: float = 0.12


@dataclass(frozen=True)
class QualitySettings:
    min_score: int = 60
    roe_min: float = 0.12
    margin_min: float = 0.08
    debt_to_equity_max: float = 150
    market_cap_min: float = 20_000_000_000
    must_pass: tuple[str, ...] = ("net_margin_positive",)    # named rules (quality.py); a failure blocks the "Quality dip" label
    distorted_roe_above: float = 1.0                          # ROE above this (1.0 = 100%) is flagged as distorted


@dataclass(frozen=True)
class FallingKnifeSettings:
    below_200d_falling: bool = True
    drawdown_52w: float = 0.35


@dataclass(frozen=True)
class NewsSettings:
    fetch_if_5d_drop: float = 0.05


@dataclass(frozen=True)
class DataSettings:
    max_stale_trading_days: int = 4
    min_screened_fraction: float = 0.9       # a run that screens fewer stocks than this share of the universe fails and keeps yesterday's files
    min_fundamentals_share: float = 0.8      # share of screened stocks with usable fundamentals; below it the run reports an error (the run still publishes)
    min_bars_share: float = 0.8              # an exchange with bars for fewer than this share of its tickers gets a warning
    min_earnings_share: float = 0.5          # earnings dates known for fewer than this share of an exchange gets an info line


@dataclass(frozen=True)
class Settings:
    dip: DipSettings = field(default_factory=DipSettings)
    quality: QualitySettings = field(default_factory=QualitySettings)
    falling_knife: FallingKnifeSettings = field(default_factory=FallingKnifeSettings)
    news: NewsSettings = field(default_factory=NewsSettings)
    data: DataSettings = field(default_factory=DataSettings)


def _section(cls, raw: dict, name: str):
    known = {f.name for f in fields(cls)}
    unknown = set(raw) - known
    if unknown:
        raise ValueError(f"settings.toml [{name}]: unknown key(s) {sorted(unknown)}; expected {sorted(known)}")
    kw = {k: tuple(v) if isinstance(v, list) else v for k, v in raw.items()}
    return cls(**kw)


def load_settings(path: Path | str | None = None) -> Settings:
    """Read settings.toml. A missing section or key falls back to the default above."""
    p = Path(path) if path else CONFIG_DIR / "settings.toml"
    raw = tomllib.loads(p.read_text(encoding="utf-8"))
    unknown = set(raw) - {f.name for f in fields(Settings)}
    if unknown:
        raise ValueError(f"settings.toml: unknown section(s) {sorted(unknown)}")
    defaults = Settings()
    return Settings(**{f.name: _section(type(getattr(defaults, f.name)), raw.get(f.name, {}), f.name)
                       for f in fields(Settings)})
