"""Health checker for Nova — structured status, no secrets."""

import logging
from typing import Dict

logger = logging.getLogger(__name__)

def run_health_check(config) -> Dict[str, bool]:
    """Check components. Returns dict with bool statuses."""
    health = {
        "microphone": False,
        "speaker": False,
        "speech": False,
        "wake_word": False,
        "browser": False,
        "ai": False,
        "vision": False,
    }
    # Microphone
    try:
        import sounddevice as sd
        try:
            devs = sd.query_devices()
            health["microphone"] = any(d.get("max_input_channels", 0) > 0 for d in devs)
        except Exception:
            health["microphone"] = False
    except ImportError:
        health["microphone"] = False

    # Speaker/TTS
    try:
        from app.tts.speaker import Speaker
        # Don't init engine fully — just check pyttsx3 available
        try:
            import pyttsx3
            health["speaker"] = True
        except ImportError:
            health["speaker"] = bool(getattr(config, "tts_enabled", False) is False)  # if disabled, consider ok
            if not health["speaker"]:
                health["speaker"] = False
    except Exception:
        health["speaker"] = False

    # Speech model
    try:
        # Check if model can be imported, not if loaded
        from faster_whisper import WhisperModel  # type: ignore
        health["speech"] = True
    except ImportError:
        health["speech"] = False
    except Exception:
        health["speech"] = bool(getattr(config, "whisper_model", None))

    # Wake word
    try:
        if getattr(config, "wake_word_enabled", False):
            # Check vosk available or dummy ok
            try:
                import vosk  # type: ignore
                health["wake_word"] = True
            except ImportError:
                health["wake_word"] = True  # dummy still works
        else:
            health["wake_word"] = False
    except Exception:
        health["wake_word"] = False

    # Browser
    try:
        if getattr(config, "browser_enabled", False):
            try:
                from playwright.sync_api import sync_playwright  # type: ignore
                health["browser"] = True
            except ImportError:
                health["browser"] = False
        else:
            health["browser"] = True  # disabled is not an error — considered ok for degraded mode
            # But for health we want to show disabled as not available? Keep True for degraded
            health["browser"] = not getattr(config, "browser_enabled", True) or health["browser"]
            # Simpler: if disabled, return True (degraded ok)
            if not getattr(config, "browser_enabled", True):
                health["browser"] = True
    except Exception:
        health["browser"] = False

    # AI
    try:
        if getattr(config, "llm_enabled", False):
            has_key = bool(getattr(config, "llm_api_key", ""))
            try:
                import openai  # type: ignore
                health["ai"] = has_key and True
            except ImportError:
                health["ai"] = False
        else:
            health["ai"] = True  # disabled is ok degraded
            if not getattr(config, "llm_enabled", True):
                health["ai"] = True
    except Exception:
        health["ai"] = False

    # Vision
    try:
        if getattr(config, "vision_enabled", False):
            try:
                import mss  # type: ignore
                from PIL import Image  # type: ignore
                health["vision"] = True
            except ImportError:
                health["vision"] = False
        else:
            health["vision"] = True
    except Exception:
        health["vision"] = False

    logger.info("Health check: %r", health)
    return health

def print_health(health: Dict[str, bool], verbose: bool = False):
    def mark(v): return "✓" if v else "✗"
    print("Microphone       " + mark(health.get("microphone")))
    print("Speaker          " + mark(health.get("speaker")))
    print("Speech Model     " + mark(health.get("speech")))
    print("Wake Word        " + mark(health.get("wake_word")))
    print("TTS              " + mark(health.get("speaker")))
    print("PC Control       ✓")  # always available logically
    print("Browser          " + mark(health.get("browser")))
    print("AI               " + mark(health.get("ai")))
    if verbose:
        print("Vision           " + mark(health.get("vision")))
    # Overall
    all_ok = all(health.get(k, False) for k in ("microphone","speaker","speech"))
    if all_ok:
        print("\nNova is ready.")
        print('\nSay:\n"Hey Nova"')
    else:
        print("\nSome components need attention (see logs/nova.log)")

    # Also log structured
    try:
        logger.info("Health printed: %r", health)
    except Exception:
        pass

    return health
