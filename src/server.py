import os
from pathlib import Path

from flask import Flask, jsonify, render_template

from .config import ARTICLES_PER_SECTION, CATEGORY_LABELS, SERVER_HOST, SERVER_PORT
from .database import get_articles_by_category, get_article_by_id, update_article_content, init_db
from .scraper import fetch_full_article

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

app = Flask(__name__, template_folder=str(TEMPLATES_DIR))


@app.route("/")
def index():
    sections = {}
    for category, label in CATEGORY_LABELS.items():
        articles = get_articles_by_category(category, ARTICLES_PER_SECTION)
        sections[category] = {"label": label, "articles": articles}
    return render_template("index.html", sections=sections)


@app.route("/api/articles/<category>")
def api_articles(category: str):
    if category not in CATEGORY_LABELS:
        return jsonify({"error": "unknown category"}), 404
    articles = get_articles_by_category(category, ARTICLES_PER_SECTION)
    return jsonify(articles)


@app.route("/api/articles")
def api_all_articles():
    result = {}
    for category in CATEGORY_LABELS:
        result[category] = get_articles_by_category(category, ARTICLES_PER_SECTION)
    return jsonify(result)


import re

@app.route("/article/<int:article_id>")
def article_view(article_id: int):
    article = get_article_by_id(article_id)
    if not article:
        return "Article not found", 404
    
    # Fetch content if not already stored
    if not article.get("content"):
        content = fetch_full_article(article["url"])
        if content:
            update_article_content(article_id, content)
            article["content"] = content
    
    # Convert content to HTML paragraphs
    if article.get("content"):
        paragraphs = [p.strip() for p in article["content"].split('\n\n') if p.strip()]
        article["content_html"] = ''.join(f'<p>{p}</p>' for p in paragraphs)
    else:
        article["content_html"] = ""
    
    return render_template("article.html", article=article)


def run(host: str = SERVER_HOST, port: int = SERVER_PORT, debug: bool = False) -> None:
    init_db()
    app.run(host=host, port=port, debug=debug)
