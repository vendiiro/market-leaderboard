import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from engine import build as B
from engine import demo

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "web" / "src" / "fixtures"
_spec = importlib.util.spec_from_file_location("check_wording", ROOT / "scripts" / "check_wording.py")
check_wording = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_wording)


def read(folder, stem):
    return json.loads((folder / f"{stem}.json").read_text(encoding="utf-8"))


@pytest.fixture()
def out(tmp_path):
    assert B.build(tmp_path, is_demo=True) == 0
    return tmp_path


def test_demo_build_writes_four_files_that_match_their_schemas(out):
    payloads = {stem: read(out, stem) for stem in B.FILES}
    B.validate(payloads)                                              # raises on a mismatch
    assert sorted(p.name for p in out.iterdir()) == ["leaderboard.json", "meta.json", "movers.json", "portfolio.json"]
    assert all(p["schema_version"] == 1 and p["asof"] == demo.END for p in payloads.values())


def test_validation_names_the_place_that_is_wrong(out):
    payloads = {stem: read(out, stem) for stem in B.FILES}
    payloads["leaderboard"]["lists"][0]["rows"][0]["ret_1d"] = "high"
    with pytest.raises(ValueError, match="leaderboard.json .*ret_1d"):
        B.validate(payloads)


def test_nan_and_infinity_are_never_written(out):
    assert B._plain({"a": float("nan"), "b": [np.float64("inf"), np.int64(3), np.bool_(True)], "c": 1.5}) == {
        "a": None, "b": [None, 3, True], "c": 1.5}
    for stem in B.FILES:
        text = (out / f"{stem}.json").read_text(encoding="utf-8")
        assert "NaN" not in text and "Infinity" not in text
    with pytest.raises(ValueError):
        B._dump({"x": float("nan")})                                  # the writer itself refuses, as a second guard


def test_demo_is_deterministic_and_the_committed_fixtures_are_current(out, tmp_path_factory):
    """web/src/fixtures/*.json must equal the demo build; regenerate with
    uv run python -m engine build --demo --out web/src/fixtures"""
    again = tmp_path_factory.mktemp("again")
    B.build(again, is_demo=True)
    for stem in B.FILES:
        assert (out / f"{stem}.json").read_bytes() == (again / f"{stem}.json").read_bytes()
        assert read(FIXTURES, stem) == read(out, stem), f"fixture {stem}.json is out of date"


def test_demo_contains_every_state_the_page_must_handle(out):
    meta, lb, mv, pf = (read(out, s) for s in ("meta", "leaderboard", "movers", "portfolio"))
    rows = {(x["key"], r["ticker"]): r for x in lb["lists"] for r in x["rows"]}
    assert meta["demo"] is True and meta["tickers"] == 16 and meta["usable"] == 15
    assert [f["ticker"] for f in meta["failures"]] == ["FIND.HE"] and "no rows" in meta["failures"][0]["reason"]
    stale = rows[("fi_small", "FINB.HE")]
    assert stale["stale"] and stale["rank"] is None and stale["stale_reason"]
    assert rows[("eu_energy", "ENGA.OL")]["lists"] == ["eu_energy", "nordic_energy"] and ("nordic_energy", "ENGA.OL") in rows
    assert [a["ticker"] for a in mv["alerts"]] == ["DEMD"] and mv["losers"][0]["ticker"] == "DEMD"
    assert [x["ticker"] for x in pf["no_risk_data"]] == ["DEFC.PA", "FINB.HE"]
    assert rows[("eu_defence", "DEFC.PA")]["ret_1y"] is not None                     # still ranked on the leaderboard
    assert rows[("fi_small", "FINC.HE")]["q_score"] is None                           # thin fundamentals: no score


def test_portfolio_matrices_line_up(out):
    pf = read(out, "portfolio")
    n = len(pf["risk_tickers"])
    assert n == 13 and pf["window"]["weeks"] == 104 and pf["window"]["end"] == "2026-11-06"
    cov = np.array(pf["cov"])
    assert cov.shape == (n, n) and np.allclose(cov, cov.T) and np.linalg.eigvalsh(cov).min() > -1e-7
    vols = {t["ticker"]: t["vol_eur"] for t in pf["tickers"]}
    assert len(vols) == 15 and vols["DEFC.PA"] is None
    assert vols[pf["risk_tickers"][0]] == pytest.approx(cov[0, 0] ** 0.5, abs=1e-4)
    assert np.allclose(np.diag(np.array(pf["corr"])), 1)


def test_all_text_in_the_output_passes_the_wording_check(out):
    for stem in B.FILES:
        assert check_wording.scan_text((out / f"{stem}.json").read_text(encoding="utf-8")) == []


def test_an_error_while_writing_leaves_the_previous_files_intact(out, monkeypatch):
    before = {stem: (out / f"{stem}.json").read_bytes() for stem in B.FILES}
    real = B._dump

    def dump(payload):
        if "gainers" in payload:                                      # the second file fails
            raise OSError("disk full")
        return real(payload)

    monkeypatch.setattr(B, "_dump", dump)
    inputs = demo.inputs()
    inputs["prices"]["DEMA"][0].iloc[-1] *= 1.5                       # new data that must not reach the folder
    with pytest.raises(OSError):
        B.build(out, is_demo=True, inputs=inputs)
    assert {stem: (out / f"{stem}.json").read_bytes() for stem in B.FILES} == before
    assert not list(out.glob("*.tmp"))


def test_too_few_usable_tickers_keeps_the_previous_files(out, capsys):
    before = {stem: (out / f"{stem}.json").read_bytes() for stem in B.FILES}
    inputs = demo.inputs()
    for t in ("DEMA", "DEMB"):                                        # 13 of 16 usable: under 90%
        del inputs["prices"][t]
    assert B.build(out, is_demo=True, inputs=inputs) == 2
    assert "previous files kept" in capsys.readouterr().out
    assert {stem: (out / f"{stem}.json").read_bytes() for stem in B.FILES} == before


def test_cli_runs_the_demo_build(tmp_path):
    import subprocess
    import sys
    r = subprocess.run([sys.executable, "-m", "engine", "build", "--demo", "--out", str(tmp_path)], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "15 of 16 tickers" in r.stdout and (tmp_path / "meta.json").exists()
