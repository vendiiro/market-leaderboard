"""The repository is public: the owner's holdings file must never be tracked (docs/superpowers/specs/2026-11-15-portfolio-page-design.md)."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def test_portfolio_file_is_ignored_by_git():
    assert git("check-ignore", "config/portfolio.toml").returncode == 0


def test_private_history_files_are_ignored_by_git():
    assert git("check-ignore", "config/nordnet.private.csv").returncode == 0


def test_no_tracked_file_is_the_private_file():
    tracked = git("ls-files").stdout.split()
    assert "config/portfolio.toml" not in tracked
    assert not [t for t in tracked if ".private." in t]
