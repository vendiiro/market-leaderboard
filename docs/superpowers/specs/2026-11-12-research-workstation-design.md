# Research workstation: design

Date: 2026-11-12. Status: draft for the owner's approval. Builds on `docs/spec.md` (revision 2), which stays valid
for everything this document does not change. Educational research tool: it shows screen results and exposure
views, never investment advice.

## Intent and why

The first version ranks and describes. The owner holds shares for a year or more and finds candidates in two
ways: he hears news about a company, or he notices that a company he considers good has fallen. He wants the page
to do the first read for him: point at companies worth a closer look, say why, say what speaks against it, and
show the usual valuation numbers with a plain guide to reading each one. He also wants the page to look and work
like a professional research screen: more on screen at once, one click from a table row to the reasoning.

The page still never concludes for him. Every pointer reads as "worth a closer look, and here is what could go
wrong". He stated this himself: the output is something to research further, with the risk acknowledged.

## What the owner decided (2026-11-12)

- **Most important question per company:** is it cheap or expensive.
- **Horizon and style:** long only, holding a year or more. No short-term trading signals.
- **Screens:** the dense table with a research panel ("workstation") and the research cards ("feed") both go in.
  The arrangement in "Screens" below was shown as a mockup and accepted.
- **Map:** used for combined assets in the Mix view (tile size = weight), not as a market overview.
- **Research panel:** content and layout as in the mockup (four measures, why look closer, what argues against,
  what this cannot tell you, cheap-or-expensive strips, the usual numbers each with a guide, range of outcomes,
  headlines). Each term is explained on the page.
- **Background:** warm paper. Softer and less clinical than the current cool grey; not a dark terminal look.
- **Map colours:** not five shades of one colour.
- **Universe:** refreshed over time, kept to good companies. Open to widening from Finland to the Nordics or
  Europe. A company must be a profitable business; how its share has moved over past years matters.
  Steadiness of the share price is not a requirement for entry (several current names would fail it).
- **Candidate rule:** left to the designer, as a quant would do it. The worked Nvidia example (four measures,
  place 14 of 40, reasons for and against, caveats) was accepted as the kind of analysis wanted.
- **Problems found in the test run must be fixed:** the currency error in the value measure and the blunt gate.
- **Range of outcomes:** a simulated one-year range per stock is wanted. The owner was told it cannot be checked
  against history at a one-year horizon and accepted it as shown: an illustration with a growth assumption he sets.

## Goals

1. **Candidates** (landing page): tonight's shortlist as cards. Each card: valuation strip, the case for and
   against in plain words, key figures, and badges for today's events.
2. **Screener:** every company once, in a dense sortable table with valuation columns and filters.
3. **Research panel:** opens from any screen for the selected company; on a phone it is a full page.
4. **Mix with a map:** weights by slider, a map of the mix, combined volatility and the existing exposure and
   correlation views.
5. **Valuation data:** P/E, forward P/E, EV/EBITDA, P/B, margins, return on equity, debt, growth; P/E against the
   company's own past year-ends and against its sector.
6. **Adding companies and markets is a data change, not a code change.**
7. **Warm paper theme** in the light mode.

## Non-goals

- No price goals, no "buy" or "sell", no statement that now is a good entry point.
- No intraday data, no paid data source.
- No market-wide map; no per-stock full-page charting tool; no portfolio of real holdings.
- No new rule-built lists for other exchanges in this round (see "Universe").

## Anti-goals

- A score that looks precise and tested when it is not. The four measures are shown separately with their
  evidence status; the average is used to pick the shortlist and is never shown as a rating out of 100.
- "Cheap" produced by a data error. A valuation figure that fails a consistency check is marked and left out of
  the ranking, not shown as a bargain.
- Text that reads as advice. Card sentences are generated from fixed templates that pass the wording check.
- A range of outcomes that reads as a forecast.

## Constraints (from the data, checked 2026-11-12 on 8 and then 58 tickers)

- Yahoo returns current ratios (forward P/E, P/B, P/S, EV/EBITDA) for nearly every ticker and trailing P/E where
  there is a trailing profit.
- Annual statements cover 4 to 5 years. Quarterly statements are missing for some (BAE Systems had none).
- Fundamentals are today's values. There is no record of what was known at a past date, so measures built on
  fundamentals cannot be backtested with this data.
- Some companies report in a different currency than they trade in (Shell, Equinor, Aker BP, Vår Energi report in
  USD). Yahoo gives this as `financialCurrency`.
- Some figures are inconsistent (Equinor: P/E 8.7 with EV/EBITDA 19.6; Finnair: trailing P/E 8.8, forward 22.3).
- Headlines: 6 to 10 per ticker; current for large companies, months old for some small Finnish ones, and
  sometimes only loosely about the company.
- dip-dashboard tested a 21-day range of outcomes: it passed overall and was not shown to be calibrated after
  sharp falls, so it did not ship. Its notes say direction cannot be forecast from this data.

## Screens

Navigation, left to right: **Candidates, Screener, Watchlists, Mix, Movers.**

- **Candidates** replaces Overview as the landing page. Filter chips: list, sector, country. Empty state when
  nothing passes.
- **Screener:** columns: company, 1y return, from 52-week high, P/E, forward P/E, P/E vs own past, forward P/E vs
  sector, profitable years (for example 4/4), a valuation word (low for it / typical / high for it / no data),
  and the four measure ranks. A strip of counts above the table (companies, low for their own past, fell more than
  20 % from high, both, data date).
- **Watchlists:** the current leaderboards, unchanged in behaviour, with P/E and forward P/E columns added. The
  list summary cards from today's Overview move to the top of this view. (Designer's call.) The existing
  "checks" column and dip flag stay here and on Movers as they are. The Screener, the cards and the panel use the
  four measures instead; the panel's guide explains that "checks" is the older pass/fail count and "business
  quality" is the newer rank. (Designer's call.)
- **Mix:** current view plus weight sliders and the map. Map: tile area = weight, colour = share of risk minus
  weight on a two-sided scale (cool = less risk than its weight, neutral grey = equal, warm = more). Every tile
  prints weight and share of risk.
- **Movers:** unchanged, plus recent headlines for the listed companies.
- **Data state:** today's Overview panel ("tonight's data", failures, limits) becomes a page reached from the
  data-status chip in the top bar. (Designer's call.)
- **Research panel:** right-hand panel on desktop (the table stays visible), full page on a phone, closable with
  Esc, reachable by keyboard from any row or card. Its address is part of the URL so a company can be bookmarked.

### Research panel content

1. Header: name, ticker, sector, country, currency; shortlist place if any; distance from 52-week high; 1y
   volatility.
2. Four measures as bars (rank 0 to 100, 100 = best) with a line stating which are tested and which are not.
3. **Why look closer:** up to three sentences, from the strongest measures and their underlying facts.
4. **What argues against:** up to three sentences, from the weakest measures.
5. **What this cannot tell you:** caveats raised by rules (see "Caveats").
6. **Cheap or expensive:** two strips. P/E now against its own fiscal year-end P/Es (each year a mark); forward
   P/E now against the companies of its sector in the universe (each company a mark, sector middle labelled).
7. **The usual numbers,** each with a one-line guide in plain words: P/E, forward P/E, EV/EBITDA, P/B, profit
   margin, return on equity, debt to equity, revenue growth, earnings growth.
8. **Range of outcomes after one year,** labelled as an illustration (see below).
9. **Headlines** where Yahoo has ones from the last 14 days; otherwise the section says there are none.

## The candidate rule (designer's call, accepted in principle by the owner)

All ranks are percentile ranks within the whole universe (all lists together), 0 to 1, higher = better.

**Gate.** A company can be a candidate only if its latest fiscal year shows a profit and at least 3 of its last 4
fiscal years do. Fewer than 3 years of statements: "not enough history", not a candidate, still in the Screener.
(Softened from "4 of 4" after the test run removed Amazon for its 2022 loss and Kalmar for having 3 years.)

**Four measures.**

- **Value** = mean of the available ranks of:
  (a) trailing P/E divided by the middle of the company's own fiscal year-end P/Es (needs at least 3 years with a
  positive EPS; lower is better);
  (b) forward P/E divided by the middle forward P/E of its sector in the universe (sectors with fewer than 5
  companies use the whole universe; lower is better);
  (c) EV/EBITDA, positive values only (lower is better).
- **Business quality** = mean of the available ranks of return on equity (a value above 100 % is marked distorted
  and left out), profit margin, and debt to equity (lower is better; not used for sectors where the existing
  quality code already says it does not apply).
- **Long-term trend** = return from 12 months ago to 1 month ago (bar T-252 to T-21), adjusted closes, own
  currency.
- **Steadiness** = the number of days in the last 756 bars on which the share moved 5 % or more while its
  region's index moved less than 2 %. Two regions only: S&P 500 (`^GSPC`) for tickers without a suffix, STOXX
  600 (`^STOXX`) for all others; stored as a new `region_index` field in the exchange registry, separate from
  the existing country `index`. Fewer is better. Needs 500 bars. (Designer's call.)

**Shortlist.** Score = mean of the available measures (at least 3 of 4 required). Tonight's candidates are the
highest scores among companies that pass the gate: 15 of them, or one fifth of the gate-passers if that is
fewer (with today's 58 companies, 40 pass the gate, so 8 are shown). Both numbers are settings. A shortlist that
holds a third of the universe would not be a shortlist; it grows to 15 as the universe grows. (Designer's call.)

**Own-past P/E, done correctly.** Year-end P/E = share price in the trading currency on the last trading day of
the fiscal year, divided by that year's diluted EPS converted from the reporting currency to the trading currency
at that day's rate (pence lines: pounds times 100). The test run skipped the conversion and produced values of
-90 % for the four USD reporters; that error must not be reproducible: a test covers a USD reporter trading in
NOK and in pence.

**Consistency checks.** A figure is marked "looks inconsistent" and excluded from ranks when: trailing or forward
P/E is negative or above 300; own-past ratio is outside -80 % to +400 %; forward P/E is under 40 % or over 250 %
of trailing P/E; EV/EBITDA and P/E disagree by more than a factor of 4 in a sector where both normally track.
(Thresholds are the builder's to tune on the 58 tickers; the principle is fixed.)

**Card sentences.** Built from fixed templates filled with the facts behind the two strongest and two weakest
measures, for example "P/E {pe} against a middle of {own} over its last {n} year-ends". No free text, no
adjectives of judgement. All templates pass the wording check.

**Caveats** ("what this cannot tell you"), each raised by a rule:
- EPS grew more than 5-fold across the statement window: the low P/E comes from profit growth, not a price fall.
- Forward P/E is below 60 % of trailing: it depends on analyst estimates of strong growth.
- Return on equity above 100 %: looks distorted.
- The company reports in another currency than it trades in: converted figures.
- Fewer than 4 years of statements.
- Always: fundamentals are current values, and the value and quality measures are untested.

**Events (badges, never selection):** 1-day move beyond the existing dip threshold, a new dip flag, a headline
from the last 2 days.

**Evidence status.** Value, profitability, 12-month momentum and low volatility are measures with a long
published record on large samples. None is tested on this universe. Before the page ships:
- Trend and steadiness are backtested on the universe's price history with a question and pass criterion written
  down before any result is seen (same discipline as dip-dashboard's backtest), and the result is shown on the
  page whatever it is. A result of "no detectable effect" is a valid outcome and is displayed as such.
  Pre-stated design (designer's call): at each month-end with at least 756 bars of history, rank the companies by
  the measure; compare the mean return over the next 252 bars of the top third with the bottom third; report the
  difference with a 90 % interval from a bootstrap that resamples whole formation months. "Supported" = the
  interval lies above zero. One run per measure, no tuning afterwards. The spec is written to a file and
  committed before the run. `backtest.py` in dip-dashboard (same commit as the other copies) may be reused.
- Value and quality are labelled untested, with the reason (no past fundamentals in free data).
- The universe holds companies chosen today, so any backtest on it flatters the past; the page says so.

## Range of outcomes (illustration)

Per company: a one-year range drawn as a fan with 50 % and 80 % bands and three figures: the chance of ending
more than 30 % lower, lower than today, and more than 30 % higher. Model: lognormal, volatility = the 1-year
daily volatility already computed (sigma), growth assumption g set by the owner (default 0 %, stepper from
-10 % to +20 %). The one-year log return is normal with mean ln(1 + g) - sigma^2 / 2 and standard deviation
sigma, so g is the expected simple return. Label, always visible: "Illustration from past volatility and the growth you set. Not checked against
history; not a forecast." No claim of calibration is made; none is possible at this horizon with about 15
separate years of data.

Worked check (Nvidia, 2026-11-12): volatility 38.6 %, growth 0 % gives 23 % / 58 % / 19 %.

This is the fifth formula the browser is allowed to compute (normal distribution function on engine numbers).
It gets a Python reference and a fixture test like the four mix formulas.

## Data additions

- Fundamentals cache: add `forwardPE`, `trailingPE` (already there), `enterpriseToEbitda`, `priceToBook`,
  `operatingMargins`, `earningsGrowth`, `trailingEps`, `forwardEps`, `financialCurrency`, `sector`, `country`.
  Still one Yahoo info call per ticker, refreshed over the week as today.
- Annual income statement per ticker (net income, diluted EPS, revenue, by fiscal year): a second cache,
  refreshed monthly, since it changes once a year.
- Headlines: fetched nightly only for candidates and movers (about 30 calls). Titles are third-party text: shown
  as text with the source and date, linked with `rel="noopener noreferrer"`, never interpreted, and marked as
  Yahoo's words. They are outside the wording check and say so.
- Region index closes (S&P 500, STOXX 600) for the steadiness measure.
- New output file `research.json` (one object per ticker: measures, facts, sentences, caveats, year-end P/Es,
  sector marks, headlines) with its own schema; `leaderboard.json` rows gain P/E and forward P/E. Schema version
  goes to 2; the page refuses version 1 data with the existing message.
- Demo data gains fundamentals histories covering: a USD reporter trading in NOK, a company failing the gate, one
  with 3 years of statements, one with an inconsistent figure, one with no headlines.

## Universe: adding companies and markets

Today a new list needs a code change (`LIST_KEYS` is fixed in `engine/watchlists.py`) and a new exchange needs a
registry entry. After this change:

- **Add a company:** one line `"TICKER" = "Company name"` under a list in `config/watchlists.toml`, then
  `uv run python scripts/verify_watchlists.py`. Sector, country and currency come from Yahoo. Nothing else.
- **Add a list:** a new `[key]` block with `name = "..."` in the same file. List keys are read from the file;
  the page shows lists in file order. No code change.
- **Add a market:** one line in the exchange registry (`engine/exchanges.py`): suffix, name, time zone, currency,
  region index. Verification already rejects a ticker whose suffix is unknown, with that reason.
- **Removal:** a ticker that fails verification is reported, never silently dropped; the owner removes the line.
- The Finnish list stays rule-built. Other lists are hand-picked and verified. Rule-built lists for other
  exchanges are out of scope for this round: the Finnish builder needed two name sources and still missed three
  companies, so each exchange is its own piece of work.

Which markets and lists to add first is the owner's choice (open question 1).

## Visual system

- **Light theme = warm paper:** background `#f7f4ee`, surface `#fffdf9`, sunken `#efeae0`, line `#e2dccf`
  (the mockup values). Ink, accent, up (blue) and down (red) stay. The contrast test must pass for every pair on
  the new backgrounds; values move if it fails.
- **Dark theme** stays for devices set to dark. Light is what the owner sees and judges. (Designer's call.)
- **Two-sided map scale:** cool, neutral grey, warm; checked with the dataviz palette validator in both themes;
  every tile prints its numbers, so colour is never the only carrier.
- **Density:** table rows about 32 px on desktop, mono figures with tabular numbers, panel width about 380 px.
- Everything from `docs/spec.md` on accessibility, states and phone layout still applies.

## Verification

- Engine: unit tests on synthetic data for every measure, the gate, the currency conversion, the consistency
  checks and the sentence templates; schema tests; wording check on generated sentences.
- The backtest of trend and steadiness, pre-registered, result committed under `docs/`.
- Web: unit tests for the range formula against the Python fixture; browser tests and screenshots (1280 and
  390 px, light and dark) for Candidates, Screener, the panel and the Mix map; contrast test on the warm tokens.
- One live build, with the candidate list read by eye for obvious data errors before it is called done.

## Left to the builder

Component structure; treemap layout method; exact thresholds of the consistency checks; exact colour values
after validation; how the panel animates; cache file layout.

## Open questions for the owner

1. Which markets or lists should be added first once adding is easy (for example a Nordic large-company list, or
   specific companies you already have in mind)?
