# Decisions and checked facts

Newest first. Each entry says what was checked, the numbers, and what follows for the code.

## 2026-11-16: Portfolio page (design `docs/superpowers/specs/2026-11-15-portfolio-page-design.md`)

Calls made while building it, each open to the owner's change:

- **ETF lists are marked at list level** (`kind = "etf"` on a `[list]` in `config/watchlists.toml`), with an optional
  per-entry `group` tag (`TICKER = { name = "...", group = "technology" }`). The spec said "a ticker with
  `kind`"; every ticker belongs to a list, so the effect is the same. ETF lists never reach Candidates, Screener or
  Watchlists.
- **`holdings.json` is a sixth output file; schema version 3** for every file. Holdings and ETF candidates join the
  covariance matrix of `portfolio.json` (weekly EUR returns, 104 weeks) when they have the full window; the others get a
  stated reason.
- **ETF lists checked 2026-11-16 against Yahoo** (all `ok` in `config/watchlists_verified.csv`): `etf_core` holds
  SXR8.DE (S&P 500), EQQQ.DE (Nasdaq-100), IWDA.AS (MSCI World) and VWCE.DE (FTSE All-World); `etf_winners` holds the three
  highest 3-year returns of a small pool of well-known UCITS ETFs that Yahoo could price in a supported currency:
  VVSM.DE (+195 %), QDVE.DE (+98 %), ISPY.L (+98 %). The pool was not exhaustive and DFNS.L (+122 %) was left out because
  it trades in USD on the London exchange, which the pence rule does not cover. The list is chosen by past return, so it
  is backward-looking and labelled so. Whether Nordnet sells each ETF is not checked here.
- **`etf_regions` (added 2026-11-16, all `ok` against Yahoo):** IMEU.AS (Europe), SXRT.DE (Euro Stoxx 50), IJPA.AS (Japan),
  SXR1.DE (Asia Pacific ex-Japan), IS3N.DE (emerging markets), XCS6.DE (China). The MSCI India and China lines on London and
  Amsterdam (NDIA.L, ICHN.AS) were left out: they trade in USD, which the exchange registry does not allow for those suffixes.
- **Proxy tickers for broker products:** a holding the owner cannot match to an exact Yahoo listing may be tracked with a
  general Yahoo ticker of the same index. Its quantity is then "proxy units" (report value divided by the proxy's close on the
  report date), so the value matches the report on that date and follows the proxy afterwards. The cost stays the broker's.
- **Result of a hand-valued fund** is value minus `cost_eur_total` when that is given; the page flags the summed result as
  incomplete whenever any holding has none (an unpriced holding, or a fund without a cost).
- **Yahoo listings of ETFs bought through a broker can differ** from the listing the broker prices (another exchange or share
  class), so a holding whose Yahoo ticker is not certain can be typed in as a fund with a manual value and `cost_eur_total`;
  it is then left out of the volatility estimate until the exact ticker is known.
- **Holdings are not matched to Yahoo by name** (the names in the holdings file are the broker's, so a name check would raise
  false alarms). A holding with no usable prices is shown as "no price tonight" and listed on the data page.
- **Result and value differ slightly from the broker's report** because Yahoo's latest close can be a day later than the
  report date and the conversion rate is Yahoo's.

## 2026-11-13: Steadiness removed from the shortlist score

Pre-registered backtest (`docs/backtests/2026-11-12-measures-result.md`): the top third by steadiness did 18.8 points worse than the bottom third over 252 bars (90 % interval -27.6 to -11.1), "not supported", and the sign is the opposite of what the measure assumes. The owner chose to drop it from the score. `engine/research.py`: `SCORED = (value, quality, trend)`, a score needs 2 of 3 (was 3 of 4), the "why / what argues against" sentences use only those three. Steadiness is still computed and shown as a bar and a Screener column, labelled with the test result. Effect on the demo data: see `web/src/fixtures/research.json`; the live shortlist changes at the next nightly build.

## 2026-11-11: Size check of the quality score lowered from 20B to 1B USD

The copied quality score has a size check, "market cap at least 20B USD", made for dip-dashboard's universe of
global large caps. On these watchlists it failed every Finnish smaller company by construction (the list is capped
at 5B EUR), so the check said nothing. The owner chose to lower it: `config/settings.toml` now has
`market_cap_min = 1_000_000_000` (USD, one threshold for all lists). Effect: US, defence and energy names are
unchanged (all far above both limits); on the Finnish list the check now separates companies above and below
about 1B USD (Finnair passes). The code default in `engine/config.py` stays at the copied 20B; the settings file
overrides it. Still an untested screen rule.

## 2026-11-11: Yahoo market cap for London listings is in pounds, the price is in pence

Checked live with yfinance 1.8.0 (`Ticker.info`), comparing `marketCap` with `sharesOutstanding` times the price:

| Ticker | Yahoo `currency` | Price | Shares outstanding | `marketCap` | Price x shares | Ratio |
|--------|------------------|-------|--------------------|-------------|----------------|-------|
| BA.L (BAE Systems) | GBp | 1925.0 | 2,923,452,200 | 56,276,455,424 | 5,627,645,485,000 | 0.01 |
| SHEL.L (Shell) | GBp | 3624.5 | 5,661,348,316 | 205,195,558,912 | 20,519,556,971,342 | 0.01 |
| BP.L (BP) | GBp | 552.2 | 15,453,912,643 | 85,336,514,560 | 8,533,650,561,465 | 0.01 |

Conclusion: prices of `.L` lines are in pence (GBp), `marketCap` is in pounds (GBP). Three names on one day; it is
re-checked whenever a UK name is added.

What follows:

- `engine/exchanges.py`: `.L` has trading currency `GBp`; verification accepts `GBp` or `GBX` for a `.L` ticker.
- `engine/fx.py`: `cap_currency("GBp")` is `"GBP"`. A market cap is converted with `cap_currency(currency)`, never
  with the quote currency directly. `usd_value(x, "GBp", ...)` divides by 100 and is right for a price, wrong for
  a market cap.
- Session 2: `quality.quality()` converts `fund["marketCap"]` with `fund["currency"]`. For UK names the build must
  pass `currency = cap_currency(currency)` in the fundamentals it hands to the quality score, otherwise their
  size check sees a value 100 times too small.
- Returns do not depend on the unit, so leaderboard returns need no change.

## 2026-11-11: Minimum history is 250 daily bars in the verification pull

The plan's rule "at least 250 daily bars in 1y" cannot be met reliably: a calendar year has about 250 to 253
sessions depending on the exchange and its holidays. Verification pulls 5 years and requires at least 250 bars in
total (status `few_bars` otherwise), which means "about one year of history or more".
