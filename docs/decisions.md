# Decisions and checked facts

Newest first. Each entry says what was checked, the numbers, and what follows for the code.

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
