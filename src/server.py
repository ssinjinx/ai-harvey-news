import os
from pathlib import Path

from flask import Flask, jsonify, render_template, send_file

from .config import ARTICLES_PER_SECTION, CATEGORY_LABELS, SERVER_HOST, SERVER_PORT
from .database import get_articles_by_category, get_article_by_id, update_article_content, init_db, get_all_categories
from .scraper import fetch_full_article

# TTS imports - optional (only needed for audio generation)
try:
    from .tts import generate_speech_for_article, get_audio_for_article, is_available as tts_is_available
except ImportError:
    # Server without GPU/TTS - still serve cached audio files
    from .config import AUDIO_CACHE_DIR
    from pathlib import Path

    def generate_speech_for_article(article_id, text, category=None):
        return None

    def get_audio_for_article(article_id, category=None):
        # Check for cached audio files with category prefix first, then fallback
        if category:
            cache_path = AUDIO_CACHE_DIR / f"{category}newsarticle_{article_id}.wav"
            if cache_path.exists():
                return cache_path
        # Fallback to old naming
        cache_path = AUDIO_CACHE_DIR / f"article_{article_id}.wav"
        if cache_path.exists():
            return cache_path
        # Fallback: check static/audio/ (pushed via GitHub)
        static_audio = Path(__file__).parent.parent / "static" / "audio"
        if category:
            static_path = static_audio / f"{category}newsarticle_{article_id}.wav"
            if static_path.exists():
                return static_path
        static_path = static_audio / f"article_{article_id}.wav"
        if static_path.exists():
            return static_path
        return None

    def tts_is_available():
        return False

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
STATIC_DIR = Path(__file__).parent.parent / "static"

app = Flask(__name__, template_folder=str(TEMPLATES_DIR), static_folder=str(STATIC_DIR), static_url_path="/static")


@app.route("/")
def index():
    return render_template("desktop/index.html", sections={})


@app.route("/home/")
def home():
    """Desktop home - all categories in a single page."""
    sections = {}
    for category, label in CATEGORY_LABELS.items():
        articles = get_articles_by_category(category, ARTICLES_PER_SECTION)
        sections[category] = {"label": label, "articles": articles}
    return render_template("desktop/index.html", sections=sections)


@app.route("/mobile/")
def mobile_home():
    """Mobile home - single column news feed with bottom nav."""
    sections = {}
    for category, label in CATEGORY_LABELS.items():
        articles = get_articles_by_category(category, ARTICLES_PER_SECTION)
        sections[category] = {"label": label, "articles": articles}
    return render_template("mobile/index.html", sections=sections)


@app.route("/category/<category_key>/")
def category_page(category_key: str):
    """Category-specific mobile page."""
    if category_key not in CATEGORY_LABELS:
        return "Category not found", 404
    label = CATEGORY_LABELS[category_key]
    articles = get_articles_by_category(category_key, ARTICLES_PER_SECTION * 2)
    return render_template(
        f"mobile/{category_key}.html",
        category=category_key,
        label=label,
        articles=articles
    )


@app.route("/desktop/category/<category_key>/")
def desktop_category_page(category_key: str):
    """Category-specific desktop page."""
    if category_key not in CATEGORY_LABELS:
        return "Category not found", 404
    label = CATEGORY_LABELS[category_key]
    articles = get_articles_by_category(category_key, ARTICLES_PER_SECTION * 2)
    return render_template(
        f"desktop/{category_key}.html",
        category=category_key,
        label=label,
        articles=articles
    )


@app.route("/brain/")
def brain_page():
    """The Brain - Harvey AI explanation page."""
    return render_template("desktop/brain.html")


@app.route("/mobile/brain/")
def mobile_brain_page():
    """The Brain - Mobile version."""
    return render_template("mobile/brain.html")


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


@app.route("/article/<int:article_id>/audio")
def article_audio(article_id: int):
    """Generate and serve audio for an article."""
    # Get article to find its category
    article = get_article_by_id(article_id)
    if not article:
        return jsonify({"error": "Article not found"}), 404

    category = article.get("category")

    # Check if audio already cached
    cached = get_audio_for_article(article_id, category)
    if cached:
        return send_file(cached, mimetype="audio/wav")

    # Check if TTS is available
    if not tts_is_available():
        return jsonify({"error": "TTS not available"}), 503

    # Fetch content if not already stored
    content = article.get("content")
    if not content:
        content = fetch_full_article(article["url"])
        if content:
            update_article_content(article_id, content)

    if not content:
        return jsonify({"error": "No content available for TTS"}), 404

    # Prepare text for TTS (use title + content)
    text = f"{article['title']}. {content}"
    # Limit text length to avoid excessive generation time
    max_chars = 3000
    if len(text) > max_chars:
        text = text[:max_chars] + "..."

    # Generate audio
    audio_path = generate_speech_for_article(article_id, text)
    if audio_path:
        return send_file(audio_path, mimetype="audio/wav")
    else:
        return jsonify({"error": "Failed to generate audio"}), 500


@app.route("/article/<int:article_id>/audio/status")
def article_audio_status(article_id: int):
    """Check if audio is available for an article."""
    article = get_article_by_id(article_id)
    category = article.get("category") if article else None
    cached = get_audio_for_article(article_id, category)
    return jsonify({
        "available": cached is not None,
        "tts_available": tts_is_available(),
    })


def run(host: str = SERVER_HOST, port: int = SERVER_PORT, debug: bool = False) -> None:
    init_db()
    app.run(host=host, port=port, debug=debug)