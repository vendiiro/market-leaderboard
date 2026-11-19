"""Turns one last30days engine run into the small summary the Research panel shows.

Pure: no network. scripts/sentiment.py runs the engine and calls summarize(). The text is third-party and shown as
received (trimmed); it is context, not a score, and nothing here has been tested as a predictor."""
from __future__ import annotations

SOURCES = ("reddit", "hackernews", "polymarket", "github", "grounding")
MAX_TITLE = 160


def _safe_url(url: object) -> str | None:
    return url if isinstance(url, str) and url.startswith(("http://", "https://")) else None


def summarize(raw: dict, ticker: str, asof: str, top: int = 5, terms: tuple[str, ...] = ()) -> dict:
    """Per source: the run's status and how many items it returned; plus the `top` most relevant items overall.
    With `terms` (company name words, ticker), items whose title names none of them are dropped: the engine's
    search is fuzzy and returns unrelated stories for small or oddly named companies."""
    results = [r for r in raw.get("results", []) if r.get("source") in SOURCES]
    if terms:
        results = [r for r in results if any(t.lower() in str(r.get("title") or "").lower() for t in terms)]
    status = raw.get("source_status", {})
    sources = {
        s: {"status": status.get(s, "not-run"), "items": sum(1 for r in results if r["source"] == s)}
        for s in SOURCES if s in status or any(r["source"] == s for r in results)
    }
    ranked = sorted(results, key=lambda r: r.get("relevance_score") or 0, reverse=True)[:top]
    items = [{
        "title": str(r.get("title") or "")[:MAX_TITLE],
        "source": r["source"],
        "url": _safe_url(r.get("url")),
        "date": r.get("published_at"),
        "relevance": round(float(r.get("relevance_score") or 0), 2),
        "engagement": r.get("engagement") or {},
    } for r in ranked]
    return {"ticker": ticker, "asof": asof, "window_days": raw.get("window_days", 30), "sources": sources, "items": items}


def extract_json(text: str) -> dict:
    """The engine prints progress lines before the JSON object; read from the first line that starts it."""
    start = text.find("\n{")
    start = 0 if text.startswith("{") else start + 1
    if start < 0 or not text[start:].startswith("{"):
        raise ValueError("no JSON object in engine output")
    import json
    return json.JSONDecoder().raw_decode(text[start:])[0]
