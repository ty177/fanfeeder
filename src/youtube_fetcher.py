"""Fetch YouTube videos via channel RSS feeds and yt-dlp search fallback."""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

import feedparser

from config import MAX_VIDEOS_PER_TEAM

logger = logging.getLogger(__name__)


def _fetch_from_rss(channel_feed_urls: list[str], max_items: int) -> list[dict]:
    """Fetch recent videos from YouTube channel RSS feeds."""
    videos = []
    for feed_url in channel_feed_urls:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                video_id = entry.get("yt_videoid", "")
                if not video_id:
                    link = entry.get("link", "")
                    if "v=" in link:
                        video_id = link.split("v=")[-1].split("&")[0]
                if not video_id:
                    continue

                url = f"https://www.youtube.com/watch?v={video_id}"
                # Skip Shorts-style URLs
                if "/shorts/" in entry.get("link", ""):
                    continue

                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                videos.append({
                    "title": entry.get("title", "Untitled"),
                    "url": url,
                    "video_id": video_id,
                    "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                    "published": published,
                })
        except Exception as e:
            logger.warning(f"Failed to parse YouTube RSS feed {feed_url}: {e}")

    # Sort by most recent, deduplicate by video_id
    seen = set()
    unique = []
    for v in sorted(videos, key=lambda x: x.get("published") or datetime.min.replace(tzinfo=timezone.utc), reverse=True):
        if v["video_id"] not in seen:
            seen.add(v["video_id"])
            unique.append(v)

    return unique[:max_items]


def _fetch_from_ytdlp(query: str, max_items: int) -> list[dict]:
    """Search YouTube using yt-dlp as a fallback."""
    search_url = f"ytsearch{max_items * 2}:{query}"
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--flat-playlist",
                "--dump-json",
                "--no-warnings",
                "--quiet",
                search_url,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.warning(f"yt-dlp search failed: {result.stderr[:200]}")
            return []

        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            video_id = data.get("id", "")
            duration = data.get("duration") or 0
            url = data.get("url", "") or data.get("webpage_url", "") or f"https://www.youtube.com/watch?v={video_id}"

            # Skip Shorts (typically under 60 seconds)
            if duration and duration < 61:
                continue
            if "/shorts/" in url:
                continue
            if not video_id:
                continue

            videos.append({
                "title": data.get("title", "Untitled"),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "video_id": video_id,
                "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                "published": None,
            })

            if len(videos) >= max_items:
                break

        return videos

    except subprocess.TimeoutExpired:
        logger.warning("yt-dlp search timed out")
        return []
    except FileNotFoundError:
        logger.warning("yt-dlp not found, skipping YouTube search fallback")
        return []
    except Exception as e:
        logger.warning(f"yt-dlp search error: {e}")
        return []


def fetch_videos(
    query: str,
    channel_feed_urls: list[str] | None = None,
    max_items: int = MAX_VIDEOS_PER_TEAM,
) -> list[dict]:
    """Fetch YouTube videos for a team.

    Tries channel RSS feeds first, falls back to yt-dlp search.
    Returns list of dicts with: title, url, video_id, thumbnail, published
    """
    logger.info(f"Fetching YouTube videos for: {query}")

    videos = []
    if channel_feed_urls:
        videos = _fetch_from_rss(channel_feed_urls, max_items)
        logger.info(f"RSS feeds returned {len(videos)} videos")

    if len(videos) < max_items:
        remaining = max_items - len(videos)
        fallback = _fetch_from_ytdlp(query, remaining)
        # Deduplicate
        existing_ids = {v["video_id"] for v in videos}
        for v in fallback:
            if v["video_id"] not in existing_ids:
                videos.append(v)
                if len(videos) >= max_items:
                    break
        logger.info(f"After yt-dlp fallback: {len(videos)} total videos")

    return videos[:max_items]
