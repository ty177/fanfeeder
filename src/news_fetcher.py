"""Fetch news headlines from Google News RSS feeds."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from urllib.parse import quote

import feedparser
import requests

from config import MAX_HEADLINES_PER_TEAM

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

# Rotate User-Agents so retries look like different clients to Google News.
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
]

_ua_index = 0


def _next_headers() -> dict:
    global _ua_index
    ua = _USER_AGENTS[_ua_index % len(_USER_AGENTS)]
    _ua_index += 1
    return {"User-Agent": ua}


def _decode_google_news_url(google_url: str) -> str:
    try:
        from googlenewsdecoder import new_decoders
        decoded = new_decoders.decode_url(google_url)
        if decoded and decoded.get("decoded_url"):
            return decoded["decoded_url"]
    except Exception as e:
        logger.debug(f"Could not decode Google News URL: {e}")
    return google_url


def _extract_source(entry) -> str:
    if hasattr(entry, "source") and hasattr(entry.source, "title"):
        return entry.source.title
    if " - " in entry.get("title", ""):
        return entry["title"].rsplit(" - ", 1)[-1].strip()
    return ""


def _clean_title(title: str) -> str:
    if " - " in title:
        return title.rsplit(" - ", 1)[0].strip()
    return title


def fetch_news(query: str, max_items: int = MAX_HEADLINES_PER_TEAM) -> list[dict]:
    """Fetch top news headlines for a search query.

    Retries up to 3 times with exponential backoff on 429/503 responses.
    Rotates User-Agent on each attempt to avoid IP-based blocks.

    Returns a list of dicts with keys: title, url, source, published
    """
    url = GOOGLE_NEWS_RSS.format(query=quote(query))
    logger.info(f"Fetching news for: {query}")

    last_error = None
    for attempt in range(3):
        if attempt > 0:
            delay = 2 ** attempt  # 2s, 4s
            logger.info(f"Retrying '{query}' in {delay}s (attempt {attempt + 1}/3)")
            time.sleep(delay)

        try:
            resp = requests.get(url, headers=_next_headers(), timeout=20)
            if resp.status_code in (429, 503):
                last_error = f"HTTP {resp.status_code}"
                logger.warning(f"Google News returned {resp.status_code} for '{query}', will retry")
                continue
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Fetch error for '{query}': {e}")
            continue

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

    logger.error(f"Failed to fetch news for '{query}' after 3 attempts: {last_error}")
    return []
