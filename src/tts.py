"""Text-to-Speech module — Paul Harvey voice clone via ComfyUI Qwen3-TTS."""
import json
import logging
import os
import re
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

from .config import AUDIO_CACHE_DIR, HARVEY_CLONE_AUDIO, OLLAMA_MODEL, OLLAMA_URL

logger = logging.getLogger("tts")

# ComfyUI settings
COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://localhost:8188")
COMFYUI_REF_AUDIO = os.environ.get("COMFYUI_REF_AUDIO", "harveyclip_5s.wav")
COMFYUI_REF_TEXT = os.environ.get(
    "COMFYUI_REF_TEXT",
    "Look at the grand canyon, it took millions of years to get right.\n\nand eveolution boy!",
)

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


def is_available() -> bool:
    """Check if ComfyUI is reachable."""
    try:
        req = urllib.request.Request(f"{COMFYUI_URL}/system_stats", method="GET")
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception:
        logger.warning("ComfyUI not reachable at %s", COMFYUI_URL)
        return False


def get_cache_path(article_id: int, category: str = None) -> Path:
    if category:
        return AUDIO_CACHE_DIR / f"{category}newsarticle_{article_id}.wav"
    return AUDIO_CACHE_DIR / f"article_{article_id}.wav"


def get_script_cache_path(article_id: int, category: str = None) -> Path:
    if category:
        return AUDIO_CACHE_DIR / f"{category}newsarticle_{article_id}_script.txt"
    return AUDIO_CACHE_DIR / f"article_{article_id}_script.txt"


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


def _copy_ref_audio_to_comfyui() -> str:
    """Ensure the reference audio is in ComfyUI's input directory. Returns filename."""
    comfy_input = Path(os.environ.get(
        "COMFYUI_DIR",
        "/media/ssinjin/c173cbdc-b600-4f53-8185-b87fbce0bc3b/ComfyUI",
    )) / "input"
    target = comfy_input / "harvey_ref_audio.wav"

    # If already there and up to date, skip
    src = Path(HARVEY_CLONE_AUDIO)
    if target.exists() and src.exists():
        if target.stat().st_size == src.stat().st_size:
            return "harvey_ref_audio.wav"

    # Copy the reference audio
    import shutil
    comfy_input.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(target))
    logger.info("Copied reference audio to %s", target)
    return "harvey_ref_audio.wav"


def generate_via_comfyui(text: str, output_filename: str = "harvey_output") -> Optional[Path]:
    """
    Generate Harvey voice clone audio via ComfyUI API.

    Sends the text to the Qwen3-TTS Voice Clone workflow and waits for the result.
    Returns the path to the generated MP3 file, or None on failure.
    """
    ref_audio_name = _copy_ref_audio_to_comfyui()

    # Build the workflow
    workflow = {
        "1": {
            "class_type": "easy positive",
            "inputs": {
                "positive": COMFYUI_REF_TEXT,
            },
        },
        "3": {
            "class_type": "easy positive",
            "inputs": {
                "positive": text,
            },
        },
        "5": {
            "class_type": "LoadAudio",
            "inputs": {
                "audio": ref_audio_name,
            },
        },
        "7": {
            "class_type": "FB_Qwen3TTSVoiceClone",
            "inputs": {
                "ref_audio": ["5", 0],
                "target_text": ["3", 0],
                "ref_text": ["1", 0],
                "model_choice": "1.7B",
                "device": "cuda",
                "precision": "bf16",
                "language": "English",
                "seed": 0,
                "max_new_tokens": 4096,
                "top_p": 0.8,
                "top_k": 25,
                "temperature": 1.0,
                "repetition_penalty": 1.05,
                "x_vector_only": False,
                "attention": "sage_attn",
                "unload_model_after_generate": False,
            },
        },
        "6": {
            "class_type": "SaveAudioMP3",
            "inputs": {
                "audio": ["7", 0],
                "filename_prefix": f"audio/{output_filename}",
                "quality": "V0",
            },
        },
    }

    prompt = {"prompt": workflow}

    # Submit to ComfyUI
    logger.info("Submitting TTS job to ComfyUI (%d chars)...", len(text))
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=json.dumps(prompt).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        logger.error("ComfyUI returned HTTP %d: %s", e.code, e.read().decode())
        return None
    except Exception as e:
        logger.error("Failed to submit to ComfyUI: %s", e)
        return None

    prompt_id = result.get("prompt_id")
    if not prompt_id:
        logger.error("No prompt_id in ComfyUI response: %s", result)
        return None

    logger.info("ComfyUI prompt_id: %s", prompt_id)

    # Poll for completion
    for attempt in range(600):  # 10 minutes max
        time.sleep(2)
        try:
            hist_req = urllib.request.Request(f"{COMFYUI_URL}/history/{prompt_id}")
            hist_resp = urllib.request.urlopen(hist_req, timeout=10)
            hist = json.loads(hist_resp.read())
        except Exception:
            continue

        if prompt_id in hist:
            status = hist[prompt_id].get("status", {})
            if status.get("completed", False) or status.get("status_str") == "success":
                # Find the output file
                outputs = hist[prompt_id].get("outputs", {})
                for node_id, node_out in outputs.items():
                    if "audio" in node_out:
                        for audio_info in node_out["audio"]:
                            filename = audio_info.get("filename", "")
                            subfolder = audio_info.get("subfolder", "")
                            # Build path to ComfyUI output
                            comfy_output = Path(os.environ.get(
                                "COMFYUI_DIR",
                                "/media/ssinjin/c173cbdc-b600-4f53-8185-b87fbce0bc3b/ComfyUI",
                            )) / "output"
                            if subfolder:
                                mp3_path = comfy_output / subfolder / filename
                            else:
                                mp3_path = comfy_output / filename

                            if mp3_path.exists():
                                logger.info("Audio generated: %s", mp3_path)
                                return mp3_path

                logger.error("ComfyUI completed but no audio output found")
                return None

            elif status.get("status_str") == "error":
                # Log node errors if available
                node_errors = hist[prompt_id].get("node_errors", {})
                logger.error("ComfyUI execution error: %s", json.dumps(node_errors, indent=2)[:500])
                return None

        if attempt % 30 == 0 and attempt > 0:
            logger.info("Still waiting for ComfyUI... (%ds)", attempt * 2)

    logger.error("ComfyUI timeout after 10 minutes")
    return None


def mp3_to_wav(mp3_path: Path, wav_path: Path) -> bool:
    """Convert MP3 to WAV using ffmpeg."""
    import subprocess
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(mp3_path),
                "-ar", "24000", "-ac", "1", "-sample_fmt", "s16",
                str(wav_path),
            ],
            capture_output=True,
            check=True,
        )
        logger.info("Converted %s -> %s", mp3_path.name, wav_path.name)
        return True
    except subprocess.CallProcessError as e:
        logger.error("ffmpeg conversion failed: %s", e.stderr.decode()[:200])
        return False


def generate_speech_for_article(
    article_id: int,
    text: str,
    force: bool = False,
    category: str = None,
) -> Optional[Path]:
    """
    Full Harvey pipeline for one article:
      1. LLM rewrite as Paul Harvey
      2. Voice clone TTS via ComfyUI Qwen3-TTS
      3. Cache the .wav and script
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

        # Step 2: Strip pause markers for TTS
        tts_text = strip_pause_markers(script)

        # Step 3: Generate via ComfyUI
        output_tag = f"harvey_{category or 'article'}_{article_id}"
        logger.info("[%d] Generating Harvey voice clone via ComfyUI (%d chars)...", article_id, len(tts_text))
        mp3_path = generate_via_comfyui(tts_text, output_filename=output_tag)

        if mp3_path is None:
            logger.error("[%d] ComfyUI generation failed", article_id)
            return None

        # Step 4: Convert MP3 to WAV for the web pipeline
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        if mp3_to_wav(mp3_path, cache_path):
            logger.info("[%d] Audio saved to %s", article_id, cache_path)
            # Clean up the MP3 from ComfyUI output if desired (optional)
            # mp3_path.unlink(missing_ok=True)
            return cache_path
        else:
            logger.error("[%d] MP3 -> WAV conversion failed", article_id)
            return None

    except Exception as e:
        logger.error("[%d] Failed to generate audio: %s", article_id, e)
        import traceback
        traceback.print_exc()
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