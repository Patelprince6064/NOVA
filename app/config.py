"""Configuration for Nova Voice Engine.

Loads settings from environment variables / .env file with sensible defaults.
All Phase 1 configuration is centralized here — no hardcoded values spread
through the codebase.
"""

import os
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Config:
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    sample_rate: int = 16000
    max_recording_seconds: int = 15
    language: str | None = None  # None = auto-detect
    # TTS settings
    tts_enabled: bool = True
    tts_rate: int = 175
    tts_volume: float = 1.0
    tts_voice: str = ""
    # Wake-word settings (Phase 3)
    wake_word_enabled: bool = True
    wake_word: str = "hey nova"
    wake_word_threshold: float = 0.5
    command_timeout_seconds: int = 8
    wake_sound_enabled: bool = True
    wake_word_cooldown_ms: int = 500
    # PC control settings (Phase 4)
    pc_control_enabled: bool = True
    default_scroll_amount: int = 5
    action_timeout_seconds: int = 10

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from environment, with defaults."""
        # Load .env if python-dotenv is available; otherwise rely on os.environ.
        try:
            from dotenv import load_dotenv

            load_dotenv()
            logger.debug("Loaded .env file")
        except ImportError:
            logger.debug("python-dotenv not installed, using os.environ only")
        except Exception as exc:
            logger.warning("Failed to load .env: %s", exc)

        def _env_str(key: str, default: str) -> str:
            val = os.getenv(key)
            if val is None or val.strip() == "":
                return default
            return val.strip()

        def _env_int(key: str, default: int) -> int:
            raw = os.getenv(key)
            if raw is None or raw.strip() == "":
                return default
            try:
                return int(raw.strip())
            except ValueError:
                logger.warning("Invalid integer for %s=%r, using default %d", key, raw, default)
                return default

        def _env_float(key: str, default: float) -> float:
            raw = os.getenv(key)
            if raw is None or raw.strip() == "":
                return default
            try:
                return float(raw.strip())
            except ValueError:
                logger.warning("Invalid float for %s=%r, using default %r", key, raw, default)
                return default

        def _env_bool(key: str, default: bool) -> bool:
            raw = os.getenv(key)
            if raw is None or raw.strip() == "":
                return default
            val = raw.strip().lower()
            if val in ("1", "true", "yes", "on", "enabled"):
                return True
            if val in ("0", "false", "no", "off", "disabled"):
                return False
            logger.warning("Invalid boolean for %s=%r, using default %r", key, raw, default)
            return default

        whisper_model = _env_str("WHISPER_MODEL", "base")
        whisper_device = _env_str("WHISPER_DEVICE", "cpu")
        whisper_compute_type = _env_str("WHISPER_COMPUTE_TYPE", "int8")
        sample_rate = _env_int("SAMPLE_RATE", 16000)
        max_recording_seconds = _env_int("MAX_RECORDING_SECONDS", 15)
        tts_enabled = _env_bool("TTS_ENABLED", True)
        tts_rate = _env_int("TTS_RATE", 175)
        tts_volume = _env_float("TTS_VOLUME", 1.0)
        tts_voice = _env_str("TTS_VOICE", "") if os.getenv("TTS_VOICE") and os.getenv("TTS_VOICE", "").strip() else ""
        wake_word_enabled = _env_bool("WAKE_WORD_ENABLED", True)
        wake_word = _env_str("WAKE_WORD", "hey nova")
        wake_word_threshold = _env_float("WAKE_WORD_THRESHOLD", 0.5)
        command_timeout_seconds = _env_int("COMMAND_TIMEOUT_SECONDS", 8)
        wake_sound_enabled = _env_bool("WAKE_SOUND_ENABLED", True)
        wake_word_cooldown_ms = _env_int("WAKE_WORD_COOLDOWN_MS", 500)
        pc_control_enabled = _env_bool("PC_CONTROL_ENABLED", True)
        default_scroll_amount = _env_int("DEFAULT_SCROLL_AMOUNT", 5)
        action_timeout_seconds = _env_int("ACTION_TIMEOUT_SECONDS", 10)

        # Optional language override (e.g., "en")
        lang_raw = os.getenv("WHISPER_LANGUAGE")
        language = lang_raw.strip() if lang_raw and lang_raw.strip() else None

        # Clamp sample rate and duration to sane ranges
        if sample_rate not in (8000, 16000, 22050, 44100, 48000):
            # faster-whisper expects 16kHz audio; warn if non-standard.
            logger.warning("SAMPLE_RATE=%d is non-standard; recommended is 16000", sample_rate)

        if max_recording_seconds <= 0 or max_recording_seconds > 120:
            logger.warning(
                "MAX_RECORDING_SECONDS=%d out of range (1-120), clamping to 15",
                max_recording_seconds,
            )
            max_recording_seconds = 15

        # Clamp TTS volume/rate
        if not 0.0 <= tts_volume <= 1.0:
            logger.warning("TTS_VOLUME=%.2f out of range (0.0-1.0), clamping.", tts_volume)
            tts_volume = max(0.0, min(1.0, tts_volume))
        if not 50 <= tts_rate <= 400:
            logger.warning("TTS_RATE=%d out of range (50-400), clamping.", tts_rate)
            tts_rate = max(50, min(400, tts_rate))
        # Clamp wake-word settings
        if not 0.0 <= wake_word_threshold <= 1.0:
            logger.warning("WAKE_WORD_THRESHOLD=%.2f out of range (0.0-1.0), clamping.", wake_word_threshold)
            wake_word_threshold = max(0.0, min(1.0, wake_word_threshold))
        if not 1 <= command_timeout_seconds <= 30:
            logger.warning("COMMAND_TIMEOUT_SECONDS=%d out of range (1-30), clamping to 8.", command_timeout_seconds)
            command_timeout_seconds = 8
        if not 0 <= wake_word_cooldown_ms <= 5000:
            logger.warning("WAKE_WORD_COOLDOWN_MS=%d out of range (0-5000), clamping to 500.", wake_word_cooldown_ms)
            wake_word_cooldown_ms = 500
        if not wake_word:
            logger.warning("WAKE_WORD empty — using default 'hey nova'")
            wake_word = "hey nova"
        if not 1 <= default_scroll_amount <= 20:
            logger.warning("DEFAULT_SCROLL_AMOUNT=%d out of range (1-20), clamping to 5.", default_scroll_amount)
            default_scroll_amount = 5
        if not 1 <= action_timeout_seconds <= 30:
            logger.warning("ACTION_TIMEOUT_SECONDS=%d out of range (1-30), clamping to 10.", action_timeout_seconds)
            action_timeout_seconds = 10

        config = cls(
            whisper_model=whisper_model,
            whisper_device=whisper_device,
            whisper_compute_type=whisper_compute_type,
            sample_rate=sample_rate,
            max_recording_seconds=max_recording_seconds,
            language=language,
            tts_enabled=tts_enabled,
            tts_rate=tts_rate,
            tts_volume=tts_volume,
            tts_voice=tts_voice,
            wake_word_enabled=wake_word_enabled,
            wake_word=wake_word,
            wake_word_threshold=wake_word_threshold,
            command_timeout_seconds=command_timeout_seconds,
            wake_sound_enabled=wake_sound_enabled,
            wake_word_cooldown_ms=wake_word_cooldown_ms,
            pc_control_enabled=pc_control_enabled,
            default_scroll_amount=default_scroll_amount,
            action_timeout_seconds=action_timeout_seconds,
        )
        logger.info(
            "Config loaded: model=%s device=%s compute=%s sr=%d max_sec=%d lang=%s tts=%s rate=%d vol=%.2f voice=%r wake=%s(%s) thr=%.2f timeout=%d cooldown=%d sound=%s pc=%s scroll=%d action_timeout=%d",
            config.whisper_model,
            config.whisper_device,
            config.whisper_compute_type,
            config.sample_rate,
            config.max_recording_seconds,
            config.language or "auto",
            "enabled" if config.tts_enabled else "disabled",
            config.tts_rate,
            config.tts_volume,
            config.tts_voice or "default",
            config.wake_word,
            "enabled" if config.wake_word_enabled else "disabled",
            config.wake_word_threshold,
            config.command_timeout_seconds,
            config.wake_word_cooldown_ms,
            "on" if config.wake_sound_enabled else "off",
            "enabled" if pc_control_enabled else "disabled",
            default_scroll_amount,
            action_timeout_seconds,
        )
        return config
