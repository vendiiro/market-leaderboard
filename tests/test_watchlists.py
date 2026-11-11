import pandas as pd
import pytest

from engine.watchlists import LIST_KEYS, all_tickers, build_fi_smallcaps, fi_smallcap_rows, load_watchlists, membership, read
from synth import flat

GOOD = "\n".join(f'[{k}]\nname = "{k} list"\n[{k}.tickers]\n"AAA{i}.HE" = "Company {i}"\n' for i, k in enumerate(LIST_KEYS))


def write(tmp_path, text):
    p = tmp_path / "watchlists.toml"
    p.write_text(text, encoding="utf-8")
    return p


def test_real_file_loads_the_five_lists():
    lists = load_watchlists()
    assert tuple(lists) == LIST_KEYS and all(lists[k] for k in LIST_KEYS if k != "fi_small")
    assert all(read()[k]["name"] for k in LIST_KEYS)


def test_toml_loads_the_five_keys_in_order(tmp_path):
    lists = load_watchlists(write(tmp_path, GOOD))
    assert tuple(lists) == LIST_KEYS and lists["us_big_tech"] == ["AAA0.HE"]


def test_unknown_or_missing_list_and_bad_entries_are_errors(tmp_path):
    with pytest.raises(ValueError, match="unknown list"):
        load_watchlists(write(tmp_path, GOOD + '[crypto]\nname = "x"\n[crypto.tickers]\n'))
    with pytest.raises(ValueError, match="missing list"):
        load_watchlists(write(tmp_path, GOOD[:GOOD.index("[fi_small]")]))
    with pytest.raises(ValueError, match="name"):
        load_watchlists(write(tmp_path, GOOD.replace('name = "eu_energy list"\n', "")))
    with pytest.raises(ValueError, match="company name"):
        load_watchlists(write(tmp_path, GOOD.replace('"AAA0.HE" = "Company 0"', '"AAA0.HE" = ""')))


def test_a_ticker_in_two_lists_is_one_ticker_with_two_memberships():
    lists = {"eu_energy": ["EQNR.OL", "SHEL.L"], "nordic_energy": ["NESTE.HE", "EQNR.OL"]}
    assert all_tickers(lists) == ["EQNR.OL", "NESTE.HE", "SHEL.L"]
    assert membership(lists) == {"EQNR.OL": ["eu_energy", "nordic_energy"], "SHEL.L": ["eu_energy"], "NESTE.HE": ["nordic_energy"]}


# ---- Finnish smaller companies ---------------------------------------------------------------------------------

def bars(price, volume, n=300):
    return flat(n, price), pd.Series([volume] * n, index=flat(n).index)


def info(name, cap):
    return {"longName": name, "currency": "EUR", "marketCap": cap}


INFO = {
    "MID.HE": info("Mid Oyj", 1.2e9), "TINY.HE": info("Tiny Oyj", 0.2e9), "BIG.HE": info("Big Oyj", 6e9),
    "QUIET.HE": info("Quiet Oyj", 1.0e9), "DUALA.HE": info("Dual Oyj", 2e9), "DUALB.HE": info("Dual Oyj", 2e9),
    "NOCAP.HE": info("Nocap Oyj", None),
}
BARS = {
    "MID.HE": bars(10, 200_000),        # 2.0M EUR a day
    "TINY.HE": bars(10, 200_000), "BIG.HE": bars(10, 200_000),
    "QUIET.HE": bars(10, 10_000),       # 0.1M EUR a day
    "DUALA.HE": bars(10, 60_000),       # 0.6M EUR a day
    "DUALB.HE": bars(10, 300_000),      # 3.0M EUR a day: the more traded class
    "NOCAP.HE": bars(10, 200_000),
}


def test_fi_smallcaps_keep_mid_sized_liquid_names_and_one_class_per_company():
    kept = build_fi_smallcaps(list(INFO) + ["GONE.HE"], INFO, BARS, {"EUR": 1.1})
    assert kept == ["DUALB.HE", "MID.HE"]
    why = {r["ticker"]: r["reason"] for r in fi_smallcap_rows(list(INFO) + ["GONE.HE"], INFO, BARS, {"EUR": 1.1})}
    assert "below" in why["TINY.HE"] and "above" in why["BIG.HE"] and "traded" in why["QUIET.HE"]
    assert "DUALB.HE" in why["DUALA.HE"] and "market cap unavailable" in why["NOCAP.HE"] and "no data" in why["GONE.HE"]
    assert why["MID.HE"] == "" and why["DUALB.HE"] == ""
    new = fi_smallcap_rows(["MID.HE"], INFO, {"MID.HE": bars(10, 200_000, n=249)}, {"EUR": 1.1})[0]
    assert not new["keep"] and "only 249 daily bars" in new["reason"]            # a recent listing


def test_fi_smallcaps_use_the_last_60_bars_for_traded_value():
    close, vol = bars(10, 10_000)
    vol.iloc[-60:] = 200_000                          # quiet long ago, liquid in the last 60 bars
    assert build_fi_smallcaps(["MID.HE"], INFO, {"MID.HE": (close, vol)}, {"EUR": 1.1}) == ["MID.HE"]


# ---- scripts/build_fi_smallcaps.py: the pure parts ---------------------------------------------------------------

def _script():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("build_fi_smallcaps", Path(__file__).resolve().parents[1] / "scripts" / "build_fi_smallcaps.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_company_names_are_parsed_from_the_wiki_table():
    text = "\n".join(["intro [[Suomi|suomalaisia]]", '{| class="wikitable"', "|-", "! Yhtiö !! Toimiala", "|-",
                      "| [[Neste (yritys)|Neste]] || Energia || suuret", "|-", "| [[Kemira]]|| Perus || suuret", "|-",
                      "| [[Outokumpu (yritys)]] || Perus || suuret", "|-", "| Plain Oyj || x || pienet", "|}"])
    assert _script().company_names(text) == ["Neste", "Kemira", "Outokumpu", "Plain Oyj"]


def test_rewrite_replaces_only_the_last_section():
    s = _script()
    text = '[fi_small]\nname = "x"\n[fi_small.tickers]\n"OLD.HE" = "Old"\n'
    assert s.rewrite_section(text, {"B.HE": 'Bé "B"', "A.HE": "A"}) == '[fi_small]\nname = "x"\n[fi_small.tickers]\n"A.HE" = "A"\n"B.HE" = "Bé \\"B\\""\n'
    with pytest.raises(ValueError):
        s.rewrite_section(text + "[later]\n", {})


def test_search_falls_back_to_other_spellings_and_checks_the_name():
    s = _script()
    assert s.queries("Oma Säästöpankki")[:3] == ["Oma Säästöpankki", "Oma Säästöpankki Oyj", "Oma Saastopankki Oyj"]
    asked = []

    def search(q):
        asked.append(q)
        hit = {"symbol": "ORNBV.HE", "quoteType": "EQUITY", "longname": "Orion Oyj"}
        other = {"symbol": "ORNBV.ST", "quoteType": "EQUITY", "longname": "Orion Oyj"}
        wrong = {"symbol": "XXX.HE", "quoteType": "EQUITY", "longname": "Something Else Oyj"}
        return [hit, other, wrong] if q == "Orion Oyj" else [wrong]

    assert s.helsinki_lines("Orion", search) == ["ORNBV.HE"] and asked == ["Orion", "Orion Oyj"]
    assert s.helsinki_lines("Nothing", lambda q: []) == []
    assert s.rewrite_section('# about [fi_small.tickers]\n[fi_small]\n[fi_small.tickers]\n"OLD.HE" = "Old"\n', {}).endswith("[fi_small.tickers]\n")


def test_wikidata_rows_become_yahoo_tickers_and_ended_listings_are_skipped():
    rows = [{"itemLabel": {"value": "Huhtamäki"}, "ticker": {"value": "HUH1V"}},
            {"itemLabel": {"value": "Gone"}, "ticker": {"value": "GONE"}, "end": {"value": "2020-01-01"}},
            {"itemLabel": {"value": "Spaced"}, "ticker": {"value": "ab c"}}, {"itemLabel": {"value": "No ticker"}}]
    assert _script().wikidata_lines(rows) == {"HUH1V.HE": "Huhtamäki", "AB-C.HE": "Spaced"}
