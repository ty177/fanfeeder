"""Sync Formspree submissions into data/subscribers.json."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data"
SUBSCRIBERS_FILE = DATA_DIR / "subscribers.json"


def load_subscribers() -> dict:
    if SUBSCRIBERS_FILE.exists():
        with open(SUBSCRIBERS_FILE) as f:
            return json.load(f)
    return {"subscribers": []}


def save_subscribers(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def process_submissions(submissions: list[dict]) -> bool:
    """Process Formspree submissions, return True if subscribers changed."""
    data = load_subscribers()
    existing = {s["email"]: s for s in data["subscribers"]}
    changed = False

    # Sort oldest-first so the most recent action per email wins
    submissions = sorted(submissions, key=lambda s: s.get("created_at") or s.get("_date") or "")

    for sub in submissions:
        email = sub.get("email", "").strip().lower()
        if not email:
            continue

        action = sub.get("action", "subscribe")

        if action == "unsubscribe":
            if email in existing:
                existing[email]["active"] = False
                changed = True
            continue

        teams_str = sub.get("teams", "")
        teams = [t.strip() for t in teams_str.split(",") if t.strip()]
        if not teams:
            continue

        now = datetime.now(timezone.utc).isoformat()

        if email in existing:
            existing[email]["teams"] = teams
            existing[email]["active"] = True
            changed = True
        else:
            existing[email] = {
                "email": email,
                "teams": teams,
                "subscribed_at": now,
                "active": True,
            }
            changed = True

    if changed:
        data["subscribers"] = list(existing.values())
        save_subscribers(data)

    return changed


def fetch_formspree_submissions() -> list[dict]:
    """Fetch recent submissions from Formspree API."""
    import requests

    api_key = os.environ.get("FORMSPREE_API_KEY", "")
    form_id = os.environ.get("FORMSPREE_FORM_ID", "")

    if not api_key or not form_id:
        print("FORMSPREE_API_KEY and FORMSPREE_FORM_ID required")
        sys.exit(1)

    url = f"https://formspree.io/api/0/forms/{form_id}/submissions"
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    return resp.json().get("submissions", [])


def main() -> None:
    submissions = fetch_formspree_submissions()
    print(f"Fetched {len(submissions)} submissions")
    changed = process_submissions(submissions)
    if changed:
        print("Subscribers updated")
    else:
        print("No changes")


if __name__ == "__main__":
    main()
