# Market leaderboard dashboard — design

Date: 2026-11-11. Status: revision 2, reviewed against the reference code and re-approved choice by choice by the
owner on 2026-11-11 (see "Decisions"). Educational research tool: it shows screen results and diversification
views, never buy/sell advice. Wording: "candidates", "flagged because", "exposure".

## Intent and why

The reference project, dip-dashboard (https://github.com/vendiiro/dip-dashboard), screens a broad universe for
sharp drops in quality companies. The owner now wants a second, cleaner dashboard that follows a small, deliberately
chosen set of companies, ranks them like a leaderboard, and shows how a mix of them spreads (or concentrates) risk
across sectors, countries and currencies. The owner is based in Finland and the reference case is a tech-heavy
portfolio, so Finnish and Nordic names and non-tech sectors matter for balance.

## Decisions made by the owner (2026-11-11)

First round (unchanged):

- **Stack:** Python data engine (reused from dip-dashboard) writes JSON; a new React + TypeScript front end renders it.
- **Repo:** a new repository; reuse the proven Python data code; the old dashboard keeps running untouched.
- **Watchlists:** US big tech; European defence and energy; Nordic energy; Finnish smaller companies (market cap
  about 0.3-5B EUR). "European defence and energy" is stored as two lists (`eu_defence`, `eu_energy`), so there are
  five list keys and five leaderboard pages.
- **Holdings:** test mixes only; no real holdings are read.

Review round (multiple choice, 2026-11-11):

| # | Question | Owner's choice |
|---|----------|----------------|
| D1 | Covariance for the mix view | Weekly returns converted to EUR (replaces the daily lag-aware max rule) |
| D2 | UK listings (`.L`) | Included in v1, with a verified pence rule |
| D3 | How the page is opened | Local static build + a one-click launcher that starts a small local server |
| D4 | Dip flags and quality score | Shown on the leaderboard, always labelled as an untested screen rule |
| D5 | Ranking | Period selector (1d / 1w / 1m / YTD / 1y, default 1m) sets the rank; rank change vs the previous bar |
| D6 | Visual language | Same colour tokens and fonts as dip-dashboard, new layout |
| D7 | Leaderboard on a phone | Compact row (rank, name, sparkline, selected return) that expands to show the rest |
| D8 | Additions to v1 | Overview landing page; risk contribution chart in the mix view |

Not chosen (stay out of v1): benchmark index row per list, composite ranking score, public hosting, per-stock
detail page.

## Goals

1. **Overview page:** one card per watchlist (equal-weight average return per period, best and weakest name,
   number of flags) and the state of tonight's data.
2. **Leaderboard page per watchlist:** rank by the selected period, rank change, returns 1d / 1w / 1m / YTD / 1y,
   drawdown from the 52-week high, 1-year volatility, quality score and dip flag (labelled untested), sparkline.
   Every column sortable.
3. **Diversification (mix) page:** build test mixes; exposure by sector, country, currency and watchlist;
   correlation heatmap; mix volatility, effective number of names and risk contribution per name; "what changes
   if I add X" as a side-by-side comparison of two mixes.
4. **Movers page:** biggest gainers and losers across all watchlists, plus dip alerts with their reasons.
5. Runs locally in Chrome after the nightly data job; clean on desktop and phone, light and dark mode.

## Non-goals and anti-goals

- No trading, no broker connection, no "buy now/sell" wording, no price targets.
- No new paid data source in v1 (yfinance free data as today).
- Anti-goal: a pretty page whose numbers cannot be traced to the Python output. Every number on screen comes from
  the JSON the pipeline writes. The front end computes only display formatting, sorting, and the four mix formulas
  listed under "Mix maths", each unit-tested against Python reference values.
- Anti-goal: hand-typed ticker lists that were never checked. Every watchlist ticker passes Yahoo verification
  before it is used.
- Anti-goal: an invented score. Rank is always the plain order of one visible column.

## Constraints

- Free data: daily adjusted bars after the close; fundamentals not point-in-time (current view only).
- Nothing private is stored: mixes live in the browser and in exported JSON files.
- Leaderboard returns and `vol_1y` are in each stock's local currency. Mix numbers (covariance, volatility, risk
  contribution) are in EUR, the owner's base currency. The two volatility figures are labelled differently on
  screen ("1y vol, local" vs "mix vol, EUR weekly").
- The dip rule and quality score are untested screen rules (the dip-dashboard backtest did not support them). Any
  place that shows them says so.
- Wording rules and the wording check apply to all on-screen text and all text inside the JSON.

## Definitions (engine)

Bars are daily adjusted closes `c`, last bar index `T`.

- **Returns:** `ret_1d = c[T]/c[T-1] - 1`, `ret_1w` uses `T-5`, `ret_1m` uses `T-21`, `ret_1y` uses `T-252`,
  `ret_ytd` uses the last bar of the previous calendar year. Missing history gives `null`, never 0.
- **Drawdown:** `dd52 = c[T] / max(c[T-251..T]) - 1` (copied rule; uses available history when shorter).
- **Volatility:** `vol_1y = std(daily simple returns, last 252) * sqrt(252)`; `null` with fewer than 126 returns.
- **Stale:** last bar more than 4 weekdays before `asof` (copied rule). Stale rows are shown greyed with the
  reason and are never ranked and never listed as movers.
- **Rank:** for each list and each period, non-stale rows with a value are ordered by that return, descending,
  ties broken by ticker; rank 1 is the highest. `rank_prev` is the same ranking computed with every series cut at
  its previous bar (stateless: no stored history needed). `rank_delta = rank_prev - rank` (positive = moved up).
- **List summary (overview):** equal-weight mean of the non-stale members' returns per period, in local
  currencies (said on screen), the top and bottom name for the default period, counts of flags and failures.
- **Holidays:** each stock's 1d return uses its own last two bars; the row shows its own last-bar date when it
  differs from `asof`.

## Mix maths

Engine side (`portfolio.json`):

- Weekly EUR returns: for each ticker, daily close times the EUR value of one unit of its currency on that date
  (FX history from Yahoo pairs, forward-filled over FX gaps of at most 3 days), then the last value of each week
  ending Friday, then simple weekly returns.
- Window: the last 104 complete weeks. A ticker without all 104 weekly returns is left out of the covariance and
  listed in `portfolio.json` under `no_risk_data` with the reason; it can still be in a mix for exposure, and the
  mix view then says the risk numbers cover only part of the mix.
- `cov = sample covariance of weekly EUR returns * 52` (annualised). Because all tickers share one window, the
  matrix is positive semi-definite by construction (tested: smallest eigenvalue >= -1e-12). `corr` is derived
  from `cov` and written alongside it. With more tickers than weeks the matrix is singular; that is fine for the
  formulas below and is stated in the docs.
- Why weekly: European markets close before the US session, so same-day daily returns understate correlation
  between regions. Weekly returns make the timing gap a small part of each observation. This replaces the earlier
  "lag-aware max" rule. It is still an estimate from two years of data and is labelled as such.

Front end (the only financial arithmetic in the browser), with weights `w` normalised to sum to 1:

1. Exposure share of a group = sum of `w_i` over the names in the group.
2. Mix variance `w'Σw`, mix volatility `sqrt(w'Σw)`.
3. Risk contribution of name i = `w_i (Σw)_i / (w'Σw)` (sums to 1).
4. Effective number of names = `1 / sum(w_i^2)`.

Worked check (also a test case in both languages): `w = (0.6, 0.4)`, vols 30 % and 20 %, correlation 0.5 gives
variance 0.0532, volatility 23.07 %, risk contributions 74.44 % and 25.56 %, effective number 1.92.

## Architecture

```
market-leaderboard/
  pyproject.toml  uv.lock            Python 3.11+, uv; ruff + pytest config
  config/
    watchlists.toml                  seed tickers per list (verified ones only)
    watchlists_verified.csv          verification output (ticker, list, name, sector, country, currency, cap, status)
    settings.toml                    dip and quality thresholds (copied), windows, failure guard
  engine/                            Python package
    data.py fx.py quality.py metrics.py screen.py fmt.py exchanges.py cache.py config.py   copied, see plan Task 1
    verify.py                        Yahoo verification core (from scripts/verify_universe.py)
    watchlists.py                    load lists, membership (a ticker may be in several lists)
    returns.py                       return windows, vol, ranks (new metrics)
    leaderboard.py                   per-list tables and list summaries
    portfolio.py                     weekly EUR returns, covariance, per-ticker meta
    movers.py                        gainers, losers, alerts
    demo.py                          synthetic data for --demo
    build.py  __main__.py            pipeline: fetch -> compute -> validate -> atomic write; `python -m engine build`
  schemas/*.schema.json              the data contract (source of truth)
  scripts/                           verify_watchlists.py, build_fi_smallcaps.py, check_wording.py,
                                     gen_types (npm script), run_nightly.bat, install_task.ps1, open_dashboard.bat
  tests/                             pytest (synthetic data only; one live smoke test, skipped offline)
  web/
    index.html  vite.config.ts       base './' so the build works from any folder
    public/data/                     live JSON (git-ignored)
    src/
      main.tsx  App.tsx  router.ts   hash routes: #/  #/list/:id  #/mix  #/movers
      data/                          load.ts (fetch + schema_version check), generated.ts (types from schemas), useData.ts
      lib/                           format.ts, mix.ts, storage.ts, sort.ts
      components/                    AppShell, Nav, DataStatus, Sparkline (SVG), RankBadge, Delta, Flag, InfoTip,
                                     EChart (one wrapper, modular imports), EmptyState, ErrorState
      views/                         Overview.tsx, Leaderboard.tsx, Mix.tsx, Movers.tsx
      styles/                        tokens.css (from dip-dashboard), base.css
      fixtures/                      demo JSON + mix_reference.json (committed)
    e2e/                             Playwright screenshots and checks
  .github/workflows/ci.yml           pytest, ruff, wording check, type generation diff, vitest, web build
```

- **Contract:** `meta.json`, `leaderboard.json`, `movers.json`, `portfolio.json`, each with `schema_version`.
  JSON Schemas in `schemas/` are the source of truth; Python validates its output against them before writing;
  TypeScript types are generated from them (`json-schema-to-typescript`) and CI fails if the generated file is
  out of date.
- **Pipeline safety:** files are written to temp names and renamed; if fewer than 90 % of tickers return usable
  data the build keeps the previous files and records the failure in `output/nightly.log` (guard copied from
  dip-dashboard's daily run). NaN and infinity are never written (null instead).
- **Demo mode:** `python -m engine build --demo` writes the same four files from seeded synthetic data. It is
  used for fixtures, Playwright, CI and cloud sessions without Yahoo access. The page shows a "demo data" banner
  when `meta.demo` is true.
- **Opening the page:** `scripts/open_dashboard.bat` serves `web/dist` with Python's built-in static server on
  a fixed local port and opens Chrome. A phone on the same Wi-Fi can open the PC's address (documented, with the
  Windows firewall note). The nightly job refreshes only the JSON in `web/dist/data`; `npm run build` is needed
  only after code changes.
- **Scheduling:** Windows Task Scheduler pattern from dip-dashboard, after the US close, Helsinki time.

## Front end design

- **Tokens:** `styles/tokens.css` starts as a copy of dip-dashboard `src/web/tokens.css` (surface, ink, line,
  accent, up = blue, down = red, status colours, IBM Plex families with system fallbacks, light and dark). New
  tokens: a categorical palette for sectors/lists/currencies (validated with the dataviz palette check in both
  themes) and a sequential-diverging pair for the correlation heatmap.
- **Direction is never colour alone:** every change shows a sign and, for rank, an arrow.
- **Shell:** top bar with the four destinations and a data-status chip ("Data as of 2026-11-10 · 3 tickers
  without data"); on a phone the destinations become a bottom tab bar. One main landmark, visible focus, all
  controls reachable by keyboard, hit areas at least 44 px on touch.
- **Leaderboard, desktop:** list tabs, period selector, full table (rank, change, name + ticker, sparkline,
  five returns, drawdown, vol, quality, flag). Numbers right-aligned in the mono face with tabular figures; the
  selected period's column is highlighted. Sort state and period live in the URL so a view can be bookmarked.
- **Leaderboard, phone (<= 640 px):** compact row with rank, change, name, sparkline and the selected period's
  return; tapping a row expands the remaining numbers below it. No horizontal scrolling.
- **Sparklines** are inline SVG (about 80 rows; no chart instance per row). ECharts is used only for exposure
  bars, risk contribution bars and the heatmap, imported modularly.
- **States:** loading, empty, stale row, failed ticker ("no data tonight" + reason), old build banner, demo
  banner, schema mismatch error. None of them shows NaN or a blank page.
- **Text:** English, plain, short; every term that is not everyday language has an InfoTip definition; the mix
  page carries the notes "weekly EUR returns, last 104 weeks" and "educational, not advice"; flags carry
  "untested screen rule".

## Watchlist definitions (ticker lists built and verified in session 1, never typed from memory unchecked)

- **US big tech:** the largest US technology and communication companies by market cap (seed: NVDA, MSFT, AAPL,
  GOOGL, AMZN, META, AVGO, TSLA, ORCL, AMD), capped at about 15 names.
- **EU defence:** listed European defence primes and suppliers (seed candidates to verify: Rheinmetall, BAE Systems,
  Leonardo, Thales, Saab, Kongsberg, Hensoldt, Renk, Dassault Aviation, Safran).
- **EU energy:** integrated oil and gas, utilities and renewables (seed candidates: Shell, TotalEnergies, BP, Eni,
  Equinor, Repsol, Iberdrola, Enel, Engie, Vestas, Ørsted).
- **Nordic energy:** Nordic-listed energy names (seed candidates: Neste, Fortum, Equinor, Aker BP, Vestas, Ørsted,
  Vår Energi).
- **Finnish smaller caps:** Nasdaq Helsinki main-list shares with market cap 0.3-5B EUR and median 60-day traded
  value of at least 0.5M EUR, rebuilt monthly by rule. A company with two share classes keeps only the class with
  the higher median traded value.
- A ticker may belong to several lists (Equinor, Vestas, Ørsted). It appears on each list's page, but movers,
  covariance and the mix picker use each ticker once and show all its lists.
- **UK listings:** `.L` is registered with trading currency GBp. Verification requires Yahoo to report GBp (or
  GBX). Whether Yahoo's `marketCap` for `.L` is in pounds or pence is checked in session 1 against
  shares outstanding times price for each UK name, and the result is written down before any cap in EUR is shown.

## Open questions for the owner (do not block the build)

- Hosting later: stay local, or a private hosted page? (The build is static, so this can be added without rework.)
- Benchmark index per list and a per-stock detail page are candidates for v2.

## Verification

Python unit tests on synthetic data (returns, ranks, covariance properties, exposure maths), JSON schema tests,
ruff, a TypeScript strict build, Vitest tests of the four mix formulas against Python reference values, the
wording check, and Playwright screenshots at 1280 and 390 px in light and dark mode, looked at before any view is
called done. Playwright also checks: no horizontal page scroll, no console errors, contrast of the token pairs.

## Left to the builder

Component internals, exact new colour values (validated), port number of the launcher, wording of the InfoTips.
