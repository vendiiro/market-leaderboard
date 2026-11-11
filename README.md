# market-leaderboard

A local dashboard that ranks hand-picked watchlists like a leaderboard and shows how a mix of them spreads risk
across sectors, countries and currencies:

- US big tech
- European defence
- European energy
- Nordic energy
- Finnish smaller companies (about 0.3-5 billion EUR market cap)

Educational research tool: it shows screen results and exposure views, never investment advice.

A Python engine (`engine/`) pulls daily prices from Yahoo Finance and writes four JSON files; a static React page
(`web/`) reads them. Design: `docs/spec.md`. Plan: `docs/plan.md`. Checked facts and decisions: `docs/decisions.md`.
Data code is adapted from [dip-dashboard](https://github.com/vendiiro/dip-dashboard).

## Views

- **Overview:** one card per watchlist (average return per period, highest and lowest name, flags) and the state
  of tonight's data.
- **Leaderboards:** one table per watchlist, ranked by the period you pick (1d, 1w, 1m, YTD, 1y), with the rank
  change since the previous close. Every column sorts. On a phone a row expands to show the rest.
- **Mix:** build a test mix (saved in the browser only) and see exposure by sector, country, currency and
  watchlist, mix volatility, each company's share of risk and how the companies move together. Compare two mixes.
- **Movers:** largest one-day gains and falls across all lists, and the dip flags with their reasons.

## Set up (once)

Needs Python 3.11+ with [uv](https://docs.astral.sh/uv/), Node.js LTS and Chrome.

```
uv sync
npm --prefix web install
npm --prefix web run build
```

## Use

```
scripts\run_nightly.bat        fetch tonight's data (about a minute); log in output\nightly.log
scripts\open_dashboard.bat     open the page at http://localhost:8765/
scripts\open_dashboard.bat lan also reachable from a phone on the same Wi-Fi (read the note in the file first)
```

Run the data build every night after the US close:

```
powershell -ExecutionPolicy Bypass -File scripts\install_task.ps1
```

The page must be opened through `open_dashboard.bat`: opening `web\dist\index.html` as a file does not work.
After changing code under `web/`, run `npm --prefix web run build` again; the nightly run only refreshes data.

Without network, or to try the page: `uv run python -m engine build --demo` writes invented data.

## Watchlists

`config/watchlists.toml` holds the lists as `"TICKER" = "company name"`.

- Check every ticker against Yahoo: `uv run python scripts/verify_watchlists.py`. It writes
  `config/watchlists_verified.csv` (status, sector, country, currency). The build only uses tickers whose status
  is `ok`, so run it after every edit of the TOML.
- Rebuild the Finnish list by rule, about once a month: `uv run python scripts/build_fi_smallcaps.py`, then the
  verification above. Every candidate and the reason it was kept or dropped is in `config/fi_candidates.csv`.

## Limits to keep in mind

- Free data: daily adjusted closes from Yahoo Finance. A build run during European trading hours contains that
  day's unfinished European bars; the nightly run avoids this.
- Fundamentals (the checks column) are current values, not point-in-time. Sector and country are Yahoo's.
- The watchlists hold companies that exist today, chosen today (survivorship): past returns of a list say nothing
  about how such a list would have done if picked earlier.
- Returns and 1-year volatility are in each stock's own currency. Mix risk numbers are in EUR, from weekly returns
  over the last 104 complete weeks; a company with a shorter history has no risk numbers. They are estimates from
  past data, not forecasts.
- The dip flag and the checks are untested screen rules (the dip-dashboard backtest did not support them).
- The Finnish list is built from the Finnish Wikipedia list of Helsinki-listed companies, matched to Yahoo
  tickers by name search and Wikidata; a company that neither finds is missing (see `config/fi_candidates.csv`).

## Develop

```
uv run pytest                      engine tests (offline, synthetic data)
uv run ruff check
uv run python scripts/check_wording.py
npm --prefix web test              unit tests (formulas against Python reference values, contrast of the colours)
npm --prefix web run e2e           browser tests and screenshots on demo data (uses the installed Chrome)
npm --prefix web run dev           dev server; uses web\public\data, or the demo fixtures when it is empty
npm --prefix web run gen:types     after changing schemas\*.schema.json
uv run python -m engine build --demo --out web/src/fixtures     after changing the engine's output
```
