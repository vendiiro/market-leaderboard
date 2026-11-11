# Start here

This repo starts empty on purpose: it holds the approved design (`docs/spec.md`) and the step-by-step plan
(`docs/plan.md`) for a market leaderboard dashboard. The code is built in four sessions, using
https://github.com/vendiiro/dip-dashboard as the reference for the data code.

## What you need

- Python 3.11+ with `uv`, Node.js LTS (npm), Git, and the GitHub CLI (`gh`) signed in.
- Network access to Yahoo Finance (`query1.finance.yahoo.com`, `query2.finance.yahoo.com`, `fc.yahoo.com`),
  Wikipedia (`en.wikipedia.org`, `fi.wikipedia.org`), GitHub and the npm and PyPI registries. In a Claude Code cloud
  environment with limited network, add the Yahoo and Wikipedia hosts to the environment's allowed hosts.
- Chrome (or Chromium) for screenshots and for viewing the page.

## Session 1: paste this as the first message in a fresh Claude Code session

```
Clone https://github.com/vendiiro/market-leaderboard and work in it.
Read CLAUDE.md, START_HERE.md, docs/spec.md and docs/plan.md first.
Then execute Session 1 of docs/plan.md (Tasks 0-3) with superpowers:subagent-driven-development:
clone the reference repo read-only as described in Task 0, set up the scaffold and CI, copy the engine code,
add EUR conversion and the UK pence rule, and build and verify the watchlists. Stop after Task 3 with a
summary of what changed, what was verified and what was not.
```

## Sessions 2, 3 and 4

Same prompt, with "Session 2 (Tasks 4-7)", "Session 3 (Tasks 8-10)" or "Session 4 (Tasks 11-14)". Each session
ends with the tests passing and a short status note added to the bottom of this file. Sessions 2-4 work without
Yahoo access (`python -m engine build --demo`); only the live checks in Tasks 2, 3 and 7 need it.

## Status

- 2026-11-11: repo created with spec and plan; no code yet.
- 2026-11-11: spec and plan revised after a review against dip-dashboard `f14d55c` (spec revision 2: weekly EUR
  covariance, UK listings included, overview page, risk contribution, four sessions); still no code.
- 2026-11-11: session 1 done (Tasks 0-3) on branch `session-1`: scaffold + CI, engine copied from dip-dashboard
  `f14d55c` (347 tests pass), EUR conversion and the UK pence rule (`docs/decisions.md`), five watchlists with
  58 tickers, all `ok` in `config/watchlists_verified.csv` (live Yahoo check 2026-11-11). Finnish list: 23 names
  built by rule; three Wikipedia names had no ticker match (Dovre Group, Lehto Group, Ålandsbanken), see
  `config/fi_candidates.csv`. Next: session 2 (Tasks 4-7).
- 2026-11-11: session 2 done (Tasks 4-7) on branch `session-2`: returns, ranks and list summaries, weekly EUR
  covariance and the mix formulas, movers and alerts, `python -m engine build` (live and `--demo`), four JSON
  schemas, demo fixtures in `web/src/fixtures/`. 386 tests pass. One live build: 58 of 58 tickers, 57 with risk
  data (GRK.HE has 83 of 104 weeks). Run during the European session, so that day's European bars were partial;
  the nightly run after the US close avoids this. Next: session 3 (Tasks 8-10).
