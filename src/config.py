import os
from pathlib import Path

# External storage root — keeps DB and audio off the local drive
DATA_DIR = Path(os.environ.get(
    "HARVEY_DATA_DIR",
    "/media/ssinjin/dd94215e-9604-48fe-ab07-6f002b2281b0/harvey-news/data",
))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = str(DATA_DIR / "news.db")
AUDIO_CACHE_DIR = DATA_DIR / "audio_cache"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Paul Harvey voice cloning
HARVEY_CLONE_AUDIO = os.environ.get("HARVEY_CLONE_AUDIO", "/home/ssinjin/Music/harveyclip.wav")

# Ollama settings for Paul Harvey LLM rewrite
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "minimax-m2.5:cloud")

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
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    ],
}

CATEGORY_LABELS = {
    "global": "Global News",
    "tech": "Tech News",
    "sports": "Sports News",
    "entertainment": "Entertainment News",
    "ai": "AI News",
}
