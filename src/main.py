"""Sports News Digest - main orchestrator.

Usage:
    python main.py              # Fetch news and send email
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

from config import EMAIL_RECIPIENT, EMAIL_SENDER, SMTP_PORT, SMTP_SERVER, TEAMS
from email_builder import build_email
from news_fetcher import fetch_news
from seen_cache import filter_new_items
from youtube_fetcher import fetch_videos

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def gather_team_data() -> list[dict]:
    """Fetch news and videos for all configured teams."""
    team_data = []
    for team in TEAMS:
        logger.info(f"--- Processing {team['name']} ---")
        headlines = fetch_news(team["news_query"])
        videos = fetch_videos(
            team["youtube_query"],
            channel_feed_urls=team.get("youtube_channels"),
        )
        team_data.append({
            "team": team,
            "headlines": headlines,
            "videos": videos,
        })
    return team_data


def send_email(html_content: str) -> None:
    """Send the digest email via Gmail SMTP."""
    app_password = os.environ.get("GMAIL_APP_PASSWORD")
    if not app_password:
        logger.error("GMAIL_APP_PASSWORD environment variable not set")
        sys.exit(1)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Sports Digest"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECIPIENT
    msg.attach(MIMEText(html_content, "html"))

    logger.info(f"Sending email to {EMAIL_RECIPIENT} via {SMTP_SERVER}:{SMTP_PORT}")
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(EMAIL_SENDER, app_password)
        server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())

    logger.info("Email sent successfully!")


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Sports News Digest")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Write HTML to preview.html instead of sending email",
    )
    args = parser.parse_args()

    logger.info("Starting Sports News Digest")
    team_data = gather_team_data()
    team_data = filter_new_items(team_data)
    html_content = build_email(team_data)

    if args.preview:
        preview_path = Path(__file__).parent.parent / "preview.html"
        preview_path.write_text(html_content, encoding="utf-8")
        logger.info(f"Preview written to {preview_path}")
        print(f"\nPreview saved to: {preview_path}")
        print("Open it in a browser to see the digest.")
    else:
        send_email(html_content)

    logger.info("Done!")


if __name__ == "__main__":
    main()
