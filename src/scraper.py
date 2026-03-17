import logging
import re
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

from .config import ARTICLES_PER_SECTION, FEEDS
from .database import Article

logger = logging.getLogger(__name__)


def _source_from_url(url: str) -> str:
    host = urlparse(url).netloc
    return host.removeprefix("www.").split(".")[0].capitalize()


def _parse_date(entry) -> str | None:
    for field in ("published", "updated"):
        raw = getattr(entry, field, None)
        if raw:
            try:
                return parsedate_to_datetime(raw).isoformat()
            except Exception:
                return raw
    return None


def _clean_text(text: str | None, max_len: int | None = None) -> str:
    if not text:
        return ""
    import re
    cleaned = re.sub(r"<[^>]+>", "", text).strip()
    return cleaned[:max_len] if max_len else cleaned


def _get_content(entry) -> str:
    """Return the richest available text from a feed entry."""
    # Some feeds provide full article content
    content_list = entry.get("content")
    if content_list:
        return _clean_text(content_list[0].get("value", ""))
    # Fall back to summary/description
    return _clean_text(entry.get("summary") or entry.get("description"), max_len=500)


def fetch_feed(
    url: str, category: str, limit: int = ARTICLES_PER_SECTION, use_llm: bool = False
) -> list[Article]:
    """Fetch and parse a single RSS/Atom feed."""
    from .llm import summarize_article

    try:
        feed = feedparser.parse(url)
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return []

    if feed.bozo and not feed.entries:
        logger.warning("Malformed feed at %s: %s", url, feed.bozo_exception)
        return []

    source = feed.feed.get("title") or _source_from_url(url)
    articles = []

    for entry in feed.entries[:limit]:
        link = entry.get("link", "")
        title = entry.get("title", "").strip()
        if not link or not title:
            continue

        content = _get_content(entry)
        if use_llm:
            summary = summarize_article(title, content) or content[:500]
        else:
            summary = content[:500]

        articles.append(
            Article(
                title=title,
                source=source,
                url=link,
                summary=summary,
                category=category,
                published_at=_parse_date(entry),
            )
        )

    return articles


def scrape_category(category: str, limit: int = ARTICLES_PER_SECTION, use_llm: bool = False) -> list[Article]:
    """Scrape all feeds for a category, return up to `limit` unique articles."""
    seen_urls: set[str] = set()
    results: list[Article] = []

    for feed_url in FEEDS.get(category, []):
        for article in fetch_feed(feed_url, category, limit, use_llm=use_llm):
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                results.append(article)
            if len(results) >= limit:
                break
        if len(results) >= limit:
            break

    return results[:limit]


def scrape_all(limit: int = ARTICLES_PER_SECTION, use_llm: bool = False) -> dict[str, list[Article]]:
    """Scrape every configured category. Returns {category: [Article]}."""
    return {category: scrape_category(category, limit, use_llm=use_llm) for category in FEEDS}


def fetch_full_article(url: str) -> str | None:
    """Fetch and extract full article text from a news site."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove script, style, nav, headers, footers, asides
        for elem in soup(["script", "style", "nav", "header", "footer", "aside", ".share", ".social", ".comments"]):
            elem.decompose()
        
        # Try common article selectors
        selectors = [
            "article",
            "[itemprop='articleBody']",
            ".article-body",
            ".post-content",
            ".entry-content",
            ".story-body",
            "main",
            ".content",
            "#content",
        ]
        
        article_elem = None
        for selector in selectors:
            article_elem = soup.select_one(selector)
            if article_elem:
                break
        
        if not article_elem:
            # Fallback: get all paragraphs
            article_elem = soup
        
        # Extract paragraphs and clean them
        paragraphs = []
        for p in article_elem.find_all("p"):
            text = p.get_text(strip=True)
            # Skip short paragraphs that are likely UI elements
            if len(text) < 20:
                continue
            # Skip common UI text
            if text.lower() in ["share", "save", "copy link", "copied", "read more", "continue reading"]:
                continue
            # Skip author bios (often contain "@" or "correspondent")
            if re.search(r'\bcorrespondent\b|\breporter\b|\@\w+\b', text.lower()):
                continue
            paragraphs.append(text)
        
        if not paragraphs:
            return None
        
        # Join paragraphs with double newline for clean formatting
        text = "\n\n".join(paragraphs)
        
        # Clean up excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        return text if len(text) > 200 else None
        
    except Exception as exc:
        logger.warning("Failed to fetch article from %s: %s", url, exc)
        return None
