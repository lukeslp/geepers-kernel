"""
Text-to-Speech Utilities
Reusable TTS functionality using Google Text-to-Speech (gTTS).

Extracted from gtts_cli.py for use across projects.
"""

import os
import sys
import subprocess
import tempfile
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass


logger = logging.getLogger(__name__)


# Check gTTS availability at module level
try:
    from gtts import gTTS
    from gtts.lang import tts_langs
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    logger.warning("gTTS not installed. Install with: pip install gtts")


@dataclass
class TTSResult:
    """Result of TTS generation"""
    success: bool
    file_path: Optional[str] = None
    file_size_kb: Optional[float] = None
    error: Optional[str] = None


def check_gtts_available() -> bool:
    """
    Check if gTTS is available and can connect to Google's service.

    Returns:
        True if gTTS is available and functional, False otherwise
    """
    if not GTTS_AVAILABLE:
        logger.error("gTTS is not installed")
        return False

    try:
        # Test internet connection by trying to get languages
        tts_langs()
        return True
    except Exception as e:
        logger.error(f"Failed to connect to Google TTS service: {e}")
        return False


def get_available_languages() -> Dict[str, str]:
    """
    Get all available languages supported by Google TTS.

    Returns:
        Dictionary mapping language codes to language names
        Empty dict if retrieval fails

    Example:
        >>> langs = get_available_languages()  # doctest: +SKIP
        >>> 'en' in langs  # doctest: +SKIP
        True
        >>> langs['en']  # doctest: +SKIP
        'English'
    """
    if not GTTS_AVAILABLE:
        logger.error("gTTS not available")
        return {}

    try:
        return tts_langs()
    except Exception as e:
        logger.error(f"Failed to retrieve languages: {e}")
        return {}


def generate_tts(
    text: str,
    output_file: Optional[str] = None,
    lang: str = "en",
    slow: bool = False,
    tld: Optional[str] = None
) -> TTSResult:
    """
    Generate Text-to-Speech using Google TTS.

    Args:
        text: Text to convert to speech
        output_file: Path to save the output file (if None, creates temp file)
        lang: Language code (default: "en")
        slow: Whether to use slower speech rate (default: False)
        tld: Top Level Domain for the Google TTS service (e.g., "com", "co.uk")

    Returns:
        TTSResult with success status and file information

    Examples:
        >>> result = generate_tts("Hello world")  # doctest: +SKIP
        >>> result.success  # doctest: +SKIP
        True
        >>> result.file_path  # doctest: +SKIP
        '/tmp/tts_output_12345.mp3'
    """
    if not GTTS_AVAILABLE:
        return TTSResult(
            success=False,
            error="gTTS not installed. Install with: pip install gtts"
        )

    # Create output file path if not provided
    if output_file is None:
        temp_dir = tempfile.gettempdir()
        output_file = os.path.join(temp_dir, f"tts_output_{os.getpid()}.mp3")

    try:
        logger.info(f"Generating TTS for {len(text)} characters (lang={lang}, slow={slow})")

        # Create gTTS instance
        tts_options = {
            "text": text,
            "lang": lang,
            "slow": slow
        }

        if tld:
            tts_options["tld"] = tld

        tts = gTTS(**tts_options)

        # Save to file
        tts.save(output_file)

        if not os.path.exists(output_file):
            raise FileNotFoundError("Output file was not created")

        file_size = os.path.getsize(output_file) / 1024  # KB

        logger.info(f"Generated TTS audio file: {output_file} ({file_size:.1f} KB)")

        return TTSResult(
            success=True,
            file_path=output_file,
            file_size_kb=file_size
        )

    except Exception as e:
        logger.error(f"Failed to generate TTS: {e}")
        return TTSResult(
            success=False,
            error=str(e)
        )


def play_audio(file_path: str) -> bool:
    """
    Play an audio file using system-specific commands.

    Tries multiple audio players depending on the platform:
    - macOS: afplay
    - Windows: winsound
    - Linux: paplay, aplay, play (sox), mplayer

    Args:
        file_path: Path to the audio file to play

    Returns:
        True if playback was successful, False otherwise

    Example:
        >>> play_audio('/path/to/audio.mp3')  # doctest: +SKIP
        True
    """
    if not os.path.exists(file_path):
        logger.error(f"Audio file not found: {file_path}")
        return False

    try:
        logger.info(f"Playing audio: {file_path}")

        if sys.platform == "darwin":  # macOS
            subprocess.run(["afplay", file_path], check=True, capture_output=True)

        elif sys.platform == "win32":  # Windows
            try:
                import winsound
                winsound.PlaySound(file_path, winsound.SND_FILENAME)
            except ImportError:
                logger.error("winsound module not available on Windows")
                return False

        else:  # Linux and other Unix-like systems
            # Try multiple players in order of preference
            players = [
                ["paplay", file_path],  # PulseAudio
                ["aplay", "-q", file_path],  # ALSA
                ["play", "-q", file_path],  # SoX
                ["mplayer", "-really-quiet", file_path],  # MPlayer
                ["mpg123", "-q", file_path],  # mpg123
            ]

            for player in players:
                try:
                    subprocess.run(
                        player,
                        check=True,
                        capture_output=True,
                        timeout=30
                    )
                    logger.debug(f"Audio played successfully with {player[0]}")
                    return True
                except (subprocess.SubprocessError, FileNotFoundError):
                    continue

            # No player worked
            logger.error("No suitable audio player found. Install one of: paplay, aplay, play, mplayer, mpg123")
            return False

        logger.info("Audio playback complete")
        return True

    except Exception as e:
        logger.error(f"Could not play audio: {e}")
        return False


def text_to_speech(
    text: str,
    lang: str = "en",
    slow: bool = False,
    play: bool = False,
    output_file: Optional[str] = None
) -> TTSResult:
    """
    Convenience function: Generate TTS and optionally play it.

    Args:
        text: Text to convert to speech
        lang: Language code (default: "en")
        slow: Whether to use slower speech rate (default: False)
        play: Whether to play the audio after generation (default: False)
        output_file: Path to save the output file (if None, creates temp file)

    Returns:
        TTSResult with success status and file information

    Example:
        >>> result = text_to_speech("Hello world", play=True)  # doctest: +SKIP
        >>> result.success  # doctest: +SKIP
        True
    """
    # Generate TTS
    result = generate_tts(text, output_file, lang, slow)

    # Play if requested and generation was successful
    if result.success and play and result.file_path:
        play_success = play_audio(result.file_path)
        if not play_success:
            logger.warning("TTS generated successfully but playback failed")

    return result


def validate_language(lang: str) -> bool:
    """
    Check if a language code is supported by gTTS.

    Args:
        lang: Language code to validate

    Returns:
        True if language is supported, False otherwise

    Example:
        >>> validate_language('en')  # doctest: +SKIP
        True
        >>> validate_language('xyz')  # doctest: +SKIP
        False
    """
    if not GTTS_AVAILABLE:
        return False

    try:
        languages = get_available_languages()
        return lang in languages
    except Exception:
        return False


def get_language_name(lang_code: str) -> Optional[str]:
    """
    Get the full name of a language from its code.

    Args:
        lang_code: Language code (e.g., "en", "es", "fr")

    Returns:
        Language name or None if not found

    Example:
        >>> get_language_name('en')  # doctest: +SKIP
        'English'
        >>> get_language_name('es')  # doctest: +SKIP
        'Spanish'
    """
    languages = get_available_languages()
    return languages.get(lang_code)


def list_common_languages() -> List[tuple]:
    """
    Get a list of commonly used languages.

    Returns:
        List of (code, name) tuples for common languages

    Example:
        >>> langs = list_common_languages()  # doctest: +SKIP
        >>> ('en', 'English') in langs  # doctest: +SKIP
        True
    """
    common = [
        'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh-CN', 'zh-TW',
        'ja', 'ko', 'ar', 'hi', 'nl', 'pl', 'tr', 'vi', 'th'
    ]

    languages = get_available_languages()
    return [
        (code, languages[code])
        for code in common
        if code in languages
    ]
