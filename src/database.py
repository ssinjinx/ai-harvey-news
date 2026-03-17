import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .config import DB_PATH


@dataclass
class Article:
    title: str
    source: str
    url: str
    summary: str
    category: str
    published_at: Optional[str]
    id: Optional[int] = None
    scraped_at: Optional[str] = None
    content: Optional[str] = None


@contextmanager
def get_conn(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str = DB_PATH) -> None:
    with get_conn(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                source      TEXT NOT NULL,
                url         TEXT NOT NULL UNIQUE,
                summary     TEXT,
                content     TEXT,
                category    TEXT NOT NULL,
                published_at TEXT,
                scraped_at  TEXT NOT NULL
            )
        """)


def save_articles(articles: list[Article], db_path: str = DB_PATH) -> int:
    """Insert articles, skipping duplicates by URL. Returns count inserted."""
    now = datetime.utcnow().isoformat()
    inserted = 0
    with get_conn(db_path) as conn:
        for a in articles:
            try:
                conn.execute(
                    """
                    INSERT INTO articles (title, source, url, summary, category, published_at, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (a.title, a.source, a.url, a.summary, a.category, a.published_at, now),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                pass  # duplicate URL
    return inserted


def get_articles_by_category(category: str, limit: int, db_path: str = DB_PATH) -> list[dict]:
    with get_conn(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM articles
            WHERE category = ?
            ORDER BY scraped_at DESC, published_at DESC
            LIMIT ?
            """,
            (category, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_articles(db_path: str = DB_PATH) -> list[dict]:
    with get_conn(db_path) as conn:
        rows = conn.execute("SELECT id, title, summary FROM articles ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def update_article_summary(article_id: int, summary: str, db_path: str = DB_PATH) -> None:
    with get_conn(db_path) as conn:
        conn.execute("UPDATE articles SET summary = ? WHERE id = ?", (summary, article_id))


def get_all_categories(db_path: str = DB_PATH) -> list[str]:
    with get_conn(db_path) as conn:
        rows = conn.execute("SELECT DISTINCT category FROM articles").fetchall()
    return [r["category"] for r in rows]


def get_article_by_id(article_id: int, db_path: str = DB_PATH) -> dict | None:
    """Fetch a single article by ID with full content."""
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM articles WHERE id = ?",
            (article_id,)
        ).fetchone()
    return dict(row) if row else None


def update_article_content(article_id: int, content: str, db_path: str = DB_PATH) -> None:
    """Update the full content of an article."""
    with get_conn(db_path) as conn:
        conn.execute("UPDATE articles SET content = ? WHERE id = ?", (content, article_id))


def get_articles_without_content(limit: int = 100, db_path: str = DB_PATH) -> list[dict]:
    """Get articles that don't have full content yet."""
    with get_conn(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, title, url FROM articles
            WHERE content IS NULL OR content = ''
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_articles_with_content(limit: int = 1000, db_path: str = DB_PATH) -> list[dict]:
    """Get articles that have full content."""
    with get_conn(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, title, content FROM articles
            WHERE content IS NOT NULL AND content != ''
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
    return [dict(r) for r in rows]
