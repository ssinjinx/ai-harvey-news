"""Text-to-Speech module — Paul Harvey voice clone via Qwen3-TTS."""
import json
import logging
import re
import urllib.request
from pathlib import Path
from typing import Optional

import soundfile as sf
import torch

from .config import AUDIO_CACHE_DIR, HARVEY_CLONE_AUDIO, OLLAMA_MODEL, OLLAMA_URL

logger = logging.getLogger("tts")

# Paul Harvey LLM prompt
HARVEY_SYSTEM_PROMPT = """\
You are Paul Harvey, the legendary American radio broadcaster known for your
distinctive storytelling style on "The Rest of the Story" and "News and Comment."

Rewrite the provided article in your voice and style. Rules:

STRUCTURE:
- Open with a dramatic hook that pulls the listener in immediately
- Build suspense by withholding the key reveal until near the end
- Use "Page 2..." as a transition into the second half
- End with your signature: "And now you know... the rest of the story."
- Sign off with: "Good day!"

PACING AND PAUSES:
- Insert [pause] where you would take a dramatic breath or let a point land
- Use ellipses (...) for trailing, contemplative thoughts
- Short sentences for impact. Very short.
- Then a longer sentence to build and carry the listener along with you.

VOICE:
- Warm, personal, conversational — as if speaking to one friend, not a crowd
- Occasional wry humor; never sarcastic
- Patriotic undertone when relevant, never preachy
- Names and places spoken with familiarity, as if you know them personally
- Avoid jargon; prefer plain, vivid language

FORBIDDEN:
- Do not summarize — dramatize
- Do not use bullet points or lists
- Do not break character or mention AI
- Keep the factual content accurate; only style changes
- Output ONLY the spoken script, no stage directions or labels
"""

DEFAULT_MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"

# Global model instance (lazy loaded)
_model = None


def get_cache_path(article_id: int, category: str = None) -> Path:
    if category:
        # Format: worldnewsarticle_10.wav, ainewsarticle_10.wav, etc.
        return AUDIO_CACHE_DIR / f"{category}newsarticle_{article_id}.wav"
    return AUDIO_CACHE_DIR / f"article_{article_id}.wav"


def get_script_cache_path(article_id: int, category: str = None) -> Path:
    if category:
        return AUDIO_CACHE_DIR / f"{category}newsarticle_{article_id}_script.txt"
    return AUDIO_CACHE_DIR / f"article_{article_id}_script.txt"


def is_available() -> bool:
    try:
        from qwen_tts import Qwen3TTSModel
        return True
    except ImportError:
        return False


def get_model():
    global _model
    if _model is None:
        from qwen_tts import Qwen3TTSModel
        logger.info("Loading %s for Harvey voice clone...", DEFAULT_MODEL)
        device_map = "cuda:0" if torch.cuda.is_available() else "cpu"
        _model = Qwen3TTSModel.from_pretrained(DEFAULT_MODEL, device_map=device_map)
        logger.info("TTS model loaded (device=%s)", device_map)
    return _model


def rewrite_as_harvey(text: str) -> str:
    """Rewrite article text in Paul Harvey's style via Ollama."""
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": HARVEY_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["message"]["content"]


def strip_pause_markers(script: str) -> str:
    return re.sub(r"\[pause\]", ", ", script)


def generate_speech_for_article(article_id: int, text: str, force: bool = False, category: str = None) -> Optional[Path]:
    """
    Full Harvey pipeline for one article:
      1. LLM rewrite as Paul Harvey
      2. Voice clone TTS with harveyclip.wav
      3. Cache the .wav and script to extraspace
    """
    cache_path = get_cache_path(article_id, category)
    script_path = get_script_cache_path(article_id, category)

    if cache_path.exists() and not force:
        logger.info("Using cached audio for article %d (%s)", article_id, category)
        return cache_path

    try:
        # Step 1: LLM rewrite
        logger.info("[%d] Rewriting as Paul Harvey via Ollama (%s)...", article_id, OLLAMA_MODEL)
        script = rewrite_as_harvey(text)
        script_path.write_text(script, encoding="utf-8")

        # Step 2: Strip pause markers
        tts_text = strip_pause_markers(script)

        # Step 3: Voice clone TTS
        logger.info("[%d] Generating Harvey voice clone (%d chars)...", article_id, len(tts_text))
        model = get_model()
        audios, sr = model.generate_voice_clone(
            text=tts_text,
            ref_audio=HARVEY_CLONE_AUDIO,
            x_vector_only_mode=True,
            language="english",
        )

        sf.write(str(cache_path), audios[0], sr)
        logger.info("[%d] Audio saved to %s", article_id, cache_path)
        return cache_path

    except Exception as e:
        logger.error("[%d] Failed to generate audio: %s", article_id, e)
        return None


def get_audio_for_article(article_id: int, category: str = None) -> Optional[Path]:
    # Try category-specific cache path first
    cache_path = get_cache_path(article_id, category)
    if cache_path.exists():
        return cache_path
    # Fallback for backwards compatibility (generic article_X.wav)
    cache_path = get_cache_path(article_id)
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


def delete_audio_cache(article_id: Optional[int] = None) -> int:
    deleted = 0
    if article_id is not None:
        for path in [get_cache_path(article_id), get_script_cache_path(article_id)]:
            if path.exists():
                path.unlink()
                deleted += 1
    else:
        if AUDIO_CACHE_DIR.exists():
            for f in AUDIO_CACHE_DIR.glob("article_*"):
                f.unlink()
                deleted += 1
    return deleted
