"""Local text-to-speech via pyttsx3.

Engine is initialized once and reused. All operations are offline (SAPI5 on Windows).
No audio is sent to external services.
"""

import logging
import threading
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class VoiceInfo:
    id: str
    name: str
    languages: List[str]
    gender: str = ""


def get_available_voices() -> List[VoiceInfo]:
    """Return list of available TTS voices (without initializing a persistent engine).

    Useful for diagnostics. Returns empty list if pyttsx3 missing or init fails.
    """
    try:
        import pyttsx3
    except ImportError:
        logger.warning("pyttsx3 not installed — cannot list voices.")
        return []

    tmp_engine = None
    try:
        tmp_engine = pyttsx3.init()
        raw_voices = tmp_engine.getProperty("voices") or []
        voices: List[VoiceInfo] = []
        for v in raw_voices:
            # v has .id, .name, .languages, .gender on most platforms
            voices.append(
                VoiceInfo(
                    id=getattr(v, "id", ""),
                    name=getattr(v, "name", str(v)),
                    languages=[str(x) for x in getattr(v, "languages", [])],
                    gender=getattr(v, "gender", ""),
                )
            )
        return voices
    except Exception as exc:
        logger.warning("Failed to list TTS voices: %s", exc)
        return []
    finally:
        if tmp_engine is not None:
            try:
                tmp_engine.stop()
            except Exception:
                pass


class Speaker:
    """Reusable offline TTS engine (pyttsx3/SAPI5 on Windows)."""

    def __init__(
        self,
        enabled: bool = True,
        rate: int = 175,
        volume: float = 1.0,
        voice: str = "",
    ) -> None:
        self.enabled = enabled
        self.rate = rate
        self.volume = volume
        # voice may be an ID substring or exact ID; empty means system default
        self.voice = voice.strip() if voice else ""
        self._engine = None
        self._available = False
        self._initialized = False
        self._speak_lock = threading.Lock()
        self._is_speaking = False

    # ------------------------------------------------------------------
    # Initialization — called once at startup
    # ------------------------------------------------------------------
    def initialize(self) -> bool:
        """Initialize the TTS engine once. Returns True if available."""
        if self._initialized and self._available:
            logger.debug("TTS engine already initialized, skipping.")
            return True

        if not self.enabled:
            logger.info("TTS disabled via config (TTS_ENABLED=false).")
            self._initialized = True
            self._available = False
            return False

        try:
            import pyttsx3  # noqa: F401 — just checking import
        except ImportError:
            logger.warning("pyttsx3 not installed — TTS unavailable. Install with: pip install pyttsx3")
            print("WARNING:\nText-to-speech is unavailable (pyttsx3 not installed).")
            print("Voice input will continue to work.")
            print("Install TTS: pip install pyttsx3\n")
            self._initialized = True
            self._available = False
            return False

        try:
            import pyttsx3

            logger.info("Initializing TTS engine (rate=%d volume=%.2f voice=%r)...", self.rate, self.volume, self.voice or "default")
            self._engine = pyttsx3.init()

            # Configure rate — clamp to sane range
            try:
                rate = max(50, min(400, int(self.rate)))
                self._engine.setProperty("rate", rate)
            except Exception as exc:
                logger.warning("Failed to set TTS rate %s: %s", self.rate, exc)

            # Configure volume — clamp 0.0–1.0
            try:
                vol = max(0.0, min(1.0, float(self.volume)))
                self._engine.setProperty("volume", vol)
            except Exception as exc:
                logger.warning("Failed to set TTS volume %s: %s", self.volume, exc)

            # Configure voice if requested
            if self.voice:
                self._select_voice(self.voice)
            else:
                logger.info("Using system default TTS voice.")

            self._initialized = True
            self._available = True
            logger.info("TTS engine initialized successfully.")

            # Log selected voice
            try:
                current_voice = self._engine.getProperty("voice")
                logger.info("Selected TTS voice ID: %s", current_voice)
            except Exception:
                pass

            return True

        except Exception as exc:
            logger.exception("Failed to initialize TTS engine")
            print("WARNING:\nUnable to initialize text-to-speech.")
            print(f"Details: {exc}")
            print("Voice input will continue to work.\n")
            self._initialized = True
            self._available = False
            # Clean up partially created engine
            if self._engine is not None:
                try:
                    self._engine.stop()
                except Exception:
                    pass
                self._engine = None
            return False

    def _select_voice(self, voice_id: str) -> None:
        """Attempt to select voice by ID substring; fall back to default on failure."""
        if self._engine is None:
            return
        try:
            voices = self._engine.getProperty("voices") or []
            if not voices:
                logger.warning("No TTS voices found — using default.")
                return

            # Try exact match first, then substring
            target = voice_id.lower()
            matched = None
            for v in voices:
                vid = getattr(v, "id", "")
                vname = getattr(v, "name", "")
                if target == vid.lower():
                    matched = vid
                    break
            if matched is None:
                for v in voices:
                    vid = getattr(v, "id", "")
                    vname = getattr(v, "name", "")
                    if target in vid.lower() or target in vname.lower():
                        matched = vid
                        break

            if matched:
                self._engine.setProperty("voice", matched)
                logger.info("TTS voice set to: %s (requested %r)", matched, voice_id)
            else:
                logger.warning("Requested TTS voice %r not found — using system default.", voice_id)
                logger.info("Available voices:")
                for idx, v in enumerate(voices):
                    logger.info("  [%d] %s (%s)", idx, getattr(v, "name", "?"), getattr(v, "id", "?"))
                print(f'WARNING: TTS voice "{voice_id}" not found — using default voice.')
                # Show available briefly on console too
                print("Available voices:")
                for idx, v in enumerate(voices):
                    print(f"  [{idx}] {getattr(v, 'name', '?')}")
        except Exception as exc:
            logger.warning("Failed to set TTS voice %r: %s — using default.", voice_id, exc)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def is_available(self) -> bool:
        return self._available and self._engine is not None

    @property
    def is_enabled(self) -> bool:
        return self.enabled

    # ------------------------------------------------------------------
    # Speak / Stop / Shutdown
    # ------------------------------------------------------------------
    def speak(self, text: str) -> bool:
        """Speak text aloud. Thread-safe, single speech active. Returns True if spoken."""
        if not text or not text.strip():
            logger.debug("speak() called with empty text — skipping.")
            return False

        if not self.enabled:
            logger.debug("TTS disabled — not speaking.")
            return False

        if not self.is_available:
            if not self._initialized:
                self.initialize()
            if not self.is_available:
                logger.warning("TTS not available — cannot speak: %r", text[:60])
                return False

        # Ensure only one speech at a time
        if not self._speak_lock.acquire(blocking=False):
            logger.warning("[INTERRUPT] TTS busy — stopping previous then speaking")
            try:
                self.stop()
            except Exception:
                pass
            # wait briefly for lock
            if not self._speak_lock.acquire(timeout=1.0):
                logger.warning("TTS speak lock timeout")
                return False

        cleaned = text.strip()
        logger.info("TTS speaking: %r (%d chars)", cleaned[:80], len(cleaned))
        self._is_speaking = True
        try:
            assert self._engine is not None
            self._engine.say(cleaned)
            self._engine.runAndWait()
            logger.info("TTS speech completed.")
            return True
        except RuntimeError as exc:
            logger.warning("TTS runtime error (may already be speaking): %s", exc)
            try:
                self._engine.stop()
            except Exception:
                pass
            try:
                self._engine.say(cleaned)
                self._engine.runAndWait()
                logger.info("TTS retry succeeded.")
                return True
            except Exception as exc2:
                logger.error("TTS retry failed: %s", exc2)
                return False
        except Exception as exc:
            logger.error("TTS speak failed: %s", exc)
            return False
        finally:
            self._is_speaking = False
            try:
                self._speak_lock.release()
            except Exception:
                pass

    def stop(self) -> None:
        """Stop current speech immediately. Safe to call multiple times or when not speaking."""
        if self._engine is None:
            logger.debug("[INTERRUPT] TTS stop called but engine is None — no-op")
            return
        try:
            self._engine.stop()
            self._is_speaking = False
            logger.info("[INTERRUPT] TTS stopped.")
        except Exception as exc:
            logger.warning("TTS stop failed: %s", exc)

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    def shutdown(self) -> None:
        """Cleanly release TTS resources."""
        if self._engine is None:
            return
        try:
            self._engine.stop()
        except Exception:
            pass
        # pyttsx3 has no explicit shutdown, just drop reference
        self._engine = None
        self._available = False
        logger.info("TTS shutdown complete.")

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def list_voices(self) -> List[VoiceInfo]:
        """List voices via the active engine if available, otherwise via temp engine."""
        if self._engine is not None:
            try:
                raw = self._engine.getProperty("voices") or []
                return [
                    VoiceInfo(
                        id=getattr(v, "id", ""),
                        name=getattr(v, "name", str(v)),
                        languages=[str(x) for x in getattr(v, "languages", [])],
                        gender=getattr(v, "gender", ""),
                    )
                    for v in raw
                ]
            except Exception:
                pass
        return get_available_voices()

    def print_voices(self) -> None:
        """Print available voices to stdout."""
        voices = self.list_voices()
        if not voices:
            print("No TTS voices found (is pyttsx3 installed and SAPI5 available?).")
            return
        print("\nAvailable voices:\n")
        selected_id = ""
        if self._engine is not None:
            try:
                selected_id = self._engine.getProperty("voice") or ""
            except Exception:
                pass
        for idx, v in enumerate(voices):
            marker = " *" if v.id == selected_id else ""
            print(f"  [{idx}] {v.name} ({v.id}){marker}")
        print()
        if selected_id:
            print(f"Selected voice: {selected_id}\n")
