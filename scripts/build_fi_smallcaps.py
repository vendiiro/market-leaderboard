#!/usr/bin/env python3
"""Rebuild the Finnish smaller-companies list ([fi_small.tickers] in config/watchlists.toml) by rule. Run monthly.

Needs network and yfinance:   uv run python scripts/build_fi_smallcaps.py

1. Company names come from the Finnish Wikipedia list of companies listed on Nasdaq Helsinki (parsed, never typed).
2. Each name is looked up with Yahoo search; only Helsinki (.HE) equity lines whose Yahoo name matches are candidates.
   Yahoo search misses some names, so tickers that Wikidata lists for Nasdaq Helsinki are added as candidates too.
   Names found by neither are listed in the CSV; the list can therefore miss a company.
3. engine.watchlists.fi_smallcap_rows keeps market cap 0.3-5B EUR, median 60-day traded value >= 0.5M EUR a day,
   at least 250 daily bars of history, and one share class per company. Every candidate and the reason it was kept or dropped goes to
   config/fi_candidates.csv.
4. The [fi_small.tickers] section (the last one in the TOML) is rewritten. Then run scripts/verify_watchlists.py.

Market cap and traded value are today's values (not point-in-time). Wikipedia and Wikidata are read as data only.
"""
from __future__ import annotations

import csv
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.data import fetch_prices  # noqa: E402
from engine.fx import fetch_fx_to_usd  # noqa: E402
from engine.verify import name_score, yahoo_info  # noqa: E402
from engine.watchlists import fi_smallcap_rows  # noqa: E402

PAGE = "Luettelo Helsingin pörssissä noteeratuista yhtiöistä"
API = "https://fi.wikipedia.org/w/api.php?action=parse&prop=wikitext&format=json&formatversion=2&page="
SPARQL = ("SELECT ?itemLabel ?ticker ?end WHERE { ?item p:P414 ?s. ?s ps:P414 wd:Q581755; pq:P249 ?ticker. "
          "OPTIONAL { ?s pq:P582 ?end } SERVICE wikibase:label { bd:serviceParam wikibase:language 'fi,en'. } }")
SECTION = "[fi_small.tickers]"
NL = chr(10)


def company_names(wikitext: str) -> list[str]:
    """First cell of every table row: '[[Target|Shown]]' -> Shown, '[[Target (yritys)]]' -> Target."""
    names = []
    for line in wikitext.splitlines():
        if not line.startswith("|") or line.startswith(("|-", "|}", "|+")):
            continue
        cell = line[1:].split("||")[0].strip()
        m = re.search(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]", cell)
        name = re.sub(r"\s*\([^)]*\)$", "", (m.group(1) if m else cell).strip())
        if name and name not in names:
            names.append(name)
    return names


def wikidata_lines(bindings: list[dict]) -> dict[str, str]:
    """{Yahoo ticker: company label} from Wikidata's 'listed on Nasdaq Helsinki' statements that have not ended."""
    return {b["ticker"]["value"].strip().replace(" ", "-").upper() + ".HE": b["itemLabel"]["value"]
            for b in bindings if "end" not in b and b.get("ticker", {}).get("value", "").strip()}


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "market-leaderboard/0.1 (educational research tool)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def fetch_names() -> list[str]:
    return company_names(_get_json(API + urllib.parse.quote(PAGE))["parse"]["wikitext"])


def fetch_wikidata() -> dict[str, str]:
    try:
        url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(SPARQL)
        return wikidata_lines(_get_json(url)["results"]["bindings"])
    except Exception as e:                       # a second source: the run goes on without it
        print(f"Wikidata query failed: {e}", file=sys.stderr)
        return {}


def queries(name: str) -> list[str]:
    """Search texts to try in order: Yahoo search often misses a bare or accented name but finds 'Name Oyj'."""
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    first = re.split(r"[ -]", name)[0]
    return list(dict.fromkeys([name, f"{name} Oyj", f"{plain} Oyj", plain, first, f"{first} Oyj"]))


def helsinki_lines(name: str, search=None) -> list[str]:
    """Yahoo tickers on Nasdaq Helsinki whose Yahoo name matches the company name (all share classes)."""
    if search is None:
        import yfinance as yf

        def search(q):
            return yf.Search(q, max_results=10).quotes
    for q in queries(name):
        hits = [x["symbol"] for x in search(q)
                if x.get("quoteType") == "EQUITY" and x.get("symbol", "").endswith(".HE")
                and name_score(name, x.get("longname") or x.get("shortname")) >= 0.6]
        if hits:
            return hits
    return []


def rewrite_section(toml_text: str, tickers: dict[str, str]) -> str:
    """Replace everything after the [fi_small.tickers] header line (the last section) with the given entries."""
    head, sep, tail = toml_text.rpartition(NL + SECTION + NL)
    if not sep or (NL + "[") in (NL + tail):
        raise ValueError(f"{SECTION} must exist and be the last section of watchlists.toml")
    lines = [f"{json.dumps(t)} = {json.dumps(n, ensure_ascii=False)}" for t, n in sorted(tickers.items())]
    return head + sep + "".join(line + NL for line in lines)


def main() -> int:
    names = fetch_names()
    print(f"{len(names)} company names from Wikipedia")
    company: dict[str, str] = {}
    not_found = []
    for n in names:
        try:
            found = helsinki_lines(n)
        except Exception as e:
            found = []
            print(f"search failed for {n}: {e}", file=sys.stderr)
        for t in found:
            company.setdefault(t, n)
        if not found:
            not_found.append(n)
        time.sleep(0.3)
    for t, label in fetch_wikidata().items():        # lines the name search missed
        if t not in company:
            company[t] = label
            not_found = [n for n in not_found if name_score(n, label) < 0.6]
    cands = sorted(company)
    print(f"{len(cands)} Helsinki lines; no line found for {len(not_found)} names: {', '.join(not_found)}")
    info = {t: i for t in cands if (i := yahoo_info(t))}
    bars = fetch_prices(cands, period="2y")
    rows = fi_smallcap_rows(cands, info, bars, fetch_fx_to_usd(["EUR"]))
    with (ROOT / "config" / "fi_candidates.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ticker", "source_name", "yahoo_name", "market_cap_eur", "median_traded_eur", "kept", "reason"])
        for r in rows:
            w.writerow([r["ticker"], company[r["ticker"]], r["company"], round(r["cap_eur"]) if r["cap_eur"] else "",
                        round(r["traded_eur"]) if r["traded_eur"] else "", "yes" if r["keep"] else "no", r["reason"]])
        for n in not_found:
            w.writerow(["", n, "", "", "", "no", "no Helsinki line found by Yahoo search or in Wikidata"])
    kept = {r["ticker"]: company[r["ticker"]] for r in rows if r["keep"]}
    if len(info) < 0.9 * len(cands) or not kept:
        print(f"only {len(info)} of {len(cands)} candidates returned data: watchlists.toml left unchanged", file=sys.stderr)
        return 2
    p = ROOT / "config" / "watchlists.toml"
    p.write_text(rewrite_section(p.read_text(encoding="utf-8"), kept), encoding="utf-8", newline=NL)
    print(f"kept {len(kept)} of {len(cands)} candidates -> {SECTION}; details in config/fi_candidates.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
