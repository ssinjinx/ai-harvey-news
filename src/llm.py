import logging

import requests

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "kimi-k2.5:cloud"


def summarize_article(title: str, content: str) -> str | None:
    """Summarize an article via Ollama. Returns None on failure (caller should fallback)."""
    if not content:
        return None

    prompt = (
        f"Summarize the following news article in 2-3 concise sentences. "
        f"Return only the summary, no preamble.\n\n"
        f"Title: {title}\n\n{content}"
    )

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=60,
        )
        resp.raise_for_status()
        summary = resp.json().get("response", "").strip()
        return summary or None
    except Exception as exc:
        logger.warning("Ollama summarization failed: %s", exc)
        return None


def is_available() -> bool:
    """Check if Ollama is reachable."""
    try:
        requests.get("http://localhost:11434", timeout=3)
        return True
    except Exception:
        return False
