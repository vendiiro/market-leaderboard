"""Command line: python -m engine build [--demo] [--out DIR] [--asof YYYY-MM-DD]. See engine/build.py."""
import argparse
from datetime import date
from pathlib import Path

from .build import DEFAULT_OUT, build

ap = argparse.ArgumentParser(prog="python -m engine")
sub = ap.add_subparsers(dest="command", required=True)
b = sub.add_parser("build", help="write the four JSON files the page reads")
b.add_argument("--demo", action="store_true", help="synthetic data, no network")
b.add_argument("--out", type=Path, default=DEFAULT_OUT)
b.add_argument("--asof", type=date.fromisoformat, help="data date (default: the newest bar)")
a = ap.parse_args()
raise SystemExit(build(a.out, a.asof, is_demo=a.demo))
