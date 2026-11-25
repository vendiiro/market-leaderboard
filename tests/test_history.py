import pytest

from engine import history as Hi

HEADER = "Päivämäärä\tArvo yhteensä (EUR)\tPäiväkohtainen kehitys (%)\tKertynyt tuotto (%)\t" \
         "Päiväkohtainen kehitys (EUR)\tKertynyt tuotto (EUR)\tNettotalletukset (EUR)"


def write(tmp_path, rows, header=HEADER, encoding="utf-16"):
    p = tmp_path / "export.csv"
    p.write_bytes(("\n".join([header, *rows]) + "\n").encode(encoding))
    return p


def pt(date, cum, value=1000.0):
    return {"date": date, "value": value, "cum": cum, "net_deposits": 900.0}


def test_parses_decimal_comma_percent_and_minus(tmp_path):
    p = write(tmp_path, ["2025-04-04\t1000,50\t-1,25%\t-10,00%\t-12,50\t-111,00\t1111,00"])
    [row] = Hi.read_nordnet_csv(p)
    assert row == {"date": "2025-04-04", "value": 1000.5, "cum": -0.10, "net_deposits": 1111.0}


def test_summary_chains_the_cumulative_return():
    pts = [pt("2026-09-11", 0.0), pt("2026-10-09", 0.10), pt("2026-10-30", -0.05), pt("2026-11-12", 0.20)]
    s = Hi.summarise(pts, "2026-11-12")
    assert s["since_start"] == pytest.approx(0.20)
    assert s["month"] == pytest.approx(1.20 / 1.10 - 1)       # boundary 2026-10-12: nearest earlier point is 10-09
    assert s["ytd"] is None                                    # history starts this year: no earlier point


def test_ytd_and_month_use_the_nearest_earlier_point():
    pts = [pt("2025-12-26", 0.05), pt("2026-03-06", 0.10)]
    s = Hi.summarise(pts, "2026-03-06")
    assert s["ytd"] == pytest.approx(1.10 / 1.05 - 1)
    assert s["month"] == pytest.approx(1.10 / 1.05 - 1)       # boundary 2026-02-06: nearest earlier is 2025-12-26


def test_max_drawdown_and_extremes():
    pts = [pt("2026-01-02", 0.0), pt("2026-01-09", 0.20), pt("2026-01-16", -0.10), pt("2026-01-23", 0.05)]
    s = Hi.summarise(pts, "2026-01-23")
    assert s["max_drawdown"] == pytest.approx(-0.25)           # peak index 1.20, trough 0.90
    assert (s["drawdown_from"], s["drawdown_to"]) == ("2026-01-09", "2026-01-16")
    assert s["lowest"] == {"date": "2026-01-16", "cum": -0.10}
    assert s["highest"] == {"date": "2026-01-09", "cum": 0.20}


def test_single_point_has_no_drawdown_and_no_month():
    s = Hi.summarise([pt("2026-01-02", 0.0)], "2026-01-02")
    assert s["max_drawdown"] == 0.0 and s["month"] is None and s["since_start"] == 0.0


@pytest.mark.parametrize("make", ["missing", "empty", "utf8", "five_columns", "bad_number"])
def test_bad_files(tmp_path, make):
    row = "2025-04-04\t1000,50\t-1,25%\t-10,00%\t-12,50\t-111,00\t1111,00"
    if make == "missing":
        p = tmp_path / "nope.csv"
    elif make == "empty":
        p = tmp_path / "e.csv"
        p.write_bytes(b"")
    elif make == "utf8":
        p = write(tmp_path, [row], encoding="utf-8")
    elif make == "five_columns":
        p = write(tmp_path, ["a\tb\tc\td\te"], header="a\tb\tc\td\te")
    else:
        p = write(tmp_path, [row.replace("-10,00%", "abc")])
    with pytest.raises(ValueError, match="history"):
        Hi.read_nordnet_csv(p)


def test_bom_only_and_blank_files_are_history_errors(tmp_path):
    for name, raw in (("bom", b"\xff\xfe"), ("blank", "\n\n\n".encode("utf-16"))):
        p = tmp_path / f"{name}.csv"
        p.write_bytes(raw)
        with pytest.raises(ValueError, match="history"):
            Hi.read_nordnet_csv(p)


@pytest.mark.parametrize("bad", ["nan", "inf", "-inf"])
def test_non_finite_numbers_are_history_errors(tmp_path, bad):
    p = write(tmp_path, [f"2025-04-04\t1000,50\t-1,25%\t{bad}\t-12,50\t-111,00\t1111,00"])
    with pytest.raises(ValueError, match="history"):
        Hi.read_nordnet_csv(p)
