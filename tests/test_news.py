from datetime import date

from engine.news import feed_url, parse_rss, summarize_news

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
