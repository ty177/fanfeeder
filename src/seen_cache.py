"""Track previously sent headlines and videos to avoid duplicates across digests."""

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


def _load(cache_path: Path) -> dict:
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not read cache, starting fresh: {e}")
    return {"urls": {}, "video_ids": {}}


def _save(data: dict, cache_path: Path) -> None:
    cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info(f"Cache saved: {len(data['urls'])} urls, {len(data['video_ids'])} videos")


def _prune(data: dict) -> dict:
    """Remove entries older than MAX_AGE_SECONDS."""
    now = time.time()
    data["urls"] = {k: v for k, v in data["urls"].items() if now - v < MAX_AGE_SECONDS}
    data["video_ids"] = {k: v for k, v in data["video_ids"].items() if now - v < MAX_AGE_SECONDS}
    return data


def filter_new_items(
    team_data: list[dict],
    cache_path: Path = DEFAULT_CACHE_PATH,
) -> list[dict]:
    """Remove previously seen headlines and videos from team_data.

    Also records the new items in the cache for future runs.
    Returns a new list with only unseen content.
    """
    cache = _prune(_load(cache_path))
    now = time.time()
    filtered = []

    for td in team_data:
        new_headlines = []
        for h in td["headlines"]:
            url = h.get("url", "")
            if url and url not in cache["urls"]:
                new_headlines.append(h)
                cache["urls"][url] = now
            else:
                logger.debug(f"Skipping seen headline: {h.get('title', '')[:60]}")

        new_videos = []
        for v in td["videos"]:
            vid = v.get("video_id", "")
            if vid and vid not in cache["video_ids"]:
                new_videos.append(v)
                cache["video_ids"][vid] = now
            else:
                logger.debug(f"Skipping seen video: {v.get('title', '')[:60]}")

        filtered.append({
            "team": td["team"],
            "headlines": new_headlines,
            "videos": new_videos,
        })

        team_name = td["team"]["name"]
        skipped_h = len(td["headlines"]) - len(new_headlines)
        skipped_v = len(td["videos"]) - len(new_videos)
        if skipped_h or skipped_v:
            logger.info(f"{team_name}: skipped {skipped_h} duplicate headlines, {skipped_v} duplicate videos")

    _save(cache, cache_path)
    return filtered
