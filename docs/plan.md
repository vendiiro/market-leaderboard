# Market Leaderboard Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A local dashboard that ranks five watchlists (US big tech, EU defence, EU energy, Nordic energy, Finnish 0.3-5B EUR small caps) like a leaderboard, opens on an overview page, shows daily movers and labelled dip alerts, and lets the owner build test mixes to see exposure, EUR volatility and risk contribution.

**Architecture:** A Python engine (proven modules copied from dip-dashboard) fetches daily data and writes four schema-validated JSON files; a React + TypeScript (Vite) static site reads them. The site computes only sorting, formatting and the four mix formulas in the spec, tested against Python reference values.

**Tech Stack:** Python 3.11+ with uv (`pyproject.toml` + `uv.lock`), pandas, numpy, yfinance, jsonschema, pytest, ruff; Node LTS, React (the version the current Vite template installs), TypeScript strict, Vite, Apache ECharts (modular imports), TanStack Table, json-schema-to-typescript, Vitest, Playwright.

**Spec:** `docs/spec.md` revision 2 (in this repo). Where the plan and the spec disagree, the spec wins; stop and report the conflict.

**Reference repo:** https://github.com/vendiiro/dip-dashboard, branch `dashboard-brief-compact-table`, commit `f14d55c`. Clone it read-only next to this repo (`../dip-dashboard`) and copy code from it; never push to it.

## Global Constraints

- This repo is https://github.com/vendiiro/market-leaderboard (public). Work in a clone of it; dip-dashboard is never modified.
- Copied files note the source path and commit in the header docstring. Copy behaviour unchanged; changes come in later, separate commits.
- Works on the owner's Windows PC and in a fresh cloud session: no absolute paths in code; only `scripts/*.bat` and `scripts/*.ps1` are Windows-only. Do not set `PYTHONUTF8=1` (the owner's user folder has non-ASCII characters); use `PYTHONIOENCODING=utf-8`.
- Dependencies are added with `uv add` / `npm install` and each one is justified in the commit message. No global installs.
- Wording: screen results, candidates, exposure; never "buy", "sell", targets or advice. Dip flag and quality score always carry "untested screen rule".
- Every watchlist ticker passes Yahoo verification (>= 250 daily bars in 1y, last bar <= 4 trading days old, quoteType EQUITY, currency matches the exchange registry) before use; no ticker is used because it was typed from memory.
- Leaderboard numbers are in local currency; mix numbers are in EUR from weekly returns over the last 104 complete weeks (spec, "Mix maths"). The old daily lag-aware correlation rule is gone; do not implement it.
- Test mixes only: no real holdings are read; mixes live in browser storage with JSON export/import.
- Every on-screen number comes from engine JSON. Browser arithmetic is limited to exposure sums, `w'Σw`, risk contribution and effective number of names.
- Everything testable offline: tests use synthetic data; `python -m engine build --demo` produces a full data set without network.
- Views are done only after Playwright screenshots at 1280 and 390 px wide, light and dark, are looked at.
- Do not commit `.env`, `data/`, `output/`, `web/public/data/` (fixtures under `web/src/fixtures/` are committed).

## Review Focus

- A ticker whose fetch fails tonight: the row shows "no data tonight" with the reason, the page still loads, ranks and movers exclude it.
- Fewer than 90 % of tickers usable: the build keeps the previous files; the page shows the previous date and a banner.
- A ticker on two lists (Equinor, Vestas, Ørsted): once in movers, once in the covariance, once in the mix picker.
- A mix with weights not summing to 100 %, a ticker missing tonight, or a ticker in `no_risk_data`: the page normalises or names the problem and says which part of the mix the risk numbers cover; never NaN.
- Holidays on one exchange: 1d returns use each stock's own last two bars and show the bar date; movers do not rank stale rows.
- UK pence: no EUR market cap for a `.L` name before the pounds/pence check in Task 2 is recorded.
- Interrupted build: temp files then rename; old files stay intact.
- Phone width: no horizontal page scroll anywhere; the expanded row shows every number the desktop table shows.

## Sessions

- **Session 1 (foundation):** Tasks 0-3: scaffold + CI, engine copy, FX in EUR + UK rule, watchlists.
- **Session 2 (engine):** Tasks 4-7: returns and ranks, mix maths, movers, build pipeline + schemas + demo data.
- **Session 3 (front end core):** Tasks 8-10: web foundation, leaderboard view, overview view.
- **Session 4 (finish):** Tasks 11-14: mix view, movers view, verification pass, nightly run + launcher + docs.

---

### Task 0: Repo scaffold and CI

**Files:** `pyproject.toml`, `uv.lock`, `engine/__init__.py`, `tests/`, `web/` (Vite React-TS template), `.github/workflows/ci.yml`, `.gitattributes` (LF for text, CRLF for `.bat`), extend `.gitignore` (`.ruff_cache/`, `web/src/**/*.tsbuildinfo`).

- [ ] **Step 0:** `git clone --branch dashboard-brief-compact-table https://github.com/vendiiro/dip-dashboard ../dip-dashboard`; confirm `git -C ../dip-dashboard rev-parse --short HEAD` is `f14d55c` or a descendant.
- [ ] **Step 1:** `uv init --bare` style `pyproject.toml` (package `engine`, Python >= 3.11); `uv add pandas numpy yfinance jsonschema`; `uv add --dev pytest ruff`. `npm create vite@latest web -- --template react-ts`; add `echarts`, `@tanstack/react-table`; dev: `vitest`, `@playwright/test`, `json-schema-to-typescript`. Set `base: './'` in `vite.config.ts`.
- [ ] **Step 2:** `uv run pytest -q` (no tests, passes), `uv run ruff check`, `npm --prefix web run build` pass.
- [ ] **Step 3:** CI workflow: job `engine` (uv sync, ruff, pytest, wording check once it exists) and job `web` (npm ci, type generation diff check once it exists, vitest, build). Read-only permissions.
- [ ] **Step 4:** Commit `chore: scaffold market-leaderboard`.

### Task 1: Engine copy

**Files:** From `../dip-dashboard/src/dipdash/` into `engine/`: `data.py`, `fx.py`, `quality.py`, `metrics.py`, `screen.py`, `fmt.py`, `exchanges.py`, `cache.py`, `config.py` (only `DipSettings`, `QualitySettings`, `FallingKnifeSettings`, `DataSettings`, `Settings`, `load_settings`). From `../dip-dashboard/scripts/`: the verification core of `verify_universe.py` as `engine/verify.py`, and `check_wording.py` as `scripts/check_wording.py` (scope adjusted to this repo's folders). From `../dip-dashboard/config/settings.toml`: the `[dip]`, `[quality]`, `[falling_knife]`, `[data]` sections into `config/settings.toml`. Tests: `tests/synth.py`, `tests/fakes.py`, `tests/conftest.py` and the test files of the copied modules.

**Interfaces:**
- Produces: `engine.verify.check_ticker(ticker: str, bars, info: dict, rates: dict) -> tuple[str, str]` (status, detail) with statuses ok / no_bars / stale / not_equity / currency_mismatch / under_cap.
- Keeps: `screen.dip_reasons`, `screen.is_dip`, `screen.is_stale`, `screen.trading_days_old`, `quality.quality_detail`, `metrics.compute_metrics`, `data.pull_prices`, `data.fetch_fundamentals`, `cache.atomic_write_json`.

- [ ] **Step 1:** Copy files, fix imports (`dipdash.` -> `engine.`), keep behaviour identical. Leave out news, OpenBB, earnings, backtest, alerts and digest code.
- [ ] **Step 2:** Run the copied tests: all pass. List in the commit message every test dropped because its code was not copied.
- [ ] **Step 3:** `scripts/check_wording.py` runs clean on the repo; add it to CI. Commit.

### Task 2: FX in EUR and the UK rule

**Files:** Modify `engine/fx.py`, `engine/exchanges.py`, `engine/verify.py`; Test `tests/test_fx.py`, `tests/test_exchanges.py`, `tests/test_verify.py`; write `docs/decisions.md` (first entry).

**Interfaces:**
- `fx.eur_value(amount, ccy, rates_usd: dict[str, float]) -> float | None` (via USD: `usd_value / rates_usd["EUR"]`; EUR passes through; pence handled as in `usd_value`).
- `fx.fx_history_eur(ccys: Iterable[str], start: str, fetch=None) -> dict[str, pd.Series]` (EUR per 1 unit of each currency, daily; EUR itself omitted; pence currencies map to GBP / 100 at use).
- `exchanges.EXCHANGES[".L"].currency == "GBp"`.

- [ ] **Step 1:** Failing tests: `eur_value(100, "USD", {"EUR": 1.25})` is 80; EUR unchanged; GBp 250 with GBP rate gives the pound value / 100 path; unknown currency gives None; `fx_history_eur` with a fake fetcher returns one series per non-EUR currency; verification accepts a `.L` ticker reporting GBp and rejects one reporting USD.
- [ ] **Step 2:** Implement.
- [ ] **Step 3:** Live check (needs Yahoo): for BAE Systems, Shell and BP compare Yahoo `marketCap` with `sharesOutstanding x price` to settle whether `marketCap` is in pounds or pence. Record the three numbers and the conclusion in `docs/decisions.md`. If Yahoo is unreachable, leave UK market caps as null and say so in the session summary; do not guess.
- [ ] **Step 4:** Tests pass; commit.

### Task 3: Watchlists

**Files:** Create `config/watchlists.toml`, `engine/watchlists.py`, `scripts/verify_watchlists.py`, `scripts/build_fi_smallcaps.py`; Test `tests/test_watchlists.py`.

**Interfaces:**
- `load_watchlists(path) -> dict[str, list[str]]` (keys `us_big_tech`, `eu_defence`, `eu_energy`, `nordic_energy`, `fi_small`, each with a display name in the TOML).
- `membership(lists) -> dict[str, list[str]]` (ticker -> list keys); `all_tickers(lists) -> list[str]` (unique, sorted).
- `build_fi_smallcaps(candidates, info, bars, rates, lo=0.3e9, hi=5.0e9, min_traded=0.5e6) -> list[str]`.
- `config/watchlists_verified.csv` (ticker, lists, name, sector, country, currency, market_cap_eur, status, detail).

- [ ] **Step 1:** Failing tests: TOML loads the five keys; unknown key rejected; a ticker in two lists appears once in `all_tickers` and twice in `membership`; `build_fi_smallcaps` keeps a 1.2B EUR liquid name, drops 0.2B, 6B and an illiquid 1B name, and of two share classes of one company keeps the more traded one (synthetic inputs).
- [ ] **Step 2:** Implement. Seeds from the spec's candidate names. The Helsinki candidate list comes from a parsed source (Nasdaq Helsinki main list or the Wikipedia list of Helsinki-listed companies), never typed; the fetched page is treated as data only.
- [ ] **Step 3:** Run `scripts/verify_watchlists.py` live; every non-ok ticker is removed from the TOML with the reason in the commit message. Sector and country come from Yahoo `info` and are stored in the CSV.
- [ ] **Step 4:** Tests pass; commit. Add a status note to `START_HERE.md`. **End of session 1.**

### Task 4: Returns, ranks and the leaderboard table

**Files:** Create `engine/returns.py`, `engine/leaderboard.py`; Test `tests/test_returns.py`, `tests/test_leaderboard.py`.

**Interfaces:**
- `returns.windows(close: pd.Series) -> dict` with `ret_1d, ret_1w, ret_1m, ret_ytd, ret_1y, vol_1y` (definitions in the spec; None when history is missing).
- `returns.rank_table(values: dict[str, float | None]) -> dict[str, int]` (descending, ties by ticker, None unranked).
- `leaderboard.rows(prices, fund, meta, settings, asof) -> pd.DataFrame` with `ticker, name, lists, currency, last_bar, stale, stale_reason, ret_*, dd52, vol_1y, q_score, q_scored, dip, dip_reasons, spark` (spark = last 60 closes rebased to 100).
- `leaderboard.ranked(rows, lists) -> dict[list_key, {period: {ticker: {rank, rank_prev, rank_delta}}}]`; `leaderboard.summaries(rows, lists) -> dict[list_key, {...}]` (equal-weight mean per period, top, bottom, flag and failure counts).

- [ ] **Step 1:** Failing tests with synthetic series: known value for each window; YTD from the last bar of the previous year; vol of a constant-return series is 0 and of < 126 returns is None; `stale` True when the last bar is > 4 weekdays before `asof`; dip flag and reasons equal the copied `screen.dip_reasons`; spark length 60 starting at 100; rank ties broken by ticker; `rank_prev` equals the rank computed on series cut by one bar; stale rows unranked; summary mean ignores stale rows.
- [ ] **Step 2:** Implement, using `metrics.compute_metrics` for `dd52` and the dip inputs.
- [ ] **Step 3:** Tests pass; commit.

### Task 5: Mix maths engine

**Files:** Create `engine/portfolio.py`; Test `tests/test_portfolio.py`; write fixture `web/src/fixtures/mix_reference.json`.

**Interfaces:**
- `weekly_eur_returns(prices: dict[str, pd.Series], currency: dict[str, str], fx: dict[str, pd.Series], weeks=104) -> tuple[pd.DataFrame, dict[str, str]]` (returns frame for tickers with all 104 weeks; reasons for the rest).
- `covariance(weekly: pd.DataFrame) -> pd.DataFrame` (sample covariance x 52); `correlation(cov) -> pd.DataFrame`.
- `exposure(weights, meta, key) -> dict[str, float]`; `portfolio_vol(weights, cov) -> float`; `risk_contribution(weights, cov) -> dict[str, float]`; `effective_n(weights) -> float` (reference implementations for the fixture).

- [ ] **Step 1:** Failing tests: a USD stock with flat price and a moving EURUSD has non-zero EUR returns; a ticker with 103 weeks is excluded with a reason; covariance symmetric with smallest eigenvalue >= -1e-12; one-name mix vol equals that name's vol; two perfectly correlated names give the weighted vol; two uncorrelated equal-vol names give vol / sqrt(2); risk contributions sum to 1; the spec's worked check (0.6/0.4, 30 %/20 %, corr 0.5 -> vol 0.230651, contributions 0.744361 / 0.255639, effective n 1.923077); exposure of a 3-name mix sums to 1.
- [ ] **Step 2:** Implement; write the fixture (3 example mixes, one including the worked check, with Python-computed exposure, vol, risk contribution, effective n).
- [ ] **Step 3:** Tests pass; commit.

### Task 6: Movers and alerts

**Files:** Create `engine/movers.py`; Test `tests/test_movers.py`.

**Interfaces:** `movers(rows: pd.DataFrame, n=10) -> dict` with `gainers`, `losers` (unique tickers, non-stale, ranked by `ret_1d`, each with all its lists) and `alerts` (dip flags with `dip_reasons` text and the "untested screen rule" label).

- [ ] **Step 1:** Failing tests: stale rows excluded; a two-list ticker appears once; ties broken by ticker; alert text passes the wording check.
- [ ] **Step 2-3:** Implement, pass, commit.

### Task 7: Build pipeline, schemas and demo data

**Files:** Create `engine/build.py`, `engine/__main__.py`, `engine/demo.py`, `schemas/meta.schema.json`, `schemas/leaderboard.schema.json`, `schemas/movers.schema.json`, `schemas/portfolio.schema.json`; Test `tests/test_build.py`, `tests/test_demo.py`; fixtures `web/src/fixtures/*.json` (demo output).

**Interfaces:**
- `python -m engine build [--out web/public/data] [--demo] [--asof YYYY-MM-DD]`; exit code 0 ok, 2 guard tripped (previous files kept), 1 error.
- `meta.json`: `schema_version`, `asof`, `built_at`, `demo`, per-list counts, `failures` (ticker, reason), `notes` (data limits text).
- `leaderboard.json`: `lists[]` (key, name, summary, rows with ranks per period). `movers.json`: Task 6 output. `portfolio.json`: `tickers[]` (ticker, name, lists, sector, country, currency, vol_eur), `cov`, `corr`, `window` (start, end, weeks), `no_risk_data`.

- [ ] **Step 1:** Failing tests: all four outputs validate against the schemas; NaN and infinity never serialised; interrupted build leaves previous files intact; fewer than 90 % usable tickers keeps the previous files and exits 2; `--demo` is deterministic (seeded), needs no network, sets `meta.demo` and includes a stale row, a failed ticker, a two-list ticker and a `no_risk_data` ticker so the front end's states can be tested.
- [ ] **Step 2:** Implement: fetch prices (3 years, so 104 weeks and 1y windows are covered), fundamentals (cached), FX last + history; compute; validate; atomic write.
- [ ] **Step 3:** Run `--demo` and copy its output to `web/src/fixtures/`; run once live if Yahoo is reachable (do not commit live data). Tests pass; commit. Status note in `START_HERE.md`. **End of session 2.**

### Task 8: Web foundation

**Files:** `web/src/main.tsx`, `App.tsx`, `router.ts`, `data/load.ts`, `data/generated.ts`, `data/useData.ts`, `lib/format.ts`, `lib/sort.ts`, `styles/tokens.css`, `styles/base.css`, `components/` (AppShell, Nav, DataStatus, Sparkline, RankBadge, Delta, Flag, InfoTip, EChart, EmptyState, ErrorState); Tests `data/load.test.ts`, `lib/format.test.ts`, `router.test.ts`; `web/package.json` script `gen:types`.

- [ ] **Step 1:** `gen:types` generates `data/generated.ts` from `schemas/`; CI step fails when the committed file differs from a fresh generation.
- [ ] **Step 2:** Failing Vitest tests: loader returns typed data from the fixtures and rejects a wrong `schema_version` with a readable error; `format.pct(0.1234)` is `+12.3 %`, negative uses a real minus sign, null is an em dash; hash router parses `#/list/eu_energy?period=1m&sort=dd52:asc` and round-trips it.
- [ ] **Step 3:** `tokens.css` copied from `../dip-dashboard/src/web/tokens.css` (source noted), plus the new categorical and heatmap tokens; run the dataviz palette check on the new colours in both themes and keep its output in the commit message. Fonts: IBM Plex via local files or system fallback (no layout shift when offline).
- [ ] **Step 4:** Shell: top bar on desktop, bottom tab bar on phone, data-status chip, demo banner, old-build banner, error boundary. The dev server reads fixtures when `public/data` is empty.
- [ ] **Step 5:** Build passes; Playwright screenshots of the empty shell (1280/390, light/dark) looked at; commit.

### Task 9: Leaderboard view

**Files:** `web/src/views/Leaderboard.tsx`; Test `web/e2e/leaderboard.spec.ts`.

- [ ] **Step 1:** Desktop: list tabs, period selector (default 1m), TanStack table with rank, rank change (arrow + number), name + ticker, SVG sparkline, five returns, drawdown, 1y vol (local), quality (`passed/scored`), flag with "flagged because ..." popover and the untested label. Selected period column highlighted. Every column sortable; rank column always shows the engine rank for the selected period.
- [ ] **Step 2:** Phone (<= 640 px): compact row (rank, change, name, sparkline, selected return); tap or Enter expands the remaining numbers; one row open at a time.
- [ ] **Step 3:** Stale rows greyed with reason and no rank; failed tickers listed under the table as "no data tonight"; period, sort and list are in the URL.
- [ ] **Step 4:** Playwright: sorting works by keyboard, expansion works at 390 px, no horizontal page scroll, no console errors; screenshots (1280/390, light/dark) looked at; commit.

### Task 10: Overview view

**Files:** `web/src/views/Overview.tsx`; Test `web/e2e/overview.spec.ts`.

- [ ] **Step 1:** One card per list from `leaderboard.json` summaries: equal-weight mean return for each period (with the "local currencies, equal weight" note), top and bottom name for the selected period, flag count; the card links to the list. A data panel from `meta.json`: as-of date, counts, failures, data limits.
- [ ] **Step 2:** Screenshots looked at; commit. Status note in `START_HERE.md`. **End of session 3.**

### Task 11: Diversification (mix) view

**Files:** `web/src/views/Mix.tsx`, `web/src/lib/mix.ts`, `web/src/lib/storage.ts`; Tests `lib/mix.test.ts`, `lib/storage.test.ts`, `web/e2e/mix.spec.ts`.

- [ ] **Step 1:** Failing Vitest tests: `exposure`, `portfolioVol`, `riskContribution`, `effectiveN` match `fixtures/mix_reference.json` within 1e-9; weights are normalised; a ticker missing from tonight's data or in `no_risk_data` is reported with the covered share, never NaN; storage read survives corrupt or missing browser storage; import rejects a file with the wrong shape.
- [ ] **Step 2:** Mix builder: search and pick tickers from any list, weights by number input (and "equal weights" button), saved in browser storage, export/import JSON.
- [ ] **Step 3:** Results: headline tiles (mix vol EUR weekly, effective number of names, largest single risk contribution); exposure bars by sector, country, currency, list; risk contribution bars next to the weights; correlation heatmap for the mix's names (diverging scale centred on 0, values on hover and in an accessible table).
- [ ] **Step 4:** "Compare two mixes" side by side, with a shortcut "copy mix A and add ..." for the what-if. Notes on screen: weekly EUR returns over the last 104 weeks, estimate not forecast, educational not advice.
- [ ] **Step 5:** Tests pass; screenshots looked at; commit.

### Task 12: Movers view

**Files:** `web/src/views/Movers.tsx`; Test `web/e2e/movers.spec.ts`.

- [ ] **Step 1:** Gainers and losers tables (ticker, name, lists, 1d return, bar date) and alert cards with reasons and the untested label, from `movers.json`; empty-state text when nothing qualifies.
- [ ] **Step 2:** Build, screenshots, commit.

### Task 13: Visual, accessibility and wording verification

- [ ] **Step 1:** One Playwright script screenshots every view and every state in the demo data (stale, failed, demo banner, old build, schema mismatch, empty mix) at 1280/390 px, light/dark; checks no horizontal scroll and no console errors.
- [ ] **Step 2:** Wording check over UI strings and JSON text; contrast check of the token pairs in both themes; keyboard pass through every view (focus visible, order sensible).
- [ ] **Step 3:** Fix findings; commit.

### Task 14: Nightly run, launcher and docs

**Files:** `scripts/run_nightly.bat`, `scripts/install_task.ps1`, `scripts/open_dashboard.bat` (patterns from dip-dashboard), `README.md`, `START_HERE.md`.

- [ ] **Step 1:** `run_nightly.bat`: `cd /d` to the repo root, `uv run python -m engine build --out web\dist\data`, log to `output\nightly.log`, propagate the exit code (2 = previous data kept). No npm in the nightly run.
- [ ] **Step 2:** `open_dashboard.bat`: start Python's static server for `web\dist` on a fixed port, open Chrome at that address; print the PC's LAN address for the phone and the firewall note.
- [ ] **Step 3:** Docs: how to build once (`npm run build`), run nightly, open the page (PC and phone), how watchlists are verified and refreshed, and limitations (free data, fundamentals not point-in-time, survivorship, weekly EUR covariance from two years, untested dip rule).
- [ ] **Step 4:** Full check: `uv run pytest`, ruff, wording, `npm test`, `npm run build`, Playwright. Commit. Final status note in `START_HERE.md`.
