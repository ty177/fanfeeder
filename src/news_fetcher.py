"""Fetch news headlines from Google News RSS feeds."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import quote

import feedparser
import requests

from config import MAX_HEADLINES_PER_TEAM

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

# Google News returns malformed XML to feedparser's default UA; a browser UA fixes it.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; FanFeeder/1.0; +https://fanfeeder.fire-exit.com)"
    )
}


def _decode_google_news_url(google_url: str) -> str:
    """Attempt to decode a Google News redirect URL to the real article URL.

    Falls back to the Google URL if decoding fails.
    """
    try:
        from googlenewsdecoder import new_decoders
        decoded = new_decoders.decode_url(google_url)
        if decoded and decoded.get("decoded_url"):
            return decoded["decoded_url"]
    except Exception as e:
        logger.debug(f"Could not decode Google News URL: {e}")
    return google_url


def _extract_source(entry) -> str:
    """Extract the news source name from a feed entry."""
    if hasattr(entry, "source") and hasattr(entry.source, "title"):
        return entry.source.title
    # Fallback: source is often appended after " - " in the title
    if " - " in entry.get("title", ""):
        return entry["title"].rsplit(" - ", 1)[-1].strip()
    return ""


def _clean_title(title: str) -> str:
    """Remove source suffix from title if present."""
    if " - " in title:
        return title.rsplit(" - ", 1)[0].strip()
    return title


def fetch_news(query: str, max_items: int = MAX_HEADLINES_PER_TEAM) -> list[dict]:
    """Fetch top news headlines for a search query.

    Returns a list of dicts with keys: title, url, source, published
    """
    url = GOOGLE_NEWS_RSS.format(query=quote(query))
    logger.info(f"Fetching news for: {query}")

    try:
        # Fetch manually so we can send a browser UA — feedparser's default UA
        # causes Google News to return malformed XML.
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except Exception as e:
        logger.error(f"Failed to fetch RSS feed for '{query}': {e}")
        return []

    if feed.bozo and not feed.entries:
        logger.warning(f"RSS feed error for '{query}': {feed.bozo_exception}")
        return []

    headlines = []
    for entry in feed.entries[:max_items]:
        raw_title = entry.get("title", "No title")
        source = _extract_source(entry)
        title = _clean_title(raw_title)
        google_url = entry.get("link", "")
        real_url = _decode_google_news_url(google_url)

        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

        headlines.append({
            "title": title,
            "url": real_url,
            "source": source,
            "published": published,
        })

    logger.info(f"Found {len(headlines)} headlines for '{query}'")
    return headlines
