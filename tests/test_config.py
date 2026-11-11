import tomllib
from pathlib import Path

import pytest

from engine.config import Settings, load_settings


def test_real_settings_file_loads_with_expected_values():
    s = load_settings()
    assert s.dip.drop_1d == 0.04 and s.dip.drop_5d == 0.07 and s.dip.drawdown_20d == 0.12
    assert s.quality.market_cap_min == 20_000_000_000
    assert s.data.max_stale_trading_days == 4


def test_code_defaults_match_the_settings_file():
    assert Settings() == load_settings()


def test_run_health_thresholds_in_toml_equal_dataclass_defaults():
    from engine.config import DataSettings
    raw = tomllib.loads((Path(__file__).resolve().parents[1] / "config" / "settings.toml").read_text(encoding="utf-8"))["data"]
    d = DataSettings()
    for k in ("min_fundamentals_share", "min_bars_share", "min_earnings_share"):
        assert k in raw, k
        assert raw[k] == getattr(d, k) == getattr(load_settings().data, k)
    assert (d.min_fundamentals_share, d.min_bars_share, d.min_earnings_share) == (0.8, 0.8, 0.5)


def test_partial_file_falls_back_to_defaults(tmp_path):
    p = tmp_path / "s.toml"
    p.write_text("[dip]\ndrop_1d = 0.03\n")
    s = load_settings(p)
    assert s.dip.drop_1d == 0.03 and s.dip.drop_5d == 0.07 and s.quality == Settings().quality


def test_typo_in_a_key_is_an_error_not_a_silent_default(tmp_path):
    p = tmp_path / "s.toml"
    p.write_text("[dip]\ndrop_1_day = 0.03\n")
    with pytest.raises(ValueError, match="drop_1_day"):
        load_settings(p)


def test_unknown_section_is_an_error(tmp_path):
    p = tmp_path / "s.toml"
    p.write_text("[dips]\ndrop_1d = 0.03\n")
    with pytest.raises(ValueError, match="dips"):
        load_settings(p)


