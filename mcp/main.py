"""FanFeeder MCP Server — live sports news queries for LLM environments.

Exposes tools so an LLM can ask:
  "What's the latest news about my teams?"
  "Show me Manchester City highlights"
  "Add the Lakers to my digest"
  "Remove Barcelona from my FanFeeder"

Subscriber identity is handled by email → SHA-256 hash, matching the
public subscribers_index.json published to GitHub Pages.

Subscription writes go through the same Formspree endpoint the web UI uses,
so the existing GitHub Actions pipeline processes them unchanged.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

import feedparser
import requests
from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# News cache — avoids hammering Google News on repeated MCP queries
# ---------------------------------------------------------------------------
_NEWS_CACHE: dict[str, tuple[float, list]] = {}  # query -> (timestamp, results)
_NEWS_TTL = 20 * 60  # 20 minutes


def _cached_fetch_news(query: str, max_items: int = 5) -> list[dict]:
    now = time.time()
    if query in _NEWS_CACHE:
        ts, results = _NEWS_CACHE[query]
        if now - ts < _NEWS_TTL:
            return results
    results = _fetch_news(query, max_items)
    _NEWS_CACHE[query] = (now, results)
    return results

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fanfeeder-mcp")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SITE_URL = os.environ.get("FANFEEDER_SITE", "https://fanfeeder.fire-exit.com")
FORMSPREE_ENDPOINT = os.environ.get(
    "FORMSPREE_ENDPOINT", "https://formspree.io/f/mzdawwjk"
)
TEAMS_JSON_URL = f"{SITE_URL}/teams.json"
INDEX_URL = f"{SITE_URL}/subscribers_index.json"

MAX_HEADLINES = 5
MAX_VIDEOS = 3

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; FanFeeder-MCP/1.0; +https://fanfeeder.fire-exit.com)"
    )
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_teams_cache: dict | None = None


def _get_teams() -> dict:
    """Fetch and cache teams.json from GitHub Pages. Returns flat id -> team dict."""
    global _teams_cache
    if _teams_cache is not None:
        return _teams_cache
    resp = requests.get(TEAMS_JSON_URL, timeout=10)
    resp.raise_for_status()
    raw = resp.json()
    flat: dict = {}
    for sport in raw["sports"]:
        for league in sport["leagues"]:
            for team in league["teams"]:
                flat[team["id"]] = {
                    **team,
                    "sport": sport["slug"],
                    "sport_name": sport["name"],
                    "league": league["slug"],
                    "league_name": league["name"],
                }
    _teams_cache = flat
    return flat


def _sha256(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


def _get_subscriber_team_ids(email: str) -> list[str]:
    """Look up subscriber's team IDs using the public hash index."""
    h = _sha256(email)
    resp = requests.get(INDEX_URL, timeout=10)
    if not resp.ok:
        return []
    index = resp.json()
    return index.get(h, [])


def _find_team_by_name(query: str, teams: dict) -> dict | None:
    """Case-insensitive search on name, short_name, and id."""
    q = query.strip().lower()
    # Exact ID match first
    if q in teams:
        return teams[q]
    # Then search names
    for team in teams.values():
        if (
            team["name"].lower() == q
            or team.get("short_name", "").lower() == q
            or team["id"].lower() == q
        ):
            return team
    # Partial match
    for team in teams.values():
        if q in team["name"].lower() or q in team.get("short_name", "").lower():
            return team
    return None


def _fetch_news(query: str, max_items: int = MAX_HEADLINES) -> list[dict]:
    """Fetch Google News RSS with a browser User-Agent (avoids malformed XML)."""
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except Exception as e:
        logger.error(f"News fetch failed for '{query}': {e}")
        return []

    if feed.bozo and not feed.entries:
        return []

    results = []
    for entry in feed.entries[:max_items]:
        raw_title = entry.get("title", "")
        title = raw_title.rsplit(" - ", 1)[0].strip() if " - " in raw_title else raw_title
        source = ""
        if hasattr(entry, "source") and hasattr(entry.source, "title"):
            source = entry.source.title
        elif " - " in raw_title:
            source = raw_title.rsplit(" - ", 1)[-1].strip()

        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()

        results.append({
            "title": title,
            "url": entry.get("link", ""),
            "source": source,
            "published": published,
        })
    return results


def _fetch_videos(query: str, channel_urls: list[str] | None = None, max_items: int = MAX_VIDEOS) -> list[dict]:
    """Fetch YouTube videos via channel RSS, fall back to yt-dlp search."""
    videos: list[dict] = []

    if channel_urls:
        for feed_url in channel_urls:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    vid = entry.get("yt_videoid", "")
                    if not vid and "v=" in entry.get("link", ""):
                        vid = entry["link"].split("v=")[-1].split("&")[0]
                    if not vid or "/shorts/" in entry.get("link", ""):
                        continue
                    published = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
                    videos.append({
                        "title": entry.get("title", "Untitled"),
                        "url": f"https://www.youtube.com/watch?v={vid}",
                        "thumbnail": f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
                        "published": published,
                    })
            except Exception:
                pass

    if len(videos) < max_items:
        remaining = max_items - len(videos)
        try:
            result = subprocess.run(
                ["yt-dlp", "--flat-playlist", "--dump-json", "--no-warnings", "--quiet",
                 f"ytsearch{remaining * 2}:{query}"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                seen_ids = {v["url"].split("v=")[-1] for v in videos}
                for line in result.stdout.strip().split("\n"):
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    vid = d.get("id", "")
                    duration = d.get("duration") or 0
                    url = d.get("url") or d.get("webpage_url") or f"https://www.youtube.com/watch?v={vid}"
                    if not vid or vid in seen_ids or duration < 61 or "/shorts/" in url:
                        continue
                    seen_ids.add(vid)
                    videos.append({
                        "title": d.get("title", "Untitled"),
                        "url": f"https://www.youtube.com/watch?v={vid}",
                        "thumbnail": f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
                        "published": None,
                    })
                    if len(videos) >= max_items:
                        break
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass

    return videos[:max_items]


def _post_to_formspree(email: str, teams: list[str], action: str = "subscribe") -> bool:
    """Submit an update to Formspree (same endpoint as the web UI)."""
    try:
        resp = requests.post(
            FORMSPREE_ENDPOINT,
            data={"email": email, "teams": ",".join(teams), "action": action},
            headers={"Accept": "application/json"},
            timeout=15,
        )
        return resp.ok
    except Exception as e:
        logger.error(f"Formspree POST failed: {e}")
        return False


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP("FanFeeder")


@mcp.tool()
def list_my_teams(email: str) -> str:
    """List the sports teams on your FanFeeder subscription.

    Args:
        email: Your FanFeeder subscription email address.
    """
    team_ids = _get_subscriber_team_ids(email)
    if not team_ids:
        return f"No active FanFeeder subscription found for {email}. Visit {SITE_URL} to subscribe."

    teams = _get_teams()
    lines = []
    for tid in team_ids:
        t = teams.get(tid)
        if t:
            lines.append(f"• {t['name']} ({t['league_name']}, {t['sport_name']})")
        else:
            lines.append(f"• {tid} (unknown team)")

    return f"Your FanFeeder teams ({len(lines)}):\n" + "\n".join(lines)


@mcp.tool()
def get_my_news(email: str, include_videos: bool = True) -> str:
    """Get the latest news headlines and YouTube highlights for your subscribed teams.

    Args:
        email: Your FanFeeder subscription email address.
        include_videos: Whether to include YouTube video links (default True).
    """
    team_ids = _get_subscriber_team_ids(email)
    if not team_ids:
        return f"No active FanFeeder subscription found for {email}. Visit {SITE_URL} to subscribe."

    teams = _get_teams()
    sections: list[str] = []

    for tid in team_ids:
        t = teams.get(tid)
        if not t:
            continue

        news_query = t.get("news_query") or t["name"]
        headlines = _cached_fetch_news(news_query)

        block = [f"\n## {t['name']}"]
        if headlines:
            block.append("**Headlines:**")
            for h in headlines:
                pub = f" ({h['published'][:10]})" if h.get("published") else ""
                block.append(f"- [{h['title']}]({h['url']}){pub}")
        else:
            block.append("*No recent headlines found.*")

        if include_videos:
            videos = _fetch_videos(
                t.get("youtube_query") or t["name"],
                t.get("channel_feed_urls"),
            )
            if videos:
                block.append("\n**Highlights:**")
                for v in videos:
                    block.append(f"- [{v['title']}]({v['url']})")

        sections.append("\n".join(block))

    if not sections:
        return "Could not load content. The team catalog may be temporarily unavailable."

    return f"# FanFeeder — Latest for your teams\n" + "\n".join(sections)


@mcp.tool()
def get_team_news(team_name: str, include_videos: bool = True) -> str:
    """Get the latest news and highlights for a specific team by name.

    Works for any team in the FanFeeder catalog, not just your subscribed ones.

    Args:
        team_name: Team name, short name, or ID (e.g. "Arsenal", "Man City", "nfl-kansas-city-chiefs").
        include_videos: Whether to include YouTube video links (default True).
    """
    teams = _get_teams()
    t = _find_team_by_name(team_name, teams)
    if not t:
        available = sorted({v["sport_name"] for v in teams.values()})
        return (
            f"Team '{team_name}' not found. Try a name like 'Arsenal', 'Golden State Warriors', "
            f"or 'Kansas City Chiefs'. Available sports: {', '.join(available)}."
        )

    news_query = t.get("news_query") or t["name"]
    headlines = _cached_fetch_news(news_query)

    lines = [f"# {t['name']} ({t['league_name']})"]

    if headlines:
        lines.append("\n**Latest headlines:**")
        for h in headlines:
            pub = f" ({h['published'][:10]})" if h.get("published") else ""
            lines.append(f"- [{h['title']}]({h['url']}){pub}")
    else:
        lines.append("\n*No recent headlines found.*")

    if include_videos:
        videos = _fetch_videos(
            t.get("youtube_query") or t["name"],
            t.get("channel_feed_urls"),
        )
        if videos:
            lines.append("\n**Highlights:**")
            for v in videos:
                lines.append(f"- [{v['title']}]({v['url']})")

    return "\n".join(lines)


@mcp.tool()
def list_available_teams(sport: Optional[str] = None, search: Optional[str] = None) -> str:
    """Browse all teams available in the FanFeeder catalog.

    Args:
        sport: Filter by sport slug (e.g. "soccer", "basketball", "american-football", "baseball").
               Leave empty to see all sports.
        search: Optional keyword to filter team names (e.g. "city", "united", "warriors").
    """
    teams = _get_teams()
    filtered = list(teams.values())

    if sport:
        sport_lower = sport.lower()
        filtered = [t for t in filtered if sport_lower in t["sport"].lower() or sport_lower in t["sport_name"].lower()]

    if search:
        q = search.lower()
        filtered = [
            t for t in filtered
            if q in t["name"].lower() or q in t.get("short_name", "").lower()
        ]

    if not filtered:
        return f"No teams found matching sport='{sport}' search='{search}'."

    # Group by sport > league
    grouped: dict[str, dict[str, list]] = {}
    for t in sorted(filtered, key=lambda x: (x["sport_name"], x["league_name"], x["name"])):
        grouped.setdefault(t["sport_name"], {}).setdefault(t["league_name"], []).append(t["name"])

    lines = [f"FanFeeder team catalog ({len(filtered)} teams):"]
    for sport_name, leagues in grouped.items():
        lines.append(f"\n**{sport_name}**")
        for league_name, team_names in leagues.items():
            lines.append(f"  {league_name}: {', '.join(team_names)}")

    return "\n".join(lines)


@mcp.tool()
def add_teams(email: str, team_names: list[str]) -> str:
    """Add one or more teams to your FanFeeder digest.

    Changes take effect on the next digest send (up to 12 hours).

    Args:
        email: Your FanFeeder subscription email address.
        team_names: List of team names to add (e.g. ["Arsenal", "Lakers"]).
    """
    teams = _get_teams()
    current_ids = set(_get_subscriber_team_ids(email))

    resolved: list[str] = []
    not_found: list[str] = []
    already_have: list[str] = []

    for name in team_names:
        t = _find_team_by_name(name, teams)
        if not t:
            not_found.append(name)
        elif t["id"] in current_ids:
            already_have.append(t["name"])
        else:
            current_ids.add(t["id"])
            resolved.append(t["name"])

    if not resolved and not not_found:
        return "You already have all of those teams. No changes made."

    new_ids = list(current_ids)
    ok = _post_to_formspree(email, new_ids, action="subscribe")

    parts: list[str] = []
    if resolved:
        parts.append(f"Added: {', '.join(resolved)}.")
    if already_have:
        parts.append(f"Already subscribed: {', '.join(already_have)}.")
    if not_found:
        parts.append(f"Not found (check spelling): {', '.join(not_found)}.")

    if not ok:
        parts.append("Warning: the subscription update may not have gone through. Try again or visit the FanFeeder website.")
    else:
        parts.append("Your digest will reflect this on the next send (up to 12 hours).")

    return " ".join(parts)


@mcp.tool()
def remove_teams(email: str, team_names: list[str]) -> str:
    """Remove one or more teams from your FanFeeder digest.

    Changes take effect on the next digest send (up to 12 hours).

    Args:
        email: Your FanFeeder subscription email address.
        team_names: List of team names to remove (e.g. ["Arsenal", "Lakers"]).
    """
    teams = _get_teams()
    current_ids = set(_get_subscriber_team_ids(email))

    if not current_ids:
        return f"No active FanFeeder subscription found for {email}."

    removed: list[str] = []
    not_found: list[str] = []
    not_subscribed: list[str] = []

    for name in team_names:
        t = _find_team_by_name(name, teams)
        if not t:
            not_found.append(name)
        elif t["id"] not in current_ids:
            not_subscribed.append(t["name"])
        else:
            current_ids.discard(t["id"])
            removed.append(t["name"])

    if not removed:
        return f"No changes made. Not subscribed: {', '.join(not_subscribed or not_found)}."

    new_ids = list(current_ids)

    if new_ids:
        ok = _post_to_formspree(email, new_ids, action="subscribe")
        action_desc = f"Removed: {', '.join(removed)}."
    else:
        ok = _post_to_formspree(email, [], action="unsubscribe")
        action_desc = f"Removed: {', '.join(removed)}. No teams remain — you've been unsubscribed."

    parts = [action_desc]
    if not_subscribed:
        parts.append(f"Wasn't subscribed: {', '.join(not_subscribed)}.")
    if not_found:
        parts.append(f"Not found: {', '.join(not_found)}.")
    if not ok:
        parts.append("Warning: the update may not have gone through. Try again or visit the website.")
    else:
        parts.append("Your digest will reflect this on the next send (up to 12 hours).")

    return " ".join(parts)


@mcp.tool()
def unsubscribe(email: str) -> str:
    """Unsubscribe from FanFeeder entirely. Stops all digest emails.

    Args:
        email: Your FanFeeder subscription email address.
    """
    ok = _post_to_formspree(email, [], action="unsubscribe")
    if ok:
        return f"Unsubscribed {email} from FanFeeder. You won't receive any more digests."
    return "Something went wrong. Please try again or visit https://fanfeeder.fire-exit.com/unsubscribe.html."


if __name__ == "__main__":
    import sys
    transport = os.environ.get("MCP_TRANSPORT", "sse")
    port = int(os.environ.get("PORT", 8000))

    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="sse", host="0.0.0.0", port=port)
