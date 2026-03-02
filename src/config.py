"""Configuration for the sports news digest."""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
TEAMS_JSON_PATH = PROJECT_ROOT / "docs" / "teams.json"
SUBSCRIBERS_JSON_PATH = PROJECT_ROOT / "data" / "subscribers.json"

# Email settings
EMAIL_SENDER = "tyahma@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Content limits
MAX_HEADLINES_PER_TEAM = 5
MAX_VIDEOS_PER_TEAM = 3

# GitHub Pages URL (for unsubscribe links)
SITE_URL = "https://ty177.github.io/fanfeeder"
