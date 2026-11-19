# Portfolio page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Portfolio page (the landing page) that shows the owner's real holdings from a private local file and lets him research additions (shares and ETFs) in a basket, with the effect on weights, concentration, correlation and volatility.

**Architecture:** The engine reads a gitignored `config/portfolio.toml` (holdings) and an optional Nordnet history CSV, prices the holdings and the ETF candidates like any other ticker, writes a sixth file `holdings.json` and adds the holdings and ETFs to the existing covariance matrix in `portfolio.json`. The page computes before and after in the browser from that matrix, reusing `web/src/lib/mix.ts`, as the Mix view does.

**Tech Stack:** Python 3.11 (`uv`, pandas, pytest, ruff), TypeScript strict + React 19, Vitest, Playwright, oxlint. No chart library, no new dependency.

**Spec:** `docs/superpowers/specs/2026-11-15-portfolio-page-design.md` (builds on `2026-11-12-research-workstation-design.md` and `docs/spec.md`). Read `CLAUDE.md` first.

## Global Constraints

- **Privacy:** the repo is public. `config/portfolio.toml` is gitignored (done). No real holding, value, account number or Nordnet figure in any tracked file, test, fixture, doc, commit message or screenshot. Tests and fixtures use only the invented demo portfolio. The mockups under `.superpowers/` hold real numbers: read them for layout, never copy numbers.
- Educational tool, no advice. `scripts/check_wording.py` bans (among others) "sell", "bargain", "undervalued", "top picks", "expected return", "should hold" in `engine/`, `config/`, `schemas/`, `web/src/`. Write "locked" or "not modelled", never "no selling". Card and table text is fixed templates; no judgement adjectives.
- Theme: warm paper only; reuse tokens from `web/src/styles/tokens.css`. No new colour without the contrast test (`web/src/styles/tokens.test.ts`) passing. Direction is never shown by colour alone (use ▲ ▼ or signs).
- Mix risk numbers: weekly returns in EUR over the last 104 complete weeks (`engine/portfolio.py`, `WEEKS = 104`). Estimates, not forecasts; say so on the page. A ticker without the full window gets a stated reason, never a number.
- Types in `web/src/data/generated/` are generated from `schemas/` (`npm run gen:types`), never hand-edited. No chart library: inline SVG, HTML and CSS.
- Tests first, one task at a time, commit after each task (message ends with the attribution line the session requires). Tests run offline on synthetic data. After any UI change, take Playwright screenshots at 1280 and 390 px, light and dark, and look at them.
- Money in the data is EUR; returns of a single holding are in its quote currency; UK lines are pence (`PENCE` in `engine/fx.py`).
- Schema version goes from 2 to 3 (all schemas, `engine/build.py` `SCHEMA_VERSION`, `web/src/data/load.ts` `SCHEMA_VERSION`, tests that assert 2).

## Review Focus

Inputs the spec implies but its tasks would not otherwise exercise; each has a test in the named task.

1. A holding whose ticker returns no prices tonight: value is null, it is left out of totals, the page shows "no price", never NaN or a wrong total (Task 4, Task 7).
2. A portfolio where nothing has risk data (only funds, or all tickers failed): volatility and risk contribution read "no risk data", never NaN (Task 6).
3. A basket with zero, negative or non-numeric amounts, or a ticker not in tonight's data: ignored with a stated reason; an empty basket shows before equal to after (Task 6).
4. A history CSV that is missing, empty, has one row, or is not UTF-16: the build continues without history and says why; the page hides the chart (Task 2, Task 5).
5. A candidate (share or ETF) with fewer than 104 weeks of history: correlation and volatility read "—" with the reason (Task 5, Task 6).
6. A holding that is also on a watchlist (the same ticker twice): counted once everywhere (Task 5).

## File Structure

- Create `engine/holdings.py`: holdings file reader, position and total maths, ETF rows, basket reference fixture.
- Create `engine/history.py`: Nordnet CSV reader and summary.
- Modify `engine/watchlists.py` (list `kind`, entry `group`), `engine/verify.py` (ETF quote types), `engine/build.py`, `engine/demo.py`, `scripts/verify_watchlists.py`.
- Create `schemas/holdings.schema.json`; modify the other schemas (version 3).
- Create `config/portfolio.example.toml`.
- Create `web/src/lib/basket.ts`, `web/src/lib/basket-storage.ts`, `web/src/components/portfolio.tsx`, `web/src/components/additions.tsx`, `web/src/views/Portfolio.tsx`, `web/src/styles/portfolio.css`; modify `web/src/router.ts`, `web/src/App.tsx`, `web/src/data/load.ts`.
- Tests: `tests/test_holdings.py`, `tests/test_history.py`, `tests/test_privacy.py`, additions to `tests/test_watchlists.py`, `tests/test_verify.py`, `tests/test_build.py`; `web/src/lib/basket.test.ts`, `web/e2e/portfolio.spec.ts`.

---

### Task 1: Holdings file reader and privacy test

**Files:** Create `engine/holdings.py` (reader part), `config/portfolio.example.toml`, `tests/test_holdings.py`, `tests/test_privacy.py`.

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Holding: name: str; kind: str; ticker: str | None; quantity: float | None; cost_price: float | None; cost_eur_total: float | None; value_eur: float | None; group: str | None`. `kind` is one of `KINDS = ("stock", "etf", "etn", "fund")`.
  - `@dataclass(frozen=True) class Holdings: label: str; holdings: list[Holding]; history_csv: Path | None`.
  - `read_holdings(path: Path | str | None = None) -> Holdings | None`. Default path `config/portfolio.toml`. Returns `None` when the default file does not exist (the build then has no portfolio); a path given explicitly that does not exist raises `FileNotFoundError`.
- TOML format (the example file, with invented values): top-level `label`, optional `history_csv`; one `[[holding]]` table per holding with keys `name`, `kind`, `ticker`, `quantity`, `cost_price`, optional `cost_eur_total`, optional `group`; a fund without a Yahoo ticker has `name`, `kind = "fund"`, `value_eur` and no `ticker`.

- [ ] **Step 1: Write failing tests** in `tests/test_holdings.py`: `test_reads_the_example_file` (loads `config/portfolio.example.toml`; asserts at least one stock with `cost_eur_total` set, one ETF, one fund with `ticker is None` and `value_eur` set); `test_missing_default_file_is_none` (monkeypatch the default path to a tmp dir; `read_holdings() is None`); `test_explicit_missing_file_raises`; parametrised `test_rejects_bad_files` for: unknown `kind`, duplicate ticker, a ticker without `quantity` or `cost_price`, a fund without ticker and without `value_eur`, negative quantity, unknown key (error text names the key and the holding). In `tests/test_privacy.py`: `test_portfolio_file_is_ignored_by_git` (`git check-ignore config/portfolio.toml` exits 0) and `test_no_tracked_file_is_the_private_file` (`git ls-files` does not list `config/portfolio.toml` nor any path ending `.private.toml`).
- [ ] **Step 2:** Run `uv run pytest tests/test_holdings.py tests/test_privacy.py -q`. Expected: FAIL (module missing); the privacy tests already pass.
- [ ] **Step 3:** Implement `read_holdings` with `tomllib`, validating as the tests list; error messages start with `portfolio.toml` and name the holding. Write `config/portfolio.example.toml` with 3 to 4 invented holdings matching the demo universe tickers in `engine/demo.py` (for example `DEMA`, `DEFA.DE`) plus one invented ETF ticker `DEMETF.DE` and one invented fund.
- [ ] **Step 4:** Run the same command and `uv run ruff check engine tests`. Expected: PASS, no lint errors.
- [ ] **Step 5: Commit** `engine/holdings.py config/portfolio.example.toml tests/test_holdings.py tests/test_privacy.py`.

---

### Task 2: Nordnet history reader and summary

**Files:** Create `engine/history.py`, `tests/test_history.py`.

**Interfaces:**
- Produces:
  - `read_nordnet_csv(path: Path | str) -> list[dict]`: one dict per row, `{"date": "YYYY-MM-DD", "value": float, "cum": float, "net_deposits": float}`; `cum` is the accumulated return as a fraction (the file's percent column divided by 100). Raises `ValueError` with a plain message for: missing file, empty file, wrong encoding, a header that does not have 7 columns, an unparseable number (message names the row).
  - `summarise(points: list[dict], asof: str) -> dict` with keys `since_start`, `month`, `ytd`, `max_drawdown` (a negative fraction), `drawdown_from`, `drawdown_to` (dates), `lowest` and `highest` (`{"date", "cum"}`). `month` and `ytd` are `None` when there is no earlier weekly point.
- File format (verified on the owner's real file, 2026-11-15): UTF-16 with a byte order mark, tab-separated, decimal comma, percent signs in the percent columns, minus sign `-`, one row per week; columns date, total value, daily development %, accumulated return %, daily development EUR, accumulated return EUR, net deposits EUR. Use column positions 0, 1, 3, 6.

- [ ] **Step 1: Write failing tests.** Each builds a small file in `tmp_path` with `.encode("utf-16")`. `test_parses_decimal_comma_percent_and_minus` (a row `2025-04-04\t1000,50\t-1,25%\t-10,00%\t...` gives `cum == -0.10`, `value == 1000.5`). `test_summary_chains_the_cumulative_return` (points with cum 0, 0.10, -0.05, 0.20: `since_start == 0.20`; `month` equals `(1+last)/(1+point_at_nearest_earlier_to_asof_minus_one_month) - 1` for an exact worked case you compute by hand in the test). `test_max_drawdown` (index `1+cum`: peak 1.20, trough 0.90 gives `-0.25`; assert `pytest.approx(-0.25)` and the two dates). `test_ytd_none_when_history_starts_this_year`. `test_bad_files` (parametrised: missing, empty, UTF-8 encoded, 5 columns, `abc` as a number; each raises `ValueError` and the message contains "history").
- [ ] **Step 2:** Run `uv run pytest tests/test_history.py -q`. Expected: FAIL.
- [ ] **Step 3:** Implement both functions. Nearest earlier point means the last point with date less than or equal to the boundary date; `month` boundary is `asof` minus one calendar month, `ytd` boundary is the previous 31 December.
- [ ] **Step 4:** Run tests and ruff. Expected: PASS.
- [ ] **Step 5: Commit.**

---

### Task 3: ETF lists, entry groups, ETF verification

**Files:** Modify `engine/watchlists.py`, `engine/verify.py`, `scripts/verify_watchlists.py`, `tests/test_watchlists.py`, `tests/test_verify.py`.

**Interfaces:**
- `watchlists.read()` result per list gains `"kind": str` (default `"stock"`; the only other value is `"etf"`) and `"groups": dict[str, str]` (ticker to group tag). An entry value in the TOML may be a string (company name, as today) or an inline table `{ name = "...", group = "technology" }`. A list-level `kind = "etf"` key marks an ETF list. Existing files read unchanged.
- `verify.classify_row(..., kind: str = "stock")`: for `kind == "etf"` the accepted Yahoo `quoteType` values are `{"ETF", "MUTUALFUND"}` instead of `"EQUITY"` (status `not_equity` stays the flag name; its detail text says what was expected). Everything else is unchanged.
- `watchlists.all_tickers` and `membership` are unchanged; add `split_by_kind(cfg: dict[str, dict]) -> tuple[dict, dict]` returning `(stock_cfg, etf_cfg)` with the same shape as `cfg`.

- [ ] **Step 1: Write failing tests:** `test_read_defaults_kind_to_stock_and_accepts_inline_tables`, `test_read_rejects_unknown_kind`, `test_inline_table_needs_a_name`, `test_split_by_kind`, and in `tests/test_verify.py` `test_etf_quote_type_is_accepted_for_etf_kind` and `test_etf_is_not_equity_for_stock_kind`.
- [ ] **Step 2:** Run `uv run pytest tests/test_watchlists.py tests/test_verify.py -q`. Expected: FAIL.
- [ ] **Step 3:** Implement. In `scripts/verify_watchlists.py` pass `kind=cfg[...]["kind"]` for each ticker (look the kind up through `membership`).
- [ ] **Step 4:** Run the same command plus the whole suite `uv run pytest -q`. Expected: PASS (existing tests unchanged).
- [ ] **Step 5: Commit.**

---

### Task 4: Positions, totals and ETF rows (pure maths)

**Files:** Modify `engine/holdings.py`; extend `tests/test_holdings.py`.

**Interfaces:**
- Consumes: `Holding`, `Holdings` (Task 1); `portfolio.eur_prices(close, ccy, fx)` from `engine/portfolio.py`; `metrics.compute_metrics(close, volume)` (keys `price`, `ret_1y`, `dd52`, `vol_1y`).
- Produces:
  - `position_rows(h: Holdings, prices: dict[str, pd.Series], currency: dict[str, str | None], sector: dict[str, str | None], fx: dict[str, pd.Series], risk_tickers: set[str]) -> list[dict]`. One dict per holding with keys `key` (ticker, or `fund:<name>`), `ticker`, `name`, `kind`, `group`, `currency`, `sector`, `quantity`, `price` (latest close, quote currency), `value_eur`, `cost_eur`, `cost_approx` (bool), `result_eur`, `return_local` (price / cost_price - 1), `weight` (value share of the portfolio, `None` if no value), `has_risk` (ticker in `risk_tickers`), `note` (`"no price tonight"` when a ticker has no prices; `None` otherwise). `value_eur` is quantity times the latest EUR price; a fund uses its `value_eur`, has no cost, result, return or risk. `cost_eur` is `cost_eur_total` when given (`cost_approx = False`), else quantity times cost price converted with the ratio of the latest EUR price to the latest quote price (`cost_approx = True`).
  - `totals(positions: list[dict], tech_group: str = "technology") -> dict` with `value_eur`, `result_eur` (sum over positions that have a result), `result_complete` (every priced non-fund position has one), `top3_share`, `tech_share` (weight of positions whose `group == tech_group`), `risk_covered` (weight of positions with `has_risk`), `unpriced` (count). Weights are over priced positions only.
  - `etf_rows(cfg_etf: dict[str, dict], prices: dict[str, tuple], currency: dict[str, str | None]) -> list[dict]` with `ticker`, `name`, `list`, `group` (entry group or `None`), `currency`, `price`, `ret_1y`, `dd52`, `vol_1y` (`None` when fewer than 60 closes, as `compute_metrics` returns).
  - `reference_baskets() -> dict`: fixed small inputs (three positions, a 3 x 3 covariance, two baskets) and their results computed with `engine/portfolio.py` functions, in the shape `web/src/lib/basket.test.ts` reads (see Task 6); the demo build writes it to `web/src/fixtures/basket_reference.json` through `python -m engine.holdings`.

- [ ] **Step 1: Write failing tests** with synthetic series: `test_usd_holding_value_uses_the_eur_rate` (10 shares at 50 USD, EUR per USD 0.9 gives `value_eur == 450.0`), `test_gbp_pence_holding` (price 1000 pence, 10 shares, rate EUR per GBP 1.2 gives 120.0), `test_cost_eur_total_wins_and_is_not_approximate`, `test_cost_is_approximate_without_cost_eur_total`, `test_fund_with_manual_value_counts_in_value_not_in_risk`, `test_unpriced_holding_is_left_out_of_totals` (value `None`, note "no price tonight", `unpriced == 1`, weights of the others sum to 1), `test_totals_top3_and_tech_share` (worked numbers), `test_etf_rows_short_history_has_none_metrics`.
- [ ] **Step 2:** Run `uv run pytest tests/test_holdings.py -q`. Expected: FAIL.
- [ ] **Step 3:** Implement. Use `eur_prices(...).iloc[-1]` for the latest rate-converted price; never divide by a zero quote price (treat as no price).
- [ ] **Step 4:** Run tests and ruff. Expected: PASS.
- [ ] **Step 5: Commit.**

---

### Task 5: Build wiring, schemas v3, demo data, fixtures

**Files:** Modify `engine/build.py`, `engine/demo.py`, `schemas/*.schema.json`, `web/src/data/load.ts`, `tests/test_build.py` (and any test asserting version 2); create `schemas/holdings.schema.json`; regenerate `web/src/fixtures/*.json` and `web/src/data/generated/*`.

**Interfaces:**
- `build.FILES` becomes `("leaderboard", "movers", "portfolio", "research", "holdings", "meta")` (meta stays last). `SCHEMA_VERSION = 3`.
- `holdings.json` (new schema, `additionalProperties: false` everywhere): `schema_version`, `asof`, `label` (string), `positions` (array of the Task 4 position dict), `totals` (the Task 4 totals dict), `history` (null, or `{"points": [{date, value, cum, net_deposits}], "summary": {...Task 2 keys}}`), `history_note` (string or null: why there is no history), `etfs` (array of the Task 4 ETF row). When there is no holdings file the file is still written with empty `positions`, zero totals, `history: null`, `etfs` as available, so the page can say "no portfolio file" instead of failing.
- `build.compute(inp, ...)` reads optional inputs `inp["holdings"]` (`Holdings | None`), `inp["history"]` (list from `read_nordnet_csv`, or `None`), `inp["extra"]` (`{ticker: {name, lists, currency, sector, country}}` for holding-only tickers and ETFs; never also in `inp["meta"]`). `leaderboard.rows` still sees only `inp["meta"]` and `inp["cfg"]` filtered by `watchlists.split_by_kind` to stock lists, so holdings and ETFs never appear in Candidates, Screener or Watchlists. `portfolio.weekly_eur_returns` runs on the live universe plus every `extra` ticker that has prices; `portfolio.json` `tickers` gets one entry per extra ticker (`lists` is `["holdings"]` or the ETF list key); risk reasons for extras go into `no_risk_data`.
- `live_inputs`: reads `config/portfolio.toml` and the history CSV; fetches 3-year prices for holding tickers and ETF-list tickers (same `fetch_prices`); ETF tickers must be `ok` in `watchlists_verified.csv`; a holding ticker with fewer than 60 closes goes to `reasons` (the position shows "no price tonight"). A history file error is caught, printed, and becomes `history_note`; it never fails the build.
- `demo.inputs()` gains: a demo `Holdings` (use `config/portfolio.example.toml`), an invented ETF list `etf_core` (`kind = "etf"`, tickers `DEMETF.DE` and `DEMETG.DE`, one with `group = "technology"`, one with 300 bars so it lacks the full risk window), one demo holding that is also on a watchlist, one holding ticker with no prices, and a short invented history (about 20 weekly points) built in code (not read from a file).

- [ ] **Step 1: Write failing tests** in `tests/test_build.py`: update the existing asserts to six files and version 3; `test_holdings_json_matches_its_schema_and_demo_story` (positions include a priced stock, the ETF, the fund and the unpriced holding with `value_eur is None`; `totals.unpriced == 1`; `history.summary` keys present); `test_holdings_and_etfs_are_not_in_candidates_screener_or_lists` (no demo holding-only or ETF ticker in `leaderboard.json`, `research.json` or `meta.json` lists); `test_extras_are_in_the_covariance_matrix` (the full-window ETF is in `portfolio.risk_tickers`, the 300-bar ETF is in `no_risk_data` with a reason); `test_ticker_on_watchlist_and_in_holdings_appears_once_in_portfolio_tickers`; `test_missing_history_file_does_not_fail_the_build` (call `compute` with a history error; `history is None`, `history_note` non-empty); `test_no_holdings_file_writes_an_empty_holdings_json`.
- [ ] **Step 2:** Run `uv run pytest tests/test_build.py -q`. Expected: FAIL.
- [ ] **Step 3:** Implement `holdings.schema.json`, bump the other schemas' `schema_version` const to 3, wire `build.py` and `demo.py` as above. Bump `SCHEMA_VERSION` in `web/src/data/load.ts` and add `holdings` to `Data`, `loadAll` and the generated-type exports (`Holdings`, `Position`).
- [ ] **Step 4:** Run `uv run python -m engine build --demo --out web/src/fixtures` and `uv run python -m engine.holdings` (writes `basket_reference.json` there); `cd web && npm run gen:types`; then `uv run pytest -q`. Expected: all pass. Check with `git diff --stat` that fixture changes are only the new file, the version number and the extra tickers.
- [ ] **Step 5: Commit** (schemas, engine, tests, fixtures, generated types).

---

### Task 6: Basket maths and storage (browser)

**Files:** Create `web/src/lib/basket.ts`, `web/src/lib/basket-storage.ts`, `web/src/lib/basket.test.ts`.

**Interfaces:**
- Consumes: `Holdings`, `Portfolio` types from `web/src/data/load.ts`; `normalise`, `portfolioVol`, `riskContribution` from `web/src/lib/mix.ts`.
- Produces:
  - `export interface BasketItem { ticker: string; amountEur: number }`.
  - `export interface Evaluation { total: number; weights: Record<string, number>; top3: number; tech: number; vol: number | null; volCovered: number; topRisk: { key: string; share: number } | null; ignored: { ticker: string; reason: string }[] }`.
  - `export function evaluate(h: Holdings, basket: BasketItem[], portfolio: Portfolio, techTickers: ReadonlySet<string>): Evaluation`. Existing positions keep their EUR value (locked); basket amounts are added as new positions (a basket ticker that is already a holding adds to that holding). `weights` are over total value. `vol` is computed over the part with risk data with weights renormalised, `volCovered` is that part's share of total value, and `vol` is `null` when nothing has risk data. `ignored` lists basket items with amount not a finite number above 0, or a ticker not in `portfolio.tickers`.
  - `export function corrToPortfolio(ticker: string, h: Holdings, portfolio: Portfolio): { value: number | null; reason: string | null }`: correlation of the ticker's weekly EUR returns with the current risky holdings (value-weighted), computed as `(Σw)_t / (σ_t · σ_p)` from `portfolio.cov`; `null` with a reason when the ticker or the holdings lack risk data.
  - `basket-storage.ts`: `loadBasket(storage?): BasketItem[]`, `saveBasket(items, storage?)`, key `market-leaderboard.basket.v1`, every field validated (same defensive style as `web/src/lib/storage.ts`); corrupt or blocked storage returns `[]`.

- [ ] **Step 1: Write failing tests** in `basket.test.ts`: `matches the Python reference` (reads `../fixtures/basket_reference.json`; for each reference basket `evaluate(...)` matches `vol`, `top3`, `tech`, `weights` within 1e-9); `empty basket equals before`; `basket amount for a holding adds to it`; `ignores zero, negative and NaN amounts and unknown tickers with reasons`; `no risk data gives null vol, never NaN` (all positions without risk); `volCovered is the risky share of value`; `corrToPortfolio is 1 for a single-holding portfolio of the same ticker` and `returns a reason for a ticker without risk data`; storage tests: round trip, corrupt JSON gives `[]`, negative amount rejected.
- [ ] **Step 2:** Run `cd web && npx vitest run src/lib/basket.test.ts`. Expected: FAIL.
- [ ] **Step 3:** Implement the modules.
- [ ] **Step 4:** Run `npm test`, `npm run lint`, `npx tsc -b`. Expected: PASS.
- [ ] **Step 5: Commit.**

---

### Task 7: Portfolio view

**Files:** Create `web/src/components/portfolio.tsx`, `web/src/components/additions.tsx`, `web/src/views/Portfolio.tsx`, `web/src/styles/portfolio.css`, `web/e2e/portfolio.spec.ts`; modify `web/src/router.ts`, `web/src/App.tsx`, `web/src/foundation.test.ts` (route tests), `web/src/main.tsx` (import the css).

**Interfaces:**
- Router: `View` gains `'portfolio'`. `parseHash('')` returns `portfolio`; Candidates moves to `#/candidates`; `formatHash` maps `portfolio` to `#/` and `candidates` to `#/candidates`. NAV order: Portfolio, Candidates, Screener, Watchlists, Mix, Movers. Update the router comment line and `App.tsx` links ("Go to Candidates" becomes "Go to Portfolio").
- Components (props typed from the generated types; layout as in the spec's "Screens" and the local mockup `portfolio-page.html`): `KeyStrip`, `HoldingsTable` (row click: shares link to `withCompany(...)` panel; others open a small ETF/fund panel `EtfPanel` in the same file showing name, kind, group, currency, 1y return, from-high, volatility), `HistoryChart` (inline SVG, weekly points, zero line, lowest and highest marked and labelled, states "weekly points"), `GroupBar` (share by `group` or kind), `GapCards` (one card per Yahoo sector in `leaderboard.json` plus one ETF card: companies, median forward P/E excluding values above 300 or below 0, share of the portfolio; a sector with 0 % is marked; a card selects the candidate list), `CandidateTable` (shares first, ETFs after; columns company, country and list, 1y, from 52-week high, P/E, forward P/E, volatility, correlation to the portfolio from `corrToPortfolio` with its reason as a tooltip text; ETF rows show "n/a" for P/E; a row has an add button that adds a default 500 EUR to the basket), `BasketPanel` (per-item amount input, remove, clear, "split equally" for the selected card; before/after table with the metrics of `Evaluation`, "covers X % of value" beside volatility; the fixed note that the numbers are estimates and the example is not a recommendation), `StatusBar` with the command field (Enter on a known ticker opens its panel; on a view name navigates; otherwise a short message).
- `Portfolio.tsx` shows a plain state ("No portfolio file found: copy `config/portfolio.example.toml` to `config/portfolio.toml`") when `positions` is empty. History-dependent items are hidden when `history` is null, with `history_note` shown.
- Locked holdings label: "Current holdings are locked in this view" (no banned words).

- [ ] **Step 1: Write failing tests.** Vitest in `foundation.test.ts`: `portfolio is the landing route` and `candidates has its own path`. Playwright `web/e2e/portfolio.spec.ts` against the demo fixtures at 1280 and 390 px, light and dark (same loops as `views.spec.ts`): the page opens without console errors or sideways scroll; the holdings table lists every demo position; the unpriced holding row shows "no price" and no `NaN` text anywhere (`page.locator('body')` not matching `/NaN|undefined/`); the history chart is present; clicking a sector card changes the candidate table; adding a candidate changes the "after" column and `localStorage` holds the basket; reloading keeps the basket; clearing returns "after" to equal "before"; a candidate without full history shows "—" for correlation; Esc closes the panel; the page text passes the banned-phrase list (reuse the regex source by reading `scripts/check_wording.py` is not needed: assert the visible text does not match `/\b(sell|bargain|undervalued|top picks?)\b/i`).
- [ ] **Step 2:** Run `cd web && npx vitest run` and `npm run e2e -- e2e/portfolio.spec.ts --trace off`. Expected: FAIL.
- [ ] **Step 3:** Implement router, components, view and CSS. Warm paper tokens only; dense rows about 32 px, mono tabular figures for numbers, ▲ ▼ with signs. On a phone sections stack and the holdings table uses the existing expanding-row pattern (see `web/src/views/Leaderboard.tsx`).
- [ ] **Step 4:** Run `npm test`, `npm run lint`, `npx tsc -b`, the full `npm run e2e -- --trace off`, and `uv run python scripts/check_wording.py`. Expected: PASS. Take screenshots at 1280 and 390 px, light and dark, of the Portfolio view (to `web/e2e/shots/`, which is where the existing ones go) and look at them: no clipped text, no overlap, contrast readable.
- [ ] **Step 5: Commit.**

---

### Task 8: ETF lists, documentation, live check

**Files:** Modify `config/watchlists.toml`, `config/watchlists_verified.csv` (generated), `docs/decisions.md`, `START_HERE.md`, `README.md`.

- [ ] **Step 1:** Propose the ETF entries from the owner's rule (spec, "ETF list rule"): list `etf_core` (name "Core ETFs", `kind = "etf"`) with Nasdaq-100 and S&P 500 trackers, euro-listed UCITS, and `etf_winners` (name "Recent winners, chosen by past return", `kind = "etf"`) with a few ETFs of the highest 1 and 3 year return among well-known UCITS ETFs. Find each Yahoo ticker with a live search; never guess a ticker. Add a `group = "technology"` tag to entries that are technology-heavy by name or index.
- [ ] **Step 2:** Run `uv run python scripts/verify_watchlists.py` (needs network). Expected: every new ETF row `ok`; fix or remove any that is not. Write the proposed list and each ticker's Yahoo name into the commit message body for the owner to read; Nordnet availability is the owner's check.
- [ ] **Step 3:** Add a dated section to `docs/decisions.md` for the design calls made here: ETF lists are marked at list level (`kind = "etf"`) with an optional per-entry `group` (the spec's "a ticker with `kind`" is satisfied through its list); `holdings.json` as a sixth file; schema version 3. Add one `START_HERE.md` status line and a short "Your portfolio" section in `README.md` (copy the example file, where the history CSV goes, that the file is private and ignored by git).
- [ ] **Step 4:** With the owner's real `config/portfolio.toml` present, run `uv run python -m engine build` then open the page (`scripts/open_dashboard.bat`). Expected: build prints counts and exits 0; the owner reads the holdings table against his Nordnet report and the ETF candidate list by eye. Do not commit `web/public/data/`; run `uv run pytest tests/test_privacy.py -q` and `git status` to confirm nothing private is staged.
- [ ] **Step 5: Commit** (config, docs; the generated verified CSV).
