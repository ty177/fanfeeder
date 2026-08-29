"""Sports News Digest - main orchestrator.

Usage:
    python main.py              # Fetch news and send emails to all subscribers
    python main.py --preview    # Write HTML to preview.html instead of sending
"""

from __future__ import annotations

import argparse
import logging
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

from config import EMAIL_SENDER, SMTP_PORT, SMTP_SERVER
from email_builder import build_email
from logo_checker import verify_logos
from news_fetcher import fetch_news
from seen_cache import filter_new_items
from subscriber_loader import get_unique_teams, load_subscribers, load_team_catalog
from youtube_fetcher import fetch_videos

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def fetch_team_content(teams: list[dict]) -> dict:
    """Fetch news and videos for each team. Returns dict keyed by team ID."""
    content = {}
    for team in teams:
        team_id = team["id"]
        logger.info(f"--- Fetching content for {team['name']} ---")
        headlines = fetch_news(team["news_query"])
        video_channels = team.get("youtube_channels")
        vids = fetch_videos(
            team["youtube_query"],
            channel_feed_urls=video_channels if video_channels else None,
        )
        content[team_id] = {
            "team": team,
            "headlines": headlines,
            "videos": vids,
        }
    return content


def send_email(html_content: str, recipient: str) -> None:
    """Send the digest email via Gmail SMTP."""
    app_password = os.environ.get("GMAIL_APP_PASSWORD")
    if not app_password:
        logger.error("GMAIL_APP_PASSWORD environment variable not set")
        sys.exit(1)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "FanFeeder Sports Digest"
    msg["From"] = EMAIL_SENDER
    msg["To"] = recipient
    msg.attach(MIMEText(html_content, "html"))

    logger.info(f"Sending email to {recipient} via {SMTP_SERVER}:{SMTP_PORT}")
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(EMAIL_SENDER, app_password)
        server.sendmail(EMAIL_SENDER, recipient, msg.as_string())

    logger.info(f"Email sent to {recipient}")


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="FanFeeder Sports Digest")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Write HTML to preview.html instead of sending email",
    )
    parser.add_argument(
        "--email",
        help="Only send to this subscriber email (for testing)",
    )
    args = parser.parse_args()

    logger.info("Starting FanFeeder Sports Digest")

    # 1. Load team catalog and subscribers
    team_catalog = load_team_catalog()
    subscribers = load_subscribers()

    if not subscribers:
        logger.warning("No active subscribers found, exiting")
        return

    # Filter to a single subscriber if --email is set
    if args.email:
        filter_email = args.email.strip().lower()
        subscribers = [s for s in subscribers if s["email"].strip().lower() == filter_email]
        if not subscribers:
            logger.warning(f"No active subscriber found for {filter_email}, exiting")
            return
        logger.info(f"Filtered to single subscriber: {filter_email}")

    # 2. Find all unique teams needed across all subscribers
    unique_teams = get_unique_teams(subscribers, team_catalog)
    if not unique_teams:
        logger.warning("No valid teams found for any subscriber, exiting")
        return

    # 3. Verify logos for all needed teams
    verify_logos(unique_teams)

    # 4. Fetch content ONCE per unique team
    team_content = fetch_team_content(unique_teams)

    # 5. Build and send per-subscriber emails
    for subscriber in subscribers:
        email = subscriber["email"]
        logger.info(f"=== Processing subscriber: {email} ===")

        # Assemble this subscriber's team data
        sub_team_data = []
        for tid in subscriber.get("teams", []):
            if tid in team_content:
                # Deep copy so dedup doesn't mutate shared content
                tc = team_content[tid]
                sub_team_data.append({
                    "team": tc["team"],
                    "headlines": list(tc["headlines"]),
                    "videos": list(tc["videos"]),
                })
            else:
                logger.warning(f"Team '{tid}' not in fetched content for {email}")

        if not sub_team_data:
            logger.warning(f"No team data for {email}, skipping")
            continue

        # Per-subscriber deduplication
        sub_team_data = filter_new_items(sub_team_data, subscriber_key=email)

        # Build the email
        html_content = build_email(sub_team_data, subscriber_email=email)

        if args.preview:
            preview_path = Path(__file__).parent.parent / "preview.html"
            preview_path.write_text(html_content, encoding="utf-8")
            logger.info(f"Preview written for {email}")
            print(f"\nPreview saved to: {preview_path}")
            print("Open it in a browser to see the digest.")
            break  # Only preview first subscriber
        else:
            send_email(html_content, recipient=email)

    logger.info("Done!")


if __name__ == "__main__":
    main()
