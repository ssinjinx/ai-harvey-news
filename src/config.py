import os

DB_PATH = os.environ.get("NEWS_DB_PATH", "news.db")
ARTICLES_PER_SECTION = 5
SERVER_HOST = "0.0.0.0"
SERVER_PORT = int(os.environ.get("PORT", 9090))

FEEDS = {
    "global": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    ],
    "tech": [
        "https://techcrunch.com/feed/",
        "https://feeds.arstechnica.com/arstechnica/index",
    ],
    "sports": [
        "https://feeds.bbci.co.uk/sport/rss.xml",
        "https://www.espn.com/espn/rss/news",
    ],
    "entertainment": [
        "https://variety.com/feed/",
        "https://deadline.com/feed/",
    ],
    "ai": [
        "https://venturebeat.com/ai/feed/",
        "https://www.artificialintelligence-news.com/feed/",
    ],
}

CATEGORY_LABELS = {
    "global": "Global News",
    "tech": "Tech News",
    "sports": "Sports News",
    "entertainment": "Entertainment News",
    "ai": "AI News",
}
