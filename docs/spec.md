# Market leaderboard dashboard — design

Date: 2026-11-11. Status: approved by the owner on 2026-11-11. Educational research tool: it shows screen results and
diversification views, never buy/sell advice. Wording: "candidates", "flagged because", "exposure".

## Intent and why

The reference project, dip-dashboard (https://github.com/vendiiro/dip-dashboard), screens a broad universe for
sharp drops in quality companies. The owner now wants a second, cleaner dashboard that follows a small, deliberately
chosen set of companies, ranks them like a leaderboard, and shows how a mix of them spreads (or concentrates) risk
across sectors, countries and currencies. The owner is based in Finland and the reference case is a tech-heavy
portfolio, so Finnish and Nordic names and non-tech sectors matter for balance.

## Decisions made by the owner (2026-11-11)

- **Stack:** Python data engine (reused from dip-dashboard) writes JSON; a new React + TypeScript front end renders it.
- **Repo:** a new repository; reuse the proven Python data code; the old dashboard keeps running untouched.
- **Watchlists (four):**
  1. US big tech (e.g. Nvidia, Microsoft and peers).
  2. European defence and energy.
  3. Nordic energy.
  4. Finnish smaller companies, market cap about 0.3-5B EUR.
- **First-version views:** leaderboard per watchlist, diversification view, daily movers and alerts.
  (A per-stock detail page is v2.)

## Goals

1. One page per watchlist ranked like a leaderboard: returns 1d / 1w / 1m / YTD / 1y, drawdown from 52-week high,
   volatility, quality score and dip flag (reusing the existing rules), sortable, with sparkline charts.
2. Diversification view: for a holdings file (or a test mix), exposure by sector, country, currency and watchlist;
   a correlation heatmap; a simple "what changes if I add X" comparison of concentration and volatility.
3. Daily movers: biggest gainers and losers across all watchlists, plus the existing dip alerts.
4. Runs locally in Chrome after the nightly data job; clean on desktop and phone, light and dark mode.

## Non-goals and anti-goals

- No trading, no broker connection, no "buy now/sell" wording, no price targets.
- No new paid data source in v1 (yfinance/OpenBB free tiers as today).
- Anti-goal: a pretty page whose numbers cannot be traced to the Python output (every number on screen comes from
  the JSON the pipeline writes; the front end computes nothing financial except display formatting).
- Anti-goal: hand-typed ticker lists that were never checked. Every watchlist ticker passes the existing Yahoo
  verification (bars, currency, quote type) before it is used.

## Constraints

- Free data: daily adjusted bars after the close; fundamentals not point-in-time (current view only).
- Holdings are private: the holdings file stays local and git-ignored; nothing is uploaded.
- Correlations are lag-aware (European and Asian markets close before or during the US session): for a pair where
  exactly one name is non-US, correlation = max(same-date correlation, correlation of the non-US return on day t
  with the US return of the latest US trading day strictly before t); other pairs use same-date returns. The max is
  deliberately conservative (slightly upward-biased) so non-US names do not look more diversifying than they are.
  Documented on screen.
- Currency: returns shown in local currency; portfolio exposure converted to EUR (the owner's base currency) with the existing FX code.
- Wording rules and the check_wording script apply to all on-screen text.

## Architecture (designer's call)

- `engine/` (Python 3.11, uv): copied from dip-dashboard (`src/dipdash/`, branch `dashboard-brief-compact-table`,
  commit f14d55c on GitHub): `data.py` (pull_prices with retries), `fx.py`,
  `quality.py`, `metrics.py`, `exchanges.py`, `cache.py`, the Yahoo verification from `verify_universe.py`.
  New: `watchlists.py` (load and verify lists), `leaderboard.py` (per-list ranking table), `portfolio.py`
  (exposure, correlation, what-if), `build.py` (writes `web/public/data/*.json` + a schema version).
- `web/` (React + TypeScript + Vite; charts with Apache ECharts; table with TanStack Table): reads the JSON files,
  no backend server needed; `npm run build` gives a static folder that opens in Chrome.
- Contract: a JSON schema per file (`leaderboard.json`, `movers.json`, `portfolio.json`, `meta.json`), validated in
  Python tests and in a TypeScript type test, like the current payload contract.
- Scheduling: reuse the Windows Task Scheduler pattern (after the US close, Helsinki time).

## Watchlist definitions (designer's call; ticker lists built and verified in session 1, never typed from memory unchecked)

- **US big tech:** the largest US technology and communication companies by market cap (seed: NVDA, MSFT, AAPL,
  GOOGL, AMZN, META, AVGO, TSLA, ORCL, AMD), capped at about 15 names.
- **EU defence:** listed European defence primes and suppliers (seed candidates to verify: Rheinmetall, BAE Systems,
  Leonardo, Thales, Saab, Kongsberg, Hensoldt, Renk, Dassault Aviation, Safran).
- **EU energy:** integrated oil and gas, utilities and renewables (seed candidates: Shell, TotalEnergies, BP, Eni,
  Equinor, Repsol, Iberdrola, Enel, Engie, Vestas, Ørsted).
- **Nordic energy:** Nordic-listed energy names (seed candidates: Neste, Fortum, Equinor, Aker BP, Vestas, Ørsted,
  Vår Energi).
- **Finnish smaller caps:** all Nasdaq Helsinki main-list shares with market cap 0.3-5B EUR and median daily traded
  value above a floor (designer's call: 0.5M EUR), refreshed monthly by rule like the universe refresh.
- UK (.L) listings need the pence/pounds currency rule settled first (open item in the old repo).

## Holdings input (owner, 2026-11-11): test mixes only

No real holdings are read. In the diversification view the owner builds example mixes (ticker + weight) in the page,
saved in the browser and exportable/importable as a small JSON file. Consequence for the anti-goal above: the engine
supplies per-ticker sector, country, currency, volatility and the covariance/correlation matrix; the page only does
weighted sums (exposure shares) and the portfolio-volatility formula sqrt(w'Σw) on those engine numbers. Both formulas
get TypeScript unit tests checked against reference values computed in Python.

## Open questions for the owner (do not block session 1)

- Hosting later: local only, or a private hosted page?
- Should the old dashboard's dip flags appear on the leaderboard, or stay in the old dashboard only?

## Verification

Python unit tests on synthetic data (rankings, exposure maths, correlation), JSON schema tests, a TypeScript build
with strict types, and Playwright screenshots at desktop and phone width in light and dark mode before calling any
view done (same rule as the current project).

## Left to the builder

Component structure, exact colour tokens (validated with the dataviz palette check), file layout inside `web/`.
