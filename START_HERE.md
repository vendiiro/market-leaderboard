# Start here

This repo starts empty on purpose: it holds the approved design (`docs/spec.md`) and the step-by-step plan
(`docs/plan.md`) for a market leaderboard dashboard. The code is built in three sessions, using
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
clone the reference repo read-only as described in Task 0, copy the engine code, build and verify the
watchlists, and build the leaderboard engine. Stop after Task 3 with a summary of what changed, what was
verified and what was not.
```

## Sessions 2 and 3

Same prompt, with "Session 2 (Tasks 4-7)" or "Session 3 (Tasks 8-11)". Each session ends with the tests passing
and a short status note added to the bottom of this file.

## Status

- 2026-11-11: repo created with spec and plan; no code yet.
