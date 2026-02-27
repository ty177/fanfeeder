"""Team configuration for the sports news digest."""

TEAMS = [
    {
        "name": "Manchester City FC",
        "short_name": "Man City",
        "sport": "football",
        "primary_color": "#6CABDD",
        "secondary_color": "#FFFFFF",
        "text_color": "#FFFFFF",
        "logo_url": "https://upload.wikimedia.org/wikipedia/en/thumb/e/eb/Manchester_City_FC_badge.svg/250px-Manchester_City_FC_badge.svg.png",
        "news_query": "Manchester City FC",
        "youtube_query": "Manchester City FC highlights",
        "youtube_channels": [
            "https://www.youtube.com/feeds/videos.xml?channel_id=UCkzCjdRMrW2vXLx8mvPVLdQ",  # Man City official
        ],
    },
    {
        "name": "FC Barcelona",
        "short_name": "Barcelona",
        "sport": "football",
        "primary_color": "#004D98",
        "secondary_color": "#A50044",
        "text_color": "#FFFFFF",
        "logo_url": "https://upload.wikimedia.org/wikipedia/en/thumb/4/47/FC_Barcelona_%28crest%29.svg/250px-FC_Barcelona_%28crest%29.svg.png",
        "news_query": "FC Barcelona men",
        "youtube_query": "FC Barcelona highlights",
        "youtube_channels": [
            "https://www.youtube.com/feeds/videos.xml?channel_id=UC14UlmYlSNiQCBe9Eookf_A",  # FC Barcelona official
        ],
    },
    {
        "name": "Golden State Warriors",
        "short_name": "Warriors",
        "sport": "basketball",
        "primary_color": "#1D428A",
        "secondary_color": "#FFC72C",
        "text_color": "#FFC72C",
        "logo_url": "https://upload.wikimedia.org/wikipedia/en/thumb/0/01/Golden_State_Warriors_logo.svg/250px-Golden_State_Warriors_logo.svg.png",
        "news_query": "Golden State Warriors",
        "youtube_query": "Golden State Warriors highlights",
        "youtube_channels": [
            "https://www.youtube.com/feeds/videos.xml?channel_id=UCeYc_OjHs3QNxIjti2whKzg",  # Warriors official
        ],
    },
    {
        "name": "San Francisco 49ers",
        "short_name": "49ers",
        "sport": "football",
        "primary_color": "#AA0000",
        "secondary_color": "#B3995D",
        "text_color": "#B3995D",
        "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/San_Francisco_49ers_logo.svg/120px-San_Francisco_49ers_logo.svg.png",
        "news_query": "San Francisco 49ers",
        "youtube_query": "San Francisco 49ers highlights",
        "youtube_channels": [
            "https://www.youtube.com/feeds/videos.xml?channel_id=UCeIOarQkwmGhimim9cDUTng",  # 49ers official
        ],
    },
]

# Email settings
EMAIL_RECIPIENT = "tyahma@gmail.com"
EMAIL_SENDER = "tyahma@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Content limits
MAX_HEADLINES_PER_TEAM = 5
MAX_VIDEOS_PER_TEAM = 3
