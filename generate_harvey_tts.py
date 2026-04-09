#!/usr/bin/env python3
"""Generate Harvey voice clone TTS from a script file via ComfyUI.

Usage:
    python generate_harvey_tts.py                          # use default script
    python generate_harvey_tts.py my_script.txt            # use custom script file
    python generate_harvey_tts.py --text "Hello world"     # use inline text

Output: /media/ssinjin/c173cbdc-b600-4f53-8185-b87fbce0bc3b/ComfyUI/input/harveyclip.wav
"""
import argparse
import json
import logging
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("harvey_tts")

COMFYUI_URL = "http://localhost:8188"
COMFYUI_DIR = Path("/media/ssinjin/c173cbdc-b600-4f53-8185-b87fbce0bc3b/ComfyUI")
SCRIPT_PATH = COMFYUI_DIR / "input" / "harvey_jocko_script.txt"
OUTPUT_PATH = COMFYUI_DIR / "input" / "harveyclip.wav"
REF_AUDIO = "harveyclip_5s.wav"  # in ComfyUI input/
REF_TEXT = "Look at the grand canyon, it took millions of years to get right.\n\nand eveolution boy!"


def generate_via_comfyui(text: str, output_filename: str = "harvey_output") -> Path | None:
    """Submit TTS job to ComfyUI and wait for the result."""

    workflow = {
        "1": {
            "class_type": "easy positive",
            "inputs": {"positive": REF_TEXT},
        },
        "3": {
            "class_type": "easy positive",
            "inputs": {"positive": text},
        },
        "5": {
            "class_type": "LoadAudio",
            "inputs": {"audio": REF_AUDIO},
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
        logger.error("ComfyUI HTTP %d: %s", e.code, e.read().decode()[:500])
        return None
    except Exception as e:
        logger.error("Failed to submit to ComfyUI: %s", e)
        return None

    prompt_id = result.get("prompt_id")
    if not prompt_id:
        logger.error("No prompt_id: %s", result)
        return None

    logger.info("Prompt ID: %s — waiting for generation...", prompt_id)

    for attempt in range(600):
        time.sleep(2)
        try:
            hist_resp = urllib.request.urlopen(
                urllib.request.Request(f"{COMFYUI_URL}/history/{prompt_id}"),
                timeout=10,
            )
            hist = json.loads(hist_resp.read())
        except Exception:
            continue

        if prompt_id in hist:
            status = hist[prompt_id].get("status", {})
            if status.get("completed", False) or status.get("status_str") == "success":
                outputs = hist[prompt_id].get("outputs", {})
                for node_id, node_out in outputs.items():
                    if "audio" in node_out:
                        for audio_info in node_out["audio"]:
                            filename = audio_info.get("filename", "")
                            subfolder = audio_info.get("subfolder", "")
                            output_dir = COMFYUI_DIR / "output"
                            mp3_path = output_dir / (subfolder + "/" + filename if subfolder else filename)
                            if mp3_path.exists():
                                logger.info("Audio generated: %s", mp3_path)
                                return mp3_path
                logger.error("No audio output found")
                return None
            elif status.get("status_str") == "error":
                logger.error("ComfyUI error: %s", json.dumps(hist[prompt_id].get("node_errors", {}))[:500])
                return None

        if attempt % 30 == 0 and attempt > 0:
            logger.info("Still waiting... (%ds)", attempt * 2)

    logger.error("Timeout after 10 minutes")
    return None


def mp3_to_wav(mp3_path: Path, wav_path: Path) -> bool:
    import subprocess
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(mp3_path), "-ar", "24000", "-ac", "1", "-sample_fmt", "s16", str(wav_path)],
            capture_output=True, check=True,
        )
        return True
    except subprocess.CallProcessError as e:
        logger.error("ffmpeg failed: %s", e.stderr.decode()[:200])
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate Harvey voice clone TTS via ComfyUI")
    parser.add_argument("script_file", nargs="?", default=str(SCRIPT_PATH), help="Path to script text file")
    parser.add_argument("--text", "-t", help="Inline text to speak (overrides file)")
    parser.add_argument("--output", "-o", default=str(OUTPUT_PATH), help="Output WAV path")
    args = parser.parse_args()

    if args.text:
        text = args.text
    else:
        script_path = Path(args.script_file)
        logger.info("Loading script from %s", script_path)
        text = script_path.read_text(encoding="utf-8").strip()

    logger.info("Script (%d chars):\n%s\n", len(text), text[:200] + ("..." if len(text) > 200 else ""))

    mp3_path = generate_via_comfyui(text, output_filename="harvey_script")
    if mp3_path is None:
        logger.error("Generation failed")
        sys.exit(1)

    wav_path = Path(args.output)
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    if mp3_to_wav(mp3_path, wav_path):
        logger.info("✅ Done! WAV saved to %s", wav_path)
    else:
        logger.error("MP3 -> WAV conversion failed, MP3 is at %s", mp3_path)
        sys.exit(1)


if __name__ == "__main__":
    main()