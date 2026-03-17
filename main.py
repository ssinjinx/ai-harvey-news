#!/usr/bin/env python3
"""
News Scraper entry point.

Usage:
  python main.py                    # scrape then serve
  python main.py scrape             # fetch articles and store in DB
  python main.py scrape --llm       # scrape with LLM summarization via Ollama
  python main.py summarize          # re-summarize existing articles via Ollama
  python main.py serve              # start the web server
"""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("news_scraper")


def scrape(use_llm: bool = False) -> None:
    from src.config import ARTICLES_PER_SECTION, CATEGORY_LABELS
    from src.database import init_db, save_articles
    from src.scraper import scrape_all

    logger.info("Initialising database...")
    init_db()

    if use_llm:
        from src.llm import is_available
        if not is_available():
            logger.warning("Ollama not reachable at localhost:11434 — scraping without LLM")
            use_llm = False
        else:
            logger.info("Ollama available — will summarize articles via LLM")

    logger.info("Scraping feeds...")
    results = scrape_all(ARTICLES_PER_SECTION, use_llm=use_llm)

    total = 0
    for category, articles in results.items():
        inserted = save_articles(articles)
        label = CATEGORY_LABELS.get(category, category)
        logger.info("  %-20s fetched=%-3d  saved=%d", label, len(articles), inserted)
        total += inserted

    logger.info("Done. %d new articles stored.", total)


def summarize() -> None:
    """Re-summarize all stored articles using Ollama."""
    from src.database import get_all_articles, update_article_summary
    from src.llm import is_available, summarize_article

    if not is_available():
        logger.error("Ollama not reachable at localhost:11434 — cannot summarize")
        sys.exit(1)

    articles = get_all_articles()
    logger.info("Re-summarizing %d articles...", len(articles))
    updated = 0
    for article in articles:
        new_summary = summarize_article(article["title"], article["summary"])
        if new_summary:
            update_article_summary(article["id"], new_summary)
            updated += 1
            logger.info("  [%d] %s", article["id"], article["title"][:60])

    logger.info("Done. %d articles re-summarized.", updated)


def serve(debug: bool = False) -> None:
    from src.server import run
    logger.info("Starting web server at http://localhost:5000")
    run(debug=debug)


def main() -> None:
    args = sys.argv[1:]
    cmd = args[0] if args else "all"
    flags = set(args[1:])

    if cmd == "scrape":
        scrape(use_llm="--llm" in flags)
    elif cmd == "summarize":
        summarize()
    elif cmd == "serve":
        serve()
    elif cmd in ("all", ""):
        scrape()
        serve()
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
