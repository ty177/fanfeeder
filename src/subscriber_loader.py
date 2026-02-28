"""Load team catalog and subscriber list."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from config import SUBSCRIBERS_JSON_PATH, TEAMS_JSON_PATH

logger = logging.getLogger(__name__)


def load_team_catalog(path: Path = TEAMS_JSON_PATH) -> dict:
    """Load teams.json and return a flat dict mapping team_id -> team_dict.

    Each team dict is augmented with 'sport' and 'league' fields from the
    hierarchy so downstream code doesn't need to traverse the tree.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    team_map = {}
    for sport in raw["sports"]:
        for league in sport["leagues"]:
            for team in league["teams"]:
                entry = {
                    **team,
                    "sport": sport["slug"],
                    "sport_name": sport["name"],
                    "league": league["slug"],
                    "league_name": league["name"],
                }
                team_map[team["id"]] = entry
    logger.info(f"Loaded {len(team_map)} teams from catalog")
    return team_map


def load_subscribers(path: Path = SUBSCRIBERS_JSON_PATH) -> list[dict]:
    """Load active subscribers from subscribers.json."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    active = [s for s in raw["subscribers"] if s.get("active", True)]
    logger.info(f"Loaded {len(active)} active subscribers")
    return active


def get_unique_teams(subscribers: list[dict], team_catalog: dict) -> list[dict]:
    """Get the deduplicated list of team dicts needed across all subscribers.

    Warns about any team IDs in subscriber lists that aren't in the catalog.
    """
    needed_ids = set()
    for sub in subscribers:
        needed_ids.update(sub.get("teams", []))

    teams = []
    for tid in sorted(needed_ids):
        if tid in team_catalog:
            teams.append(team_catalog[tid])
        else:
            logger.warning(f"Unknown team ID '{tid}' in subscriber data, skipping")

    logger.info(f"{len(teams)} unique teams needed across all subscribers")
    return teams
