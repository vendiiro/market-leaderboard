# Portfolio page: design

Date: 2026-11-15. Status: approved by the owner on 2026-11-15. Builds on
`docs/superpowers/specs/2026-11-12-research-workstation-design.md` and `docs/spec.md`; both stay valid for
everything this document does not change. **This document reverses one non-goal of the workstation spec: "no
portfolio of real holdings".** Educational research tool: it shows screen results and exposure views, never
investment advice.

## Intent and why

The owner holds shares for one to two years or more and does not plan to sell any current holding in that time.
The only lever he has is where new money goes. Today the dashboard shows companies but knows nothing about what he
already owns, so he cannot see how a candidate would change his own portfolio.

He wants one page that shows his portfolio the way a professional terminal does (dense, numbers first, one click
to detail), and next to it a place to research additions: companies and ETFs from the dashboard's lists, including
sectors his portfolio does not hold today, with the effect of each addition on concentration, correlation and
volatility. He knows his portfolio is concentrated in US technology; he does not want technology excluded from
the candidates, because he understands what such an addition does and wants to see it quantified.

## What the owner decided (2026-11-15)

- One page combines the dense portfolio view (holdings table, history chart, key figures) with the "what if" view
  (basket of additions, before and after). Both were shown as mockups and accepted; the other two mockup tabs
  (per-holding cards, look-through exposure) were not chosen.
- Current holdings are locked in the what-if: no selling. Only new money is modelled.
- Candidates are not limited to sectors the portfolio lacks. Technology names may appear. Sectors the portfolio
  does not hold are highlighted, not enforced.
- Candidates are shares **and ETFs**, with the emphasis on shares. First ETFs: ordinary, popular ones such as
  Nasdaq-100 and S&P 500 trackers (ones sold through Nordnet), and optionally a few ETFs that returned the most
  over recent years. Which exact ETFs is the builder's to propose from this rule (see "ETF list rule").
- The basket shows the effect on weights and concentration **and** on correlation and volatility.
- The look is "closer to Bloomberg or an official terminal": dense, mono figures, a command bar, a key strip.

## Goals

1. **Portfolio view:** value, unrealised result, weights, type or sector, return since purchase, and a history
   chart, from a private local file (see "Data and privacy").
2. **Sector gap cards:** per sector of the dashboard's universe: number of companies, median forward P/E, share of
   the portfolio today. A card filters the candidate table. A sector with 0 % in the portfolio is marked.
3. **Candidate table** for the chosen sector: the existing screener columns plus correlation to the portfolio and
   one-year volatility, with ETFs as candidates beside shares (valuation columns read "n/a" for an ETF).
4. **Research basket:** the owner adds candidates and amounts (a new deposit split over them), sees the portfolio
   before and after: total value, weights of the largest holdings, share of the three largest, share in the
   technology-heavy group, portfolio volatility, largest risk contribution, and each added item's correlation to
   the current portfolio.
5. **ETFs as universe members:** an ETF belongs to a list marked `kind = "etf"` in `config/watchlists.toml` (an
   entry may carry a `group` tag); the engine treats its prices like any other ticker's.
6. Adding companies, ETFs and lists stays a data change, not a code change.

## Non-goals

- No buy or sell wording, no price goals, no verdict that an addition is good, no "diversification score".
- No selling in the what-if, no tax lots, no realised result, no several accounts.
- No Nordnet login or API and no parsing of the Nordnet PDF: the owner edits a file (see below).
- No look-through of ETF contents (company X is 3 % of the ETF and 15 % direct) in this round. It needs ETF
  holdings data that free Yahoo data may not give. Revisit after the first version.
- No projection of future prices (the owner removed the range of outcomes on 2026-11-12; that still holds).

## Anti-goals

- **Holdings in a public repository.** `vendiiro/market-leaderboard` is public. Any commit, doc, test, screenshot
  or fixture that contains the real holdings or values is a failure even if the page works.
- A before and after table that reads as a recommendation. The wording check applies to all new text.
- Correlation or volatility shown for an ETF with too little history as if it were reliable. The mix maths needs
  104 weekly returns; a ticker without them is excluded with a stated reason, as for shares today.

## Data and privacy

- **Holdings file:** `config/portfolio.toml`, listed in `.gitignore`. One block per holding: Yahoo ticker,
  name, kind (`stock`, `etf`, `etn`, `fund`), quantity, cost price per unit in the quote currency. A committed
  `config/portfolio.example.toml` holds invented demo values. Optional keys per holding: `cost_eur_total` (see
  "The numbers"), `group` (free text tag), and, for a fund without a Yahoo ticker, `value_eur` (see "Designer's calls").
- **History file (optional):** the Nordnet "daily development" CSV export, kept outside the repo or in a
  gitignored path. Its format, checked on the owner's file on 2026-11-15: UTF-16 with a byte order mark,
  tab-separated, decimal comma, percent signs in the percent columns, one row per week from the first deposit.
  Columns: date, total value, daily development (%), accumulated return (%), daily development (EUR), accumulated
  return (EUR), net deposits (EUR). The accumulated return in percent is time-weighted; the one in EUR is
  money-weighted, so they can disagree in sign. The chart and the largest fall come from the percent column. The
  page says these are weekly points.
- **Generated data:** the portfolio part of the nightly output goes under `web/public/data/` (already gitignored).
  Demo mode (`python -m engine build --demo`) uses `config/portfolio.example.toml` so the page and tests work with
  no private data.
- A test asserts that `config/portfolio.toml` is ignored by git and that no tracked file contains it.
- The local mockups used while designing hold real numbers. They live under `.superpowers/` (ignored). They are a
  visual reference for the layout only; do not copy their numbers into tracked files.

## Screens

Navigation: **Portfolio**, Candidates, Screener, Watchlists, Mix, Movers. Portfolio is the landing page
(designer's call).

Portfolio view, top to bottom (visual reference: the local mockup `portfolio-page.html` in the
`.superpowers/brainstorm/` session folder):

1. Status bar: account label, data dates, a command field that jumps to a ticker or view.
2. Key strip: value, unrealised result, return since the first deposit, one-month return, year-to-date, portfolio
   volatility, largest fall in the history.
3. Left: holdings table (name, type or sector, value, result, return since purchase, weight bar). Right: history
   chart with the lowest and highest points marked, and a bar of where the portfolio sits by sector or type.
4. Section "Researchable additions": sector gap cards.
5. Left: candidate table for the chosen card. Right: the research basket and the before and after table.
6. Key strip at the bottom (view shortcuts) and a source line (portfolio file date, Yahoo data date).

A row click opens the existing research panel (shares) or a smaller ETF panel (name, type, expense ratio and
sector split if Yahoo gives them, 1y return and volatility). Phone: sections stack; the table follows the
existing expanding-row pattern.

**Theme.** Warm paper only (owner's choice, 2026-11-15). The mockup's dark amber terminal variant is dropped; the
terminal feel comes from density, mono figures, the command field and the key strip. The existing dark mode for
devices set to dark stays as it is.

## The numbers

- **Value and result:** quantity times latest close, converted to EUR with the existing FX code (pence rule
  included); result = value minus the EUR cost. The EUR cost is `cost_eur_total` when the file gives it (the owner can
  take it from his Nordnet report as value minus result); otherwise it is quantity times cost price converted at
  today's rate, and the result is marked "approximate". Shown with a note that Nordnet's own figures include
  exchange-rate effects and may differ slightly. (Designer's call.)
- **Return since purchase:** price against cost price in the quote currency.
- **Portfolio volatility, correlations, risk contribution:** the existing Mix maths (weekly returns in EUR over 104
  weeks, `engine/portfolio.py`), with the current holdings as fixed weights and the basket as additions. The page
  computes before and after from a covariance matrix the engine writes for the holdings plus all candidates, as
  the Mix view does today. These are estimates from two years of data, not forecasts, and the page says so.
- **"Technology-heavy" share:** the share of the portfolio in holdings whose `group` tag is `technology` (free text in
  the file, this one value is the one the metric reads), plus, for candidates, shares whose Yahoo sector is
  Technology or Communication Services and ETFs whose entry in `watchlists.toml` carries `group = "technology"`.
  Owner-set tags are more honest than guessing an ETF's content from its name. Candidates and holdings that are not
  tagged count as not technology-heavy. (Designer's call.)
- **Sector gap cards:** sectors come from Yahoo for shares; an ETF is counted under its tag. The median forward P/E
  uses the consistency checks of the workstation spec; an inconsistent figure is marked and left out.

## Designer's calls (from the builder check; the owner can overrule any)

- **Funds without a Yahoo ticker** (Nordnet funds) take `value_eur` in the holdings file, edited by hand at each
  update. They count in total value, weights, the three-largest share and the technology-heavy share. They are
  left out of correlation, volatility and risk contribution; the volatility figure is computed over the part of
  the portfolio that has price history, weights renormalised, and labelled "covers X % of value".
- **History file path:** a `history_csv` key in `config/portfolio.toml`. Without it, or in demo mode without a
  demo history, the chart and the key-strip items that need it (return since first deposit, one month, year to
  date, largest fall) are hidden, not rebuilt from current prices. Demo mode ships a short invented history.
- **Key strip from weekly points:** "since the first deposit" chains the time-weighted percent column (the last
  value). One month and year to date use the nearest earlier weekly point to the boundary and say "weekly points".
- **Candidate universe for the covariance matrix:** every ticker on every dashboard list plus ETFs, as Mix does
  today; holdings are fetched and verified as extra tickers. A holding whose ticker fails verification is shown
  without risk data and reported on the data-state page; it does not stop the build.
- **Basket state:** saved in the browser (`localStorage`) as its own object, separate from saved Mix mixes. Each
  item has its own EUR amount; the deposit is the sum.
- **Local only:** the dashboard runs on the owner's machine (README). Generated portfolio data stays in
  gitignored `web/public/data/`. Hosting or sharing the built page is out of scope; if it is ever wanted, holdings
  must be stripped first.
- **ETF candidates:** shipping with an empty or short ETF list is valid; entries are added as the owner names them.

## ETF list rule (owner's rule, 2026-11-15; mechanics are the designer's)

- Two groups, kept apart in `config/watchlists.toml` so the page can show which is which: **core** (broad, popular
  index ETFs such as Nasdaq-100 and S&P 500 trackers, euro-listed UCITS) and **recent winners** (a few ETFs with
  the highest trailing return over the last years).
- The "recent winners" group is chosen by past return, so it is backward-looking by construction. Its rows carry a
  fixed label saying so, and it is never used to rank or to suggest. This is the same survivorship caveat as for
  the share universe.
- Shares stay the focus: the candidate table lists shares first and ETFs after them, and the sector cards count
  shares and ETFs separately.
- Every ETF ticker passes Yahoo verification before use. Whether Nordnet sells an ETF cannot be checked from free
  data; the owner checks that when he reads the list. Neither group is complete or ranked by cost; the page does
  not claim they are.

## Constraints

- Free Yahoo data: daily bars, current ratios, no point-in-time fundamentals (see the workstation spec).
- Some candidates have inconsistent ratios (in the 2026-11-13 run, a forward P/E above 1,700 and one near 4). They
  are marked and ignored in sorting and medians, never shown as bargains.
- UCITS ETFs bought through Nordnet are mostly listed in euros on European exchanges; their Yahoo tickers must be
  found and verified like any watchlist entry. A ticker that fails verification is reported, never guessed.
- Currencies: holdings and candidates trade in EUR, USD, GBp, NOK, SEK, DKK; mix risk is in EUR.

## Verification

- Engine: unit tests on synthetic data for the holdings maths, the EUR conversion for a USD and a GBp holding, the
  before and after formulas against a Python fixture (as for Mix), ETF tickers with too little history, funds with a
  manual value, and the Nordnet CSV reader (UTF-16, decimal comma).
- Privacy test (see above). The demo portfolio is invented.
- Schema: bump the schema version, update `schemas/`, regenerate types; the page refuses older data with the
  existing message.
- Web: browser tests and screenshots at 1280 and 390 px, light and dark, for the Portfolio view with the demo
  portfolio; contrast test on any new colours.
- One live build with the owner's private file; the owner reads the holdings table against his Nordnet report.
- The wording check runs on every new sentence.

## Left to the builder

Component structure; how the engine and page share the Mix code; the ETF panel's exact content; the file layout
of the generated portfolio JSON; chart implementation (inline SVG, no chart library, as today); the command field's
exact behaviour; thresholds for "too little history".

## Open questions for the owner

None. The owner's answers are recorded under "What the owner decided" and "ETF list rule"; the designer's calls
are listed under "Designer's calls".
