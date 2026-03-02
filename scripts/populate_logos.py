#!/usr/bin/env python3
"""One-time script to populate logo_url in docs/teams.json using Wikipedia scraping.

Usage:
    python scripts/populate_logos.py             # Populate logos and sort teams
    python scripts/populate_logos.py --dry-run   # Show what would change without writing
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Add src/ to path so we can import logo_checker
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from logo_checker import _find_logo_on_wikipedia  # noqa: E402

TEAMS_JSON = PROJECT_ROOT / "docs" / "teams.json"


def main():
    parser = argparse.ArgumentParser(description="Populate team logos from Wikipedia")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    args = parser.parse_args()

    with open(TEAMS_JSON, encoding="utf-8") as f:
        data = json.load(f)

    total = 0
    found = 0
    failed = []

    for sport in data["sports"]:
        for league in sport["leagues"]:
            # Sort teams alphabetically by name
            league["teams"].sort(key=lambda t: t["name"])

            for team in league["teams"]:
                total += 1
                if team.get("logo_url"):
                    print(f"  [SKIP] {team['name']} — already has logo")
                    found += 1
                    continue

                print(f"  [FETCH] {team['name']}...", end=" ", flush=True)
                url = _find_logo_on_wikipedia(team)
                if url:
                    team["logo_url"] = url
                    found += 1
                    print(f"OK → {url[:80]}...")
                else:
                    failed.append(team["name"])
                    print("FAILED")

                time.sleep(1)  # Rate limit Wikipedia requests

    print(f"\n{'='*60}")
    print(f"Results: {found}/{total} teams have logos")
    if failed:
        print(f"\nFailed to find logos for {len(failed)} teams:")
        for name in failed:
            print(f"  - {name}")

    if not args.dry_run:
        with open(TEAMS_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nWritten to {TEAMS_JSON}")
    else:
        print("\n[DRY RUN] No changes written.")


if __name__ == "__main__":
    main()
