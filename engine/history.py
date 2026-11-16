"""The broker's "daily development" export (Nordnet) and a summary of it. No network.

Format, checked on the owner's real file on 2026-11-15: UTF-16 with a byte order mark, tab-separated, decimal comma,
percent signs in the percent columns, one row per week from the first deposit. Seven columns: date, total value,
daily development %, accumulated return %, daily development EUR, accumulated return EUR, net deposits EUR.
The accumulated return in percent is time-weighted (deposits do not distort it); the one in EUR is money-weighted,
so the two can disagree in sign. This module uses the percent column only. Weekly points, not daily ones."""
from __future__ import annotations

import math

from datetime import date
from pathlib import Path

COLUMNS = 7
_BOMS = (b"\xff\xfe", b"\xfe\xff")


def _fail(why: str) -> ValueError:
    return ValueError(f"Nordnet history file: {why}")


def _num(text: str, row: int, what: str) -> float:
    t = text.strip().replace("%", "").replace(" ", "").replace(" ", "").replace(",", ".").replace("−", "-")
    try:
        x = float(t)
    except ValueError:
        raise _fail(f"row {row}: {what} {text!r} is not a number") from None
    if not math.isfinite(x):
        raise _fail(f"row {row}: {what} {text!r} is not a finite number")
    return x


def read_nordnet_csv(path: Path | str) -> list[dict]:
    """[{"date": "YYYY-MM-DD", "value": EUR, "cum": accumulated return as a fraction, "net_deposits": EUR}]."""
    p = Path(path)
    try:
        raw = p.read_bytes()
    except OSError as e:
        raise _fail(f"cannot read {p.name} ({e.strerror or e})") from None
    if not raw:
        raise _fail(f"{p.name} is empty")
    if not raw.startswith(_BOMS):
        raise _fail(f"{p.name} is not UTF-16 (the export has a byte order mark); open the original export, do not re-save it")
    lines = [ln for ln in raw.decode("utf-16").splitlines() if ln.strip()]
    if not lines:
        raise _fail(f"{p.name} has no rows")
    if len(lines[0].split("\t")) != COLUMNS:
        raise _fail(f"expected {COLUMNS} tab-separated columns, got {len(lines[0].split(chr(9)))}")
    out = []
    for i, line in enumerate(lines[1:], start=2):
        cells = line.split("\t")
        if len(cells) != COLUMNS:
            raise _fail(f"row {i} has {len(cells)} columns, expected {COLUMNS}")
        try:
            day = date.fromisoformat(cells[0].strip())
        except ValueError:
            raise _fail(f"row {i}: date {cells[0]!r} is not YYYY-MM-DD") from None
        out.append({"date": str(day), "value": _num(cells[1], i, "value"), "cum": _num(cells[3], i, "accumulated return") / 100,
                    "net_deposits": _num(cells[6], i, "net deposits")})
    if not out:
        raise _fail(f"{p.name} has a header but no rows")
    return out


def _month_before(d: date) -> date:
    y, m = (d.year, d.month - 1) if d.month > 1 else (d.year - 1, 12)
    for day in (d.day, 30, 29, 28):
        try:
            return date(y, m, day)
        except ValueError:
            continue
    raise AssertionError("unreachable")


def _at_or_before(points: list[dict], boundary: date) -> dict | None:
    earlier = [p for p in points if date.fromisoformat(p["date"]) <= boundary]
    return earlier[-1] if earlier else None


def summarise(points: list[dict], asof: str) -> dict:
    """since_start, month, ytd (fractions; month and ytd are None without an earlier weekly point), the largest fall
    of the accumulated-return index with its dates, and the lowest and highest accumulated return."""
    asof_d = date.fromisoformat(asof)
    last = points[-1]["cum"]

    def since(boundary: date) -> float | None:
        base = _at_or_before(points, boundary)
        return None if base is None or base is points[-1] else (1 + last) / (1 + base["cum"]) - 1

    peak, peak_date = float("-inf"), points[0]["date"]
    worst, frm, to = 0.0, points[0]["date"], points[0]["date"]
    for p in points:
        idx = 1 + p["cum"]
        if idx > peak:
            peak, peak_date = idx, p["date"]
        if idx / peak - 1 < worst:
            worst, frm, to = idx / peak - 1, peak_date, p["date"]
    lo = min(points, key=lambda p: p["cum"])
    hi = max(points, key=lambda p: p["cum"])
    return {"since_start": last, "month": since(_month_before(asof_d)), "ytd": since(date(asof_d.year - 1, 12, 31)),
            "max_drawdown": worst, "drawdown_from": frm, "drawdown_to": to,
            "lowest": {"date": lo["date"], "cum": lo["cum"]}, "highest": {"date": hi["date"], "cum": hi["cum"]}}
