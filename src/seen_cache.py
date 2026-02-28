"""Track previously sent headlines and videos to avoid duplicates across digests.

Cache is per-subscriber so each subscriber independently receives fresh content.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Cache lives one directory above src/, at the project root
DEFAULT_CACHE_PATH = Path(__file__).parent.parent / ".seen_cache.json"

# Items older than 3 days are pruned to keep the cache small
MAX_AGE_SECONDS = 3 * 24 * 60 * 60


def _load_all(cache_path: Path) -> dict:
    """Load the full cache file. Auto-migrates old flat format."""
    if not cache_path.exists():
        return {}
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not read cache, starting fresh: {e}")
        return {}

    # Migrate old flat format {"urls": {...}, "video_ids": {...}}
    # to per-subscriber format {"email": {"urls": {...}, "video_ids": {...}}}
    if "urls" in data and "video_ids" in data and not any("@" in k for k in data):
        logger.info("Migrating old cache format to per-subscriber format")
        old_data = {"urls": data["urls"], "video_ids": data["video_ids"]}
        # Assign old cache to the original subscriber
        return {"tyahma@gmail.com": old_data}

    return data


def _save_all(data: dict, cache_path: Path) -> None:
    """Save the full cache file."""
    total_urls = sum(len(v.get("urls", {})) for v in data.values())
    total_vids = sum(len(v.get("video_ids", {})) for v in data.values())
    cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info(f"Cache saved: {len(data)} subscribers, {total_urls} urls, {total_vids} videos")


def _prune_subscriber(sub_cache: dict) -> dict:
    """Remove entries older than MAX_AGE_SECONDS from a subscriber's cache."""
    now = time.time()
    sub_cache["urls"] = {
        k: v for k, v in sub_cache.get("urls", {}).items()
        if now - v < MAX_AGE_SECONDS
    }
    sub_cache["video_ids"] = {
        k: v for k, v in sub_cache.get("video_ids", {}).items()
        if now - v < MAX_AGE_SECONDS
    }
    return sub_cache


def filter_new_items(
    team_data: list[dict],
    subscriber_key: str,
    cache_path: Path = DEFAULT_CACHE_PATH,
) -> list[dict]:
    """Remove previously seen headlines and videos for a specific subscriber.

    Each subscriber has their own section in the cache, so subscriber A seeing
    a headline doesn't prevent subscriber B from also receiving it.

    Args:
        team_data: List of dicts with keys: team, headlines, videos
        subscriber_key: Email address used as the cache key
        cache_path: Path to the cache JSON file

    Returns:
        New list with only unseen content for this subscriber.
    """
    all_cache = _load_all(cache_path)
    sub_cache = _prune_subscriber(
        all_cache.get(subscriber_key, {"urls": {}, "video_ids": {}})
    )
    now = time.time()
    filtered = []

    for td in team_data:
        new_headlines = []
        for h in td["headlines"]:
            url = h.get("url", "")
            if url and url not in sub_cache["urls"]:
                new_headlines.append(h)
                sub_cache["urls"][url] = now
            else:
                logger.debug(f"[{subscriber_key}] Skipping seen headline: {h.get('title', '')[:60]}")

        new_videos = []
        for v in td["videos"]:
            vid = v.get("video_id", "")
            if vid and vid not in sub_cache["video_ids"]:
                new_videos.append(v)
                sub_cache["video_ids"][vid] = now
            else:
                logger.debug(f"[{subscriber_key}] Skipping seen video: {v.get('title', '')[:60]}")

        filtered.append({
            "team": td["team"],
            "headlines": new_headlines,
            "videos": new_videos,
        })

        team_name = td["team"]["name"]
        skipped_h = len(td["headlines"]) - len(new_headlines)
        skipped_v = len(td["videos"]) - len(new_videos)
        if skipped_h or skipped_v:
            logger.info(f"{team_name} [{subscriber_key}]: skipped {skipped_h} dup headlines, {skipped_v} dup videos")

    all_cache[subscriber_key] = sub_cache
    _save_all(all_cache, cache_path)
    return filtered
