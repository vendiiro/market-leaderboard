import json
from pathlib import Path

from engine.sentiment import SOURCES, summarize

RAW = json.loads((Path(__file__).parent / "fixtures" / "last30days_nvda.json").read_text(encoding="utf-8"))


def test_counts_and_statuses_cover_only_the_chosen_sources():
    s = summarize(RAW, "NVDA", "2026-11-18")
    assert s["ticker"] == "NVDA" and s["window_days"] == 30
    assert set(s["sources"]) <= set(SOURCES)          # yahoo_finance and others are dropped
    assert s["sources"]["hackernews"] == {"status": "ok", "items": 1}
    assert s["sources"]["reddit"]["items"] == 0


def test_items_are_ranked_capped_and_safe():
    s = summarize(RAW, "NVDA", "2026-11-18", top=3)
    assert len(s["items"]) == 3
    scores = [i["relevance"] for i in s["items"]]
    assert scores == sorted(scores, reverse=True)
    assert all(i["url"] is None or i["url"].startswith(("http://", "https://")) for i in s["items"])


def test_third_party_text_is_trimmed_and_bad_urls_removed():
    raw = {"window_days": 30, "source_status": {}, "results": [
        {"source": "reddit", "title": "x" * 500, "url": "javascript:alert(1)", "published_at": "2026-11-01", "relevance_score": 1.0, "engagement": {}},
    ]}
    item = summarize(raw, "X", "2026-11-18")["items"][0]
    assert len(item["title"]) <= 160 and item["url"] is None


def test_empty_or_failed_run_gives_an_honest_empty_summary():
    s = summarize({"results": [], "source_status": {"reddit": "rate-limited"}}, "X", "2026-11-18")
    assert s["items"] == [] and s["sources"]["reddit"]["status"] == "rate-limited"


def test_extract_json_skips_progress_lines():
    from engine.sentiment import extract_json
    assert extract_json('/last30days · researching\nResearch complete\n{"results": [], "window_days": 30}\n') == {"results": [], "window_days": 30}
    try:
        extract_json("only progress text")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_terms_drop_unrelated_stories():
    s = summarize(RAW, "NVDA", "2026-11-18", terms=("nvidia",))
    assert s["items"] and all("nvidia" in i["title"].lower() for i in s["items"])
    assert summarize(RAW, "ZZZ", "2026-11-18", terms=("zzzcorp",))["items"] == []
