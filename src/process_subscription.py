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
    # Normalize stored emails to lowercase so lookups are case-insensitive
    existing = {s["email"].strip().lower(): s for s in data["subscribers"]}
    changed = False

    # Sort oldest-first so the most recent action per email wins.
    # Tiebreak: subscribes before unsubscribes so unsubscribes always win ties.
    def _sort_key(s):
        date = s.get("_date") or s.get("created_at") or ""
        action_order = 1 if s.get("action", "subscribe") == "unsubscribe" else 0
        return (date, action_order)

    submissions = sorted(submissions, key=_sort_key)

    for sub in submissions:
        email = sub.get("email", "").strip().lower()
        if not email:
            continue

        action = sub.get("action", "subscribe")
        print(f"  Processing {action} for {email}")

        if action == "unsubscribe":
            if email in existing:
                existing[email]["active"] = False
            else:
                # Guard against future re-subscription via stale Formspree submissions
                existing[email] = {"email": email, "teams": [], "active": False}
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


def write_subscribers_index(data: dict | None = None) -> None:
    """Write docs/subscribers_index.json mapping sha256(email) -> [team_ids].

    This lets the manage page look up a subscriber's current teams client-side
    without exposing raw email addresses.
    """
    import hashlib

    if data is None:
        data = load_subscribers()

    docs_dir = Path(__file__).parent.parent / "docs"
    index = {}
    for sub in data["subscribers"]:
        if not sub.get("active", True):
            continue
        email = sub.get("email", "").strip().lower()
        if not email:
            continue
        h = hashlib.sha256(email.encode()).hexdigest()
        index[h] = sub.get("teams", [])

    out_path = docs_dir / "subscribers_index.json"
    out_path.write_text(json.dumps(index), encoding="utf-8")
    print(f"subscribers_index.json written ({len(index)} active subscribers)")


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
    write_subscribers_index()


if __name__ == "__main__":
    main()
