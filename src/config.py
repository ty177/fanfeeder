"""Configuration for the sports news digest."""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
TEAMS_JSON_PATH = PROJECT_ROOT / "docs" / "teams.json"
SUBSCRIBERS_JSON_PATH = PROJECT_ROOT / "data" / "subscribers.json"

# Email settings
RESEND_FROM = "FanFeeder <donotreply@fanfeeder.fire-exit.com>"

# Content limits
MAX_HEADLINES_PER_TEAM = 5
MAX_VIDEOS_PER_TEAM = 3

# Custom domain URL (for unsubscribe links)
SITE_URL = "https://fanfeeder.fire-exit.com"
