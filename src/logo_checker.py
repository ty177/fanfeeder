"""Verify team logo URLs are reachable; fall back to Wikipedia if not."""

from __future__ import annotations

import logging
import re
from urllib.parse import quote, urljoin

import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10
HEADERS = {
    "User-Agent": "SportDigestBot/1.0 (logo verification)",
}


def _is_url_reachable(url: str) -> bool:
    """Check if a URL returns a successful response via HEAD request."""
    try:
        resp = requests.head(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if resp.status_code == 200:
            return True
        # Some servers don't support HEAD, try GET with stream
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, stream=True)
        return resp.status_code == 200
    except requests.RequestException as e:
        logger.warning(f"Logo URL unreachable ({url}): {e}")
        return False


def _find_logo_on_wikipedia(team: dict) -> str | None:
    """Scrape the team's Wikipedia page to find the infobox logo/crest image URL.

    Reads the wikipedia_url from the team dict (populated from teams.json).
    """
    team_name = team.get("name", "Unknown")
    wiki_url = team.get("wikipedia_url")
    if not wiki_url:
        logger.warning(f"No Wikipedia URL for '{team_name}'")
        return None

    try:
        resp = requests.get(wiki_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        html = resp.text
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch Wikipedia page for '{team_name}': {e}")
        return None

    # Look for the infobox image — Wikipedia infobox logos typically appear in
    # <td class="infobox-image"> or similar, with an <img> tag whose src points
    # to upload.wikimedia.org. We look for the first image in the infobox that
    # matches common logo/crest/badge patterns.
    infobox_match = re.search(
        r'<table[^>]*class="[^"]*infobox[^"]*"[^>]*>(.*?)</table>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if not infobox_match:
        logger.warning(f"No infobox found on Wikipedia page for '{team_name}'")
        return None

    infobox_html = infobox_match.group(1)

    # Find all img tags in the infobox
    img_matches = re.findall(
        r'<img[^>]+src="([^"]+)"[^>]*/?>',
        infobox_html,
        re.IGNORECASE,
    )

    for src in img_matches:
        # Normalize protocol-relative URLs
        if src.startswith("//"):
            src = "https:" + src

        # Look for images from Wikimedia that are likely logos/crests/badges
        if "upload.wikimedia.org" not in src:
            continue

        # Skip tiny icons (like flag icons, edit icons)
        width_match = re.search(r'(?:width|(\d+)px)', src)
        if width_match and width_match.group(1):
            width = int(width_match.group(1))
            if width < 40:
                continue

        # Prefer images with logo/crest/badge in the filename
        src_lower = src.lower()
        is_likely_logo = any(
            keyword in src_lower
            for keyword in ("logo", "crest", "badge", "emblem", "shield", "seal")
        )

        if is_likely_logo:
            logger.info(f"Found Wikipedia logo for '{team_name}': {src}")
            return src

    # If no logo-specific image found, return the first reasonably-sized
    # Wikimedia image from the infobox as a best guess
    for src in img_matches:
        if src.startswith("//"):
            src = "https:" + src
        if "upload.wikimedia.org" in src:
            logger.info(f"Using first infobox image for '{team_name}': {src}")
            return src

    logger.warning(f"No suitable logo image found on Wikipedia for '{team_name}'")
    return None


def verify_logos(teams: list[dict]) -> list[dict]:
    """Verify each team's logo URL is reachable.

    If a logo is unreachable, attempts to find a replacement from Wikipedia.
    Returns the teams list with updated logo_url values where needed.
    """
    for team in teams:
        name = team["name"]
        logo_url = team.get("logo_url", "")

        if not logo_url:
            logger.warning(f"{name}: No logo URL configured")
            fallback = _find_logo_on_wikipedia(team)
            if fallback:
                team["logo_url"] = fallback
                logger.info(f"{name}: Set logo from Wikipedia")
            continue

        if _is_url_reachable(logo_url):
            logger.info(f"{name}: Logo OK")
        else:
            logger.warning(f"{name}: Logo unreachable, searching Wikipedia...")
            fallback = _find_logo_on_wikipedia(team)
            if fallback and _is_url_reachable(fallback):
                team["logo_url"] = fallback
                logger.info(f"{name}: Replaced logo with Wikipedia fallback")
            elif fallback:
                # Use it even if we can't verify — better than nothing
                team["logo_url"] = fallback
                logger.warning(f"{name}: Using unverified Wikipedia logo")
            else:
                logger.error(f"{name}: No fallback logo found, keeping original URL")

    return teams
