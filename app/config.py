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

        whisper_model = _env_str("WHISPER_MODEL", "base")
        whisper_device = _env_str("WHISPER_DEVICE", "cpu")
        whisper_compute_type = _env_str("WHISPER_COMPUTE_TYPE", "int8")
        sample_rate = _env_int("SAMPLE_RATE", 16000)
        max_recording_seconds = _env_int("MAX_RECORDING_SECONDS", 15)

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

        config = cls(
            whisper_model=whisper_model,
            whisper_device=whisper_device,
            whisper_compute_type=whisper_compute_type,
            sample_rate=sample_rate,
            max_recording_seconds=max_recording_seconds,
            language=language,
        )
        logger.info(
            "Config loaded: model=%s device=%s compute=%s sr=%d max_sec=%d lang=%s",
            config.whisper_model,
            config.whisper_device,
            config.whisper_compute_type,
            config.sample_rate,
            config.max_recording_seconds,
            config.language or "auto",
        )
        return config
