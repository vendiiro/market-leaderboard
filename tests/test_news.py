from datetime import date

import json

from engine.news import feed_url, hn_url, merge_items, parse_hn, parse_rss, summarize_news

TODAY = date(2026, 11, 18)


def rss(*items: tuple[str, str, str]) -> str:
    body = "".join(f"<item><title>{t}</title><link>{u}</link><pubDate>{d}</pubDate><source>Wire</source></item>" for t, u, d in items)
    return f"<rss><channel>{body}</channel></rss>"


XML = rss(
    ("Acme wins big order - Wire", "https://example.com/a", "Tue, 17 Nov 2026 08:00:00 GMT"),
    ("Acme wins big order - Wire", "https://example.com/a2", "Tue, 17 Nov 2026 09:00:00 GMT"),       # duplicate title
    ("Acme CEO steps down", "javascript:alert(1)", "Sat, 07 Nov 2026 08:00:00 GMT"),                  # unsafe link
    ("Acme quarterly report", "https://example.com/c", "Thu, 22 Oct 2026 08:00:00 GMT"),              # 27 days old
    ("Acme old story", "https://example.com/d", "Mon, 05 Oct 2026 08:00:00 GMT"),                     # outside 30 days
    ("Unrelated sports result", "https://example.com/e", "Mon, 16 Nov 2026 08:00:00 GMT"),
    ("Acme undated", "https://example.com/f", ""),
)


def test_window_duplicates_links_and_order():
    items = parse_rss(XML, TODAY)
    assert [i["title"] for i in items] == ["Acme wins big order - Wire", "Unrelated sports result", "Acme CEO steps down", "Acme quarterly report"]
    assert items[2]["url"] is None and items[0]["url"] == "https://example.com/a"


def test_terms_drop_unrelated_stories():
    assert all("Acme" in i["title"] for i in parse_rss(XML, TODAY, terms=("acme",)))


def test_summary_counts_by_week_oldest_first():
    s = summarize_news(parse_rss(XML, TODAY, terms=("acme",)), "ACME", "Acme Oy", TODAY)
    assert s["count"] == 3 and s["per_week"] == [1, 0, 1, 1] and sum(s["per_week"]) == s["count"]


def test_empty_feed_is_an_honest_zero():
    s = summarize_news(parse_rss(rss(), TODAY), "X", "X Oy", TODAY)
    assert s["count"] == 0 and s["items"] == [] and s["per_week"] == [0, 0, 0, 0]


def test_feed_url_uses_name_and_ticker_base():
    u = feed_url("Nokia Oyj", "NOKIA.HE")
    assert "when%3A30d" in u and "NOKIA" in u and ".HE" not in u


def test_capped_flag_marks_a_full_feed():
    assert summarize_news([], "X", "X Oy", TODAY, raw_count=100)["capped"] is True
    assert summarize_news([], "X", "X Oy", TODAY, raw_count=40)["capped"] is False


def _ts(day: str) -> int:
    from datetime import datetime, timezone
    return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()) + 3600


HN = json.dumps({"hits": [
    {"title": "Acme open-sources its router", "url": "https://example.com/router", "created_at_i": _ts("2026-11-15"), "objectID": "1"},
    {"title": "Ask HN: anyone use Acme?", "url": None, "created_at_i": _ts("2026-11-10"), "objectID": "2"},
    {"title": "Acme open-sources its router", "url": "https://example.com/dup", "created_at_i": _ts("2026-11-15"), "objectID": "3"},
    {"title": "Acme from long ago", "url": "https://example.com/old", "created_at_i": _ts("2026-09-01"), "objectID": "4"},
    {"title": "Something else", "url": "https://example.com/x", "created_at_i": _ts("2026-11-16"), "objectID": "5"},
    {"title": "Acme bad link", "url": "javascript:alert(1)", "created_at_i": _ts("2026-11-12"), "objectID": "6"},
]})


def test_hn_window_dupes_links_and_terms():
    items = parse_hn(HN, TODAY, terms=("acme",))
    assert [i["title"] for i in items] == ["Acme open-sources its router", "Acme bad link", "Ask HN: anyone use Acme?"]
    assert items[0]["source"] == "Hacker News" and items[0]["url"] == "https://example.com/router"
    assert items[1]["url"] == "https://news.ycombinator.com/item?id=6"      # unsafe link replaced by the HN page
    assert items[2]["url"] == "https://news.ycombinator.com/item?id=2"      # no own link: the HN page


def test_hn_url_filters_to_the_window():
    u = hn_url("Acme Corp", TODAY)
    assert "query=Acme%20Corp" in u and "tags=story" in u and "created_at_i%3E" in u


def test_merge_keeps_one_entry_per_headline_newest_first():
    a = [{"title": "Same", "source": "A", "url": None, "date": "2026-11-10"}]
    b = [{"title": "same", "source": "B", "url": None, "date": "2026-11-10"}, {"title": "New", "source": "B", "url": None, "date": "2026-11-16"}]
    assert [i["title"] for i in merge_items(a, b)] == ["New", "Same"]


def test_summary_carries_its_group():
    assert summarize_news([], "X", "X Oy", TODAY, group="candidate")["group"] == "candidate"
