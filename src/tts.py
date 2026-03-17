"""Text-to-Speech module using Qwen3-TTS."""
import logging
import os
from pathlib import Path
from typing import Optional

import soundfile as sf
import torch

from .config import DB_PATH

logger = logging.getLogger("tts")

# Default model - using 0.6B for faster inference and lower memory
DEFAULT_MODEL = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
DEFAULT_SPEAKER = "Aiden"  # Sunny American male voice with clear midrange
DEFAULT_LANGUAGE = "English"

# Cache directory for audio files
AUDIO_CACHE_DIR = Path(__file__).parent.parent / "audio_cache"

# Global model instance (lazy loaded)
_model = None


def get_cache_path(article_id: int) -> Path:
    """Get the cache path for an article's audio file."""
    AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return AUDIO_CACHE_DIR / f"article_{article_id}.wav"


def is_available() -> bool:
    """Check if TTS is available (qwen-tts installed and working)."""
    try:
        from qwen_tts import Qwen3TTSModel
        return True
    except ImportError:
        return False


def get_model():
    """Get or initialize the TTS model (lazy loading)."""
    global _model
    if _model is None:
        if not is_available():
            raise RuntimeError("qwen-tts not installed. Run: pip install qwen-tts")
        
        from qwen_tts import Qwen3TTSModel
        
        logger.info(f"Loading Qwen3-TTS model: {DEFAULT_MODEL}")
        
        # Determine device
        if torch.cuda.is_available():
            device_map = "cuda:0"
            dtype = torch.bfloat16
            logger.info("Using CUDA for TTS")
        else:
            device_map = "cpu"
            dtype = torch.float32
            logger.info("Using CPU for TTS (slower)")
        
        try:
            _model = Qwen3TTSModel.from_pretrained(
                DEFAULT_MODEL,
                device_map=device_map,
                dtype=dtype,
                attn_implementation="eager",  # Use eager attention for compatibility
            )
            logger.info("TTS model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load TTS model: {e}")
            raise
    
    return _model


def generate_speech(
    text: str,
    output_path: str | Path,
    speaker: str = DEFAULT_SPEAKER,
    language: str = DEFAULT_LANGUAGE,
    instruct: Optional[str] = None,
) -> bool:
    """
    Generate speech from text using Qwen3-TTS.
    
    Args:
        text: The text to convert to speech
        output_path: Where to save the audio file
        speaker: Speaker name (e.g., 'Aiden', 'Ryan', 'Serena')
        language: Language code (e.g., 'English', 'Chinese')
        instruct: Optional instruction for voice style (e.g., "Speak slowly and clearly")
    
    Returns:
        True if successful, False otherwise
    """
    try:
        model = get_model()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Generating speech for text ({len(text)} chars) with speaker={speaker}")
        
        # Generate audio
        wavs, sr = model.generate_custom_voice(
            text=text,
            language=language,
            speaker=speaker,
            instruct=instruct or "",
        )
        
        # Save audio file
        sf.write(str(output_path), wavs[0], sr)
        logger.info(f"Audio saved to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate speech: {e}")
        return False


def generate_speech_for_article(article_id: int, text: str, force: bool = False) -> Optional[Path]:
    """
    Generate speech for an article and cache it.
    
    Args:
        article_id: The article ID
        text: The text content to convert
        force: If True, regenerate even if cached file exists
    
    Returns:
        Path to the audio file if successful, None otherwise
    """
    cache_path = get_cache_path(article_id)
    
    # Check if already cached
    if cache_path.exists() and not force:
        logger.info(f"Using cached audio for article {article_id}")
        return cache_path
    
    # Generate new audio
    if generate_speech(text, cache_path):
        return cache_path
    
    return None


def get_audio_for_article(article_id: int) -> Optional[Path]:
    """Get the cached audio file for an article if it exists."""
    cache_path = get_cache_path(article_id)
    if cache_path.exists():
        return cache_path
    return None


def delete_audio_cache(article_id: Optional[int] = None) -> int:
    """
    Delete cached audio files.
    
    Args:
        article_id: If provided, delete only that article's audio.
                   If None, delete all cached audio.
    
    Returns:
        Number of files deleted
    """
    deleted = 0
    
    if article_id is not None:
        cache_path = get_cache_path(article_id)
        if cache_path.exists():
            cache_path.unlink()
            deleted += 1
    else:
        if AUDIO_CACHE_DIR.exists():
            for f in AUDIO_CACHE_DIR.glob("*.wav"):
                f.unlink()
                deleted += 1
    
    return deleted


# Voice cloning functions (for Phase 2 - Paul Harvey voice)
def generate_voice_clone(
    text: str,
    output_path: str | Path,
    ref_audio: str | Path,
    ref_text: str,
    language: str = DEFAULT_LANGUAGE,
) -> bool:
    """
    Generate speech using voice cloning.
    
    Args:
        text: The text to convert to speech
        output_path: Where to save the audio file
        ref_audio: Path to reference audio file for voice cloning
        ref_text: Transcript of the reference audio
        language: Language code
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from qwen_tts import Qwen3TTSModel
        
        # Load the base model for voice cloning
        model = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            device_map="cuda:0" if torch.cuda.is_available() else "cpu",
            dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
            attn_implementation="eager",
        )
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Generating voice clone for text ({len(text)} chars)")
        
        wavs, sr = model.generate_voice_clone(
            text=text,
            language=language,
            ref_audio=str(ref_audio),
            ref_text=ref_text,
        )
        
        sf.write(str(output_path), wavs[0], sr)
        logger.info(f"Cloned audio saved to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate voice clone: {e}")
        return False


def create_voice_clone_prompt(ref_audio: str | Path, ref_text: str):
    """
    Create a reusable voice clone prompt from reference audio.
    
    This is useful for generating multiple clips with the same voice
    without reprocessing the reference audio each time.
    """
    try:
        from qwen_tts import Qwen3TTSModel
        
        model = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            device_map="cuda:0" if torch.cuda.is_available() else "cpu",
            dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
            attn_implementation="eager",
        )
        
        return model.create_voice_clone_prompt(
            ref_audio=str(ref_audio),
            ref_text=ref_text,
        )
    except Exception as e:
        logger.error(f"Failed to create voice clone prompt: {e}")
        return None