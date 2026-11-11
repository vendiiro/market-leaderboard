# Market Leaderboard Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A new local dashboard that ranks four watchlists (US big tech, EU defence + energy, Nordic energy, Finnish 0.3-5B EUR small caps) like a leaderboard, shows daily movers and dip alerts, and lets the owner build test mixes to see how sector/country/currency exposure and portfolio volatility change.

**Architecture:** A Python engine (proven modules copied from dip-dashboard) fetches daily data and writes versioned JSON files; a React + TypeScript (Vite) static site reads them. The site computes only weighted sums and sqrt(w'Σw) on engine numbers, tested against Python reference values.

**Tech Stack:** Python 3.11 + uv, pandas, numpy, yfinance, pytest; Node LTS, React 18, TypeScript (strict), Vite, Apache ECharts, TanStack Table, Vitest, Playwright.

**Spec:** `docs/spec.md` (in this repo).

**Reference repo:** https://github.com/vendiiro/dip-dashboard, branch `dashboard-brief-compact-table`, commit `f14d55c`. Clone it read-only next to this repo (`../dip-dashboard`) and copy code from it; never push to it.

## Global Constraints

- This repo is https://github.com/vendiiro/market-leaderboard (public). Work in a clone of it; dip-dashboard is never modified.
- Source modules are copied from the reference repo at commit `f14d55c` (`src/dipdash/`, `scripts/`); note the source path and commit in each copied file's header docstring.
- Works on the owner's Windows PC and in a fresh cloud session: no absolute paths in code; the nightly scheduler files (Task 11) are Windows-only.
- Wording: screen results, candidates, exposure; never "buy", "sell", targets or advice. Run a wording check on all UI strings and JSON text.
- Every watchlist ticker passes Yahoo verification (>= 250 daily bars in 1y, last bar <= 4 trading days old, quoteType EQUITY, currency matches the exchange) before use; no ticker is used because it was typed from memory.
- Finnish small caps: Nasdaq Helsinki (`.HE`), market cap 0.3-5.0B EUR, median 60-day traded value >= 0.5M EUR, rebuilt monthly by rule.
- Returns in local currency; mix exposure in EUR via the copied FX code. Correlations are lag-aware as defined in the spec (Constraints section): pairs with exactly one non-US name use max(same-date, non-US day t vs US latest day before t); labelled on screen.
- Test mixes only: no real holdings are read; mixes live in browser storage with JSON export/import.
- Every on-screen number comes from engine JSON; front end math limited to weighted sums and sqrt(w'Σw), unit-tested against Python fixtures.
- Views are done only after Playwright screenshots at 1280 and 390 px wide, light and dark, are looked at.
- Do not commit `.env`, `data/`, `web/public/data/` live files (fixtures under `web/src/fixtures/` are committed).

## Review Focus

- A ticker whose data fetch fails on a given night: the row shows "no data tonight" with the reason, the page still loads, ranks exclude it.
- A mix with weights not summing to 100% or containing a ticker missing from tonight's data: the page normalises or names the problem, never shows NaN.
- Holidays on one exchange (e.g. Helsinki closed, US open): 1d returns use each stock's own last two bars and say so; movers do not rank stale rows.
- UK pence-quoted listings (`.L`): excluded until the pence/pound rule exists; verification rejects them with a clear reason.
- Empty or partially written JSON (night run interrupted): the page shows the previous build's date and a banner, not a blank screen (build writes to temp files and renames).

## Sessions

- **Session 1:** Tasks 0-3 (repo, engine copy, watchlists, leaderboard engine).
- **Session 2:** Tasks 4-7 (mix maths engine, movers, JSON build + schemas, web shell + leaderboard).
- **Session 3:** Tasks 8-11 (diversification view, movers view, visual verification, nightly run).

---

### Task 0: Repo scaffold

**Files:** In the existing repo (already holds `README.md`, `START_HERE.md`, `CLAUDE.md`, `.gitignore`, `docs/spec.md`, `docs/plan.md`): create `pyproject.toml`, `engine/__init__.py`, `tests/`, `web/` (Vite React-TS template).

- [ ] **Step 0:** `git clone --branch dashboard-brief-compact-table https://github.com/vendiiro/dip-dashboard ../dip-dashboard` (reference, read-only); confirm `git -C ../dip-dashboard rev-parse --short HEAD` is `f14d55c` or a descendant.
- [ ] **Step 1:** `uv venv`; `uv pip install pandas numpy yfinance pytest`; `npm create vite@latest web -- --template react-ts`; add `echarts`, `@tanstack/react-table`, `vitest`, `@playwright/test` (say why each is added in the commit message).
- [ ] **Step 2:** `pytest -q` (empty, passes) and `npm --prefix web run build` (passes).
- [ ] **Step 3:** Commit `chore: scaffold market-leaderboard`.

### Task 1: Engine copy

**Files:** Copy from `../dip-dashboard/src/dipdash/` into `engine/`: `data.py`, `fx.py`, `quality.py`, `metrics.py`, `exchanges.py`, `cache.py`, `config.py` (only the pieces used), and the verification core of `../dip-dashboard/scripts/verify_universe.py` as `engine/verify.py`; copy their tests from `../dip-dashboard/tests/` into `tests/`.

**Interfaces:**
- Produces: `engine.verify.check_ticker(ticker: str, bars, info: dict, rates: dict) -> tuple[str, str]` (status, detail) with statuses ok / no_bars / stale / not_equity / currency_mismatch / under_cap.

- [ ] **Step 1:** Copy files, fix imports (`dipdash.` -> `engine.`), keep behaviour identical.
- [ ] **Step 2:** Run the copied tests: all pass (drop tests for code not copied, list them in the commit message).
- [ ] **Step 3:** Commit.

### Task 2: Watchlists

**Files:** Create `config/watchlists.toml`, `engine/watchlists.py`, `scripts/verify_watchlists.py`, `scripts/build_fi_smallcaps.py`; Test `tests/test_watchlists.py`.

**Interfaces:**
- Produces: `load_watchlists(path) -> dict[str, list[str]]` (keys `us_big_tech`, `eu_defence`, `eu_energy`, `nordic_energy`, `fi_small`); `config/watchlists_verified.csv` (ticker, list, name, sector, country, currency, market_cap_eur, status).
- `build_fi_smallcaps(candidates: list[str], info: dict, bars: dict, rates: dict, lo=0.3e9, hi=5.0e9, min_traded=0.5e6) -> list[str]`.

- [ ] **Step 1:** Failing tests: TOML loads the five keys; unknown key rejected; `build_fi_smallcaps` keeps a 1.2B EUR liquid name, drops 0.2B, 6B and an illiquid 1B name (synthetic inputs).
- [ ] **Step 2:** Implement. Seed lists in the TOML from the spec's candidate names; the Helsinki candidate list comes from a parsed source (Nasdaq Helsinki main list or Wikipedia list of Helsinki-listed companies), never typed.
- [ ] **Step 3:** Run `scripts/verify_watchlists.py` live; every non-ok ticker is removed from the TOML with the reason in the commit message.
- [ ] **Step 4:** Tests pass; commit.

### Task 3: Leaderboard engine

**Files:** Create `engine/leaderboard.py`; Test `tests/test_leaderboard.py`.

**Interfaces:**
- Produces: `leaderboard_rows(prices: dict[str, pd.Series], fund: dict[str, dict], meta: dict[str, dict], asof: date) -> pd.DataFrame` with columns `ret_1d, ret_1w, ret_1m, ret_ytd, ret_1y, dd52, vol_1y, q_score, dip, last_bar, stale, spark` (spark = last 60 closes rebased to 100).

- [ ] **Step 1:** Failing tests with synthetic series: known returns for each window, YTD from the last bar of the previous year, `stale` True when the last bar is > 4 trading days before `asof`, dip flag matches the copied rule, spark length 60 and starts at 100.
- [ ] **Step 2:** Implement using the copied `metrics.py` where it already computes the value.
- [ ] **Step 3:** Tests pass; commit.

### Task 4: Mix maths engine

**Files:** Create `engine/portfolio.py`; Test `tests/test_portfolio.py`; write fixture `web/src/fixtures/mix_reference.json`.

**Interfaces:**
- Produces: `ticker_meta(...) -> dict[str, {sector, country, currency, vol_1y}]`; `covariance(prices, tickers, window=252) -> pd.DataFrame` (annualised, lag-aware correlation x vols for non-US); `exposure(weights, meta, key) -> dict[str, float]`; `portfolio_vol(weights, cov) -> float`.

- [ ] **Step 1:** Failing tests: exposure of a 3-name mix by sector sums to 1; portfolio_vol of one name equals its vol; two perfectly correlated names equal weighted vol; two uncorrelated equal-vol names give vol/sqrt(2); covariance matrix symmetric and positive semi-definite (nearest-PSD fix if needed, documented).
- [ ] **Step 2:** Implement; write the fixture (3 example mixes with Python-computed exposure and vol) for the TypeScript tests.
- [ ] **Step 3:** Tests pass; commit.

### Task 5: Movers and alerts

**Files:** Create `engine/movers.py`; Test `tests/test_movers.py`.

**Interfaces:** `movers(rows: pd.DataFrame, n=10) -> dict` with `gainers`, `losers` (non-stale rows only, ranked by ret_1d) and `alerts` (dip flags with plain-language reasons).

- [ ] **Step 1:** Failing tests: stale rows excluded; ties broken by ticker; alert reason text passes the wording check.
- [ ] **Step 2-3:** Implement, pass, commit.

### Task 6: JSON build and schemas

**Files:** Create `engine/build.py`, `schemas/*.schema.json`; Test `tests/test_build.py`.

**Interfaces:** `build(out_dir: Path, asof: date) -> None` writes `meta.json` (schema_version, asof, built_at, per-list counts, failures), `leaderboard.json`, `movers.json`, `portfolio.json` (meta + covariance for all watchlist tickers); writes to temp files and renames.

- [ ] **Step 1:** Failing tests: outputs validate against schemas; NaN never serialised (null instead); interrupted build leaves previous files intact.
- [ ] **Step 2-3:** Implement, pass, run once live, commit (not the live data).

### Task 7: Web shell and leaderboard view

**Files:** `web/src/App.tsx`, `web/src/data.ts` (typed loaders), `web/src/views/Leaderboard.tsx`, `web/src/theme.css` (colour tokens, light/dark); Test `web/src/data.test.ts`.

- [ ] **Step 1:** Types generated or hand-written from the schemas; a Vitest test loads a fixture and rejects a wrong schema_version.
- [ ] **Step 2:** Tabs per watchlist; TanStack table sortable by every column; ECharts sparkline per row; stale rows greyed with the reason; banner when `meta.asof` is older than the last expected session.
- [ ] **Step 3:** `npm run build` passes; Playwright screenshots (1280/390, light/dark) looked at; commit.

### Task 8: Diversification view

**Files:** `web/src/views/Mix.tsx`, `web/src/mix.ts` (exposure, portfolioVol); Test `web/src/mix.test.ts`.

- [ ] **Step 1:** Failing Vitest tests: `exposure` and `portfolioVol` match `fixtures/mix_reference.json` within 1e-9; weights normalised; a missing ticker is reported, not NaN.
- [ ] **Step 2:** Mix builder (pick tickers from any watchlist, set weights), saved in browser storage, export/import JSON; exposure bars by sector, country, currency, watchlist; correlation heatmap for the mix; "compare two mixes" side by side; on-screen note on lag-aware correlation and that this is educational, not advice.
- [ ] **Step 3:** Tests pass; screenshots looked at; commit.

### Task 9: Movers view

**Files:** `web/src/views/Movers.tsx`.

- [ ] **Step 1:** Gainers/losers tables and alert cards from `movers.json`; empty state text when nothing moved.
- [ ] **Step 2:** Build, screenshots, commit.

### Task 10: Visual and wording verification

- [ ] **Step 1:** Playwright script screenshots every view at 1280/390 px, light/dark; checks no horizontal scroll and no console errors.
- [ ] **Step 2:** Wording check over UI strings and JSON text; accessibility contrast check of the colour tokens.
- [ ] **Step 3:** Fix findings; commit.

### Task 11: Nightly run and docs

**Files:** `scripts/run_nightly.bat`, `scripts/install_task.ps1` (pattern from dip-dashboard), `README.md`, `START_HERE.md`.

- [ ] **Step 1:** Bat: `cd /d` to repo root, run `engine.build`, `npm --prefix web run build`, log to `output/nightly.log`, propagate exit code.
- [ ] **Step 2:** Docs: how to run, how to open the page in Chrome, how the watchlists are verified and refreshed, limitations (free data, not point-in-time, survivorship, correlation timing).
- [ ] **Step 3:** Commit.
