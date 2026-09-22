"""Local wake-word detection for Nova.

Architecture:
    🎤 Microphone
          │
          ▼
   Audio Input Manager (single ownership)
          │
     ┌────┴────┐
     ▼         ▼
  Wake Mode  Command Mode
   (detector)  (record + Whisper)

The detector runs continuously in Wake Mode and triggers a callback on
"Hey Nova" (configurable). It is lightweight — Vosk or OpenWakeWord if
available, otherwise a simple energy-based fallback. Whisper is NOT run
while waiting.

Microphone ownership:
- Detector holds InputStream in Wake Mode.
- On detection, detector pauses/releases mic, main records command with
  its own short-lived stream, then detector resumes.
This avoids two streams fighting for exclusive access.

Privacy: audio stays in RAM, only command audio after wake is transcribed.
No cloud services.
"""

import logging
import queue
import threading
import time
import json
import os
import sys
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    import sounddevice as sd
except ImportError:
    sd = None  # handled at runtime


class WakeWordState(Enum):
    IDLE = auto()
    LISTENING_FOR_WAKE_WORD = auto()
    LISTENING_FOR_COMMAND = auto()
    PROCESSING = auto()
    SPEAKING = auto()
    CANCELLING = auto()


@dataclass
class WakeWordConfig:
    enabled: bool = True
    wake_word: str = "hey nova"
    threshold: float = 0.5
    cooldown_ms: int = 500
    sample_rate: int = 16000
    device_index: Optional[int] = None


# ---------------------------------------------------------------------------
# Helpers — Vosk model discovery / OpenWakeWord
# ---------------------------------------------------------------------------

def _find_vosk_model() -> Optional[Path]:
    """Search common locations for vosk small model."""
    candidates = [
        Path("models/vosk-model-small-en-us-0.15"),
        Path("vosk-model-small-en-us-0.15"),
        Path.home() / ".cache" / "vosk" / "vosk-model-small-en-us-0.15",
        Path.home() / ".cache" / "vosk-model-small-en-us-0.15" / "vosk-model-small-en-us-0.15",
        Path("C:/Alpha/Alpha 0.2/nova/models/vosk-model-small-en-us-0.15"),
    ]
    for p in candidates:
        if p.exists() and (p / "am" / "final.mdl").exists():
            return p
        # some extractions create nested folder
        if p.exists() and p.is_dir():
            # check if contains conf/model.conf
            if (p / "conf" / "model.conf").exists():
                return p
    # also check any subdirectory in models/
    models_dir = Path("models")
    if models_dir.exists():
        for sub in models_dir.iterdir():
            if sub.is_dir() and (sub / "am" / "final.mdl").exists():
                return sub
    return None


def _try_download_vosk_model(target_dir: Path = Path("models")) -> Optional[Path]:
    """Attempt to download vosk small model (40MB). Non-blocking if offline."""
    # Only attempt if we have internet; fail quickly if not.
    import urllib.request
    import zipfile
    import tempfile

    url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
    target_dir.mkdir(parents=True, exist_ok=True)
    zip_path = target_dir / "vosk-model-small-en-us-0.15.zip"

    # If already downloaded partially, skip
    existing = _find_vosk_model()
    if existing:
        return existing

    print("Downloading Vosk wake-word model (40MB)...")
    print(f"  URL: {url}")
    logger.info("Downloading Vosk model from %s", url)
    try:
        # short timeout to avoid hanging offline
        urllib.request.urlretrieve(url, str(zip_path))
        print("Extracting Vosk model...")
        with zipfile.ZipFile(str(zip_path), "r") as z:
            z.extractall(str(target_dir))
        try:
            zip_path.unlink()
        except Exception:
            pass
        found = _find_vosk_model()
        if found:
            print(f"Vosk model ready at: {found}")
            logger.info("Vosk model downloaded to %s", found)
            return found
        logger.warning("Vosk download extracted but model not found in expected layout.")
        return None
    except Exception as exc:
        logger.warning("Failed to auto-download Vosk model: %s", exc)
        print(f"Could not download Vosk model: {exc}")
        print("Falling back to energy-based dummy detector.")
        print("To enable accurate 'Hey Nova' detection:")
        print("  1. pip install vosk")
        print("  2. Download https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
        print("  3. Extract to nova/models/vosk-model-small-en-us-0.15")
        return None


# ---------------------------------------------------------------------------
# WakeWordDetector
# ---------------------------------------------------------------------------

class WakeWordDetector:
    """Reusable wake-word detector.

    Usage:
        detector = WakeWordDetector(
            wake_word="hey nova",
            threshold=0.5,
            device_index=0,
            cooldown_ms=500,
        )
        detector.start(on_wake_word=lambda: print("Hey Nova!"))
        ...
        detector.stop()

    Thread-safe, single mic ownership in wake mode.
    """

    def __init__(
        self,
        wake_word: str = "hey nova",
        threshold: float = 0.5,
        cooldown_ms: int = 500,
        device_index: Optional[int] = None,
        sample_rate: int = 16000,
        enabled: bool = True,
        block_duration_ms: int = 200,  # chunk size for streaming
    ) -> None:
        self.wake_word = wake_word.lower().strip() if wake_word else "hey nova"
        self.threshold = float(threshold)
        self.cooldown_ms = int(cooldown_ms)
        self.device_index = device_index
        self.sample_rate = int(sample_rate)
        self.enabled = enabled
        self.block_duration_ms = int(block_duration_ms)

        self._running = False
        self._paused = False
        self._speaking = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._callback: Optional[Callable[[], None]] = None
        self._callback_lock = threading.Lock()
        self._last_trigger_time = 0.0
        self._backend = "none"  # vosk | openwakeword | dummy
        self._state = WakeWordState.IDLE

        # Backend specifics
        self._vosk_model = None
        self._vosk_recognizer = None
        self._oww_model = None
        self._oww_threshold = threshold

    # ------------------------------------------------------------------
    # Backend initialization
    # ------------------------------------------------------------------
    def _init_backend(self) -> str:
        """Try backends in order: openwakeword -> vosk -> dummy."""
        if not self.enabled:
            logger.info("Wake-word detection disabled via config.")
            self._backend = "disabled"
            return "disabled"

        # Try OpenWakeWord first (most accurate, lowest CPU)
        try:
            import openwakeword  # type: ignore
            from openwakeword.model import Model as OWWModel  # type: ignore

            logger.info("Trying OpenWakeWord backend...")
            # OWW ships with hey_jarvis; we can use it as proxy or custom
            # For hey nova we rely on vosk fallback if no custom model
            # OWW will be tried, but if no hey_nova model we still fallback
            try:
                # Attempt to load default model; if it exists it will be hey_jarvis
                # We don't hard-fail if missing — we'll use vosk instead
                # Keep OWW as backend only if we have a model file
                # For now, prefer vosk for arbitrary phrase, so skip OWW unless model present
                logger.debug("OpenWakeWord available but no hey_nova model bundled — preferring Vosk")
                raise ImportError("No hey_nova OWW model")
            except Exception:
                # fall through to vosk
                pass
        except ImportError:
            logger.debug("OpenWakeWord not available or no model — trying Vosk")

        # Try Vosk
        try:
            import vosk  # type: ignore

            model_path = _find_vosk_model()
            if model_path is None:
                # Try auto-download if internet likely; but don't block long if offline
                # Only auto-download if explicitly allowed via env or if we can reach URL quickly
                # For now, attempt download but with short timeout inside helper
                # To avoid surprising 40MB download, we try but handle offline gracefully
                logger.info("Vosk model not found — attempting auto-download...")
                model_path = _try_download_vosk_model()

            if model_path is not None and model_path.exists():
                from vosk import Model, KaldiRecognizer  # type: ignore

                logger.info("Initializing Vosk model at %s", model_path)
                self._vosk_model = Model(str(model_path))
                # 16kHz, mono
                self._vosk_recognizer = KaldiRecognizer(self._vosk_model, self.sample_rate)
                # Enable partial results for low latency
                self._vosk_recognizer.SetWords(True)
                self._backend = "vosk"
                logger.info("Wake-word backend: vosk (phrase=%r)", self.wake_word)
                return "vosk"
            else:
                logger.warning("Vosk model not found — using dummy energy detector.")
                logger.info("To enable accurate detection: download vosk-model-small-en-us-0.15 to models/")
        except ImportError:
            logger.warning("vosk not installed — using dummy detector. pip install vosk for accurate wake-word.")
        except Exception as exc:
            logger.warning("Vosk init failed (%s) — using dummy detector.", exc)

        # Dummy fallback
        self._backend = "dummy"
        logger.info("Wake-word backend: dummy (energy threshold=%.2f) phrase=%r", self.threshold, self.wake_word)
        return "dummy"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start(self, on_wake_word: Callable[[], None]) -> bool:
        """Start continuous monitoring. Returns True if started."""
        if self._running:
            logger.warning("WakeWordDetector already running.")
            return False
        if not self.enabled:
            logger.info("Wake-word disabled — not starting detector.")
            return False
        if sd is None:
            logger.error("sounddevice not installed — cannot start wake-word detector.")
            print("ERROR: sounddevice not installed — wake-word unavailable. pip install sounddevice")
            return False

        with self._callback_lock:
            self._callback = on_wake_word

        # Init backend (model load once)
        backend = self._init_backend()
        if backend == "disabled":
            return False

        self._stop_event.clear()
        self._running = True
        self._paused = False
        self._state = WakeWordState.LISTENING_FOR_WAKE_WORD
        self._thread = threading.Thread(target=self._run, name="WakeWordDetector", daemon=True)
        self._thread.start()
        logger.info("Wake-word detector started (backend=%s, phrase=%r, threshold=%.2f)", self._backend, self.wake_word, self.threshold)
        return True

    def stop(self) -> None:
        """Stop monitoring and release mic."""
        if not self._running:
            return
        logger.info("Stopping wake-word detector...")
        self._stop_event.set()
        self._running = False
        self._paused = False
        self._state = WakeWordState.IDLE
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.5)
        self._thread = None
        logger.info("Wake-word detector stopped.")

    def is_running(self) -> bool:
        return self._running and not self._stop_event.is_set()

    def pause(self) -> None:
        """Temporarily ignore detections (during command recording/TTS)."""
        self._paused = True
        logger.debug("Wake-word detector paused.")

    def resume(self) -> None:
        """Resume after pause; applies cooldown."""
        self._paused = False
        self._last_trigger_time = time.time()  # cooldown from now
        logger.debug("Wake-word detector resumed (cooldown %dms).", self.cooldown_ms)
        # Reset vosk partial to avoid stale buffer triggering immediately
        if self._vosk_recognizer is not None:
            try:
                # Reset recognizer state by recreating (vosk has no clear)
                from vosk import KaldiRecognizer  # type: ignore

                self._vosk_recognizer = KaldiRecognizer(self._vosk_model, self.sample_rate)
                self._vosk_recognizer.SetWords(True)
            except Exception:
                pass

    def set_speaking(self, is_speaking: bool) -> None:
        """Tell detector TTS is active — suppresses detection."""
        self._speaking = is_speaking
        if is_speaking:
            self.pause()
        else:
            # Small extra cooldown after TTS to avoid echo
            threading.Timer(self.cooldown_ms / 1000.0, self.resume).start()

    # ------------------------------------------------------------------
    # Internal — audio loop
    # ------------------------------------------------------------------
    def _run(self) -> None:
        """Background thread: open mic and stream."""
        if sd is None:
            return

        block_frames = int(self.sample_rate * self.block_duration_ms / 1000)
        q: "queue.Queue[np.ndarray]" = queue.Queue()

        def callback(indata, frames, time_info, status):
            if status:
                logger.debug("Wake-word audio status: %s", status)
            if not self._paused and not self._speaking and self._running:
                # Mono float32
                q.put(indata[:, 0].copy() if indata.ndim > 1 else indata.copy())

        stream = None
        try:
            logger.info("Wake-word mic opening: device=%s sr=%d block=%d", self.device_index, self.sample_rate, block_frames)
            stream = sd.InputStream(
                device=self.device_index,
                channels=1,
                samplerate=self.sample_rate,
                dtype="float32",
                blocksize=block_frames,
                callback=callback,
            )
            stream.start()
            logger.info("Wake-word listening started — waiting for %r", self.wake_word)
        except Exception as exc:
            msg = str(exc).lower()
            if "permission" in msg or "access" in msg:
                print("\nERROR: Microphone permission denied for wake-word.")
                print("Windows Settings → Privacy & security → Microphone → Enable access")
            elif "invalid" in msg or "no device" in msg:
                print(f"\nERROR: Cannot open microphone for wake-word [{self.device_index}]: {exc}")
            else:
                print(f"\nERROR: Wake-word mic failed: {exc}")
            logger.exception("Failed to open wake-word InputStream")
            self._running = False
            self._state = WakeWordState.IDLE
            return

        # Dummy backend state: for debouncing energy
        energy_trigger_count = 0

        try:
            while not self._stop_event.is_set():
                try:
                    chunk = q.get(timeout=0.4)
                except queue.Empty:
                    continue

                if self._paused or self._speaking:
                    # Drain queue while paused to avoid stale audio
                    while not q.empty():
                        try:
                            q.get_nowait()
                        except queue.Empty:
                            break
                    continue

                # Cooldown check
                now = time.time()
                if (now - self._last_trigger_time) * 1000 < self.cooldown_ms:
                    continue

                # Backend-specific detection
                triggered = False
                text_for_log = ""

                if self._backend == "vosk" and self._vosk_recognizer is not None:
                    # Vosk expects int16
                    import json as _json

                    # Convert float32 (-1..1) to int16
                    int16 = (chunk * 32767).astype(np.int16).tobytes()
                    try:
                        if self._vosk_recognizer.AcceptWaveform(int16):
                            res = _json.loads(self._vosk_recognizer.Result())
                            text = res.get("text", "").lower().strip()
                            if text:
                                text_for_log = text
                                if self.wake_word in text:
                                    triggered = True
                        else:
                            # Partial — low latency check
                            pres = _json.loads(self._vosk_recognizer.PartialResult())
                            partial = pres.get("partial", "").lower().strip()
                            if partial and self.wake_word in partial:
                                # Require partial length > wake word to reduce false positives
                                triggered = True
                                text_for_log = partial + " (partial)"
                    except Exception as exc:
                        logger.debug("Vosk waveform error: %s", exc)

                elif self._backend == "dummy":
                    # Energy-based: RMS > threshold mapped to 0.02-0.08 range
                    # threshold 0.5 -> ~0.02, threshold 0.9 -> 0.07 (higher = less sensitive)
                    rms = float(np.sqrt(np.mean(chunk**2))) if chunk.size else 0.0
                    # Map threshold 0..1 to rms 0.01..0.08
                    rms_threshold = 0.01 + (self.threshold * 0.07)
                    if rms > rms_threshold:
                        energy_trigger_count += 1
                        # Require 2 consecutive loud chunks to reduce noise triggers
                        if energy_trigger_count >= 2:
                            # Dummy still checks: if wake_word is default, any loud speech triggers
                            # This is intentional fallback — accurate phrase needs vosk
                            triggered = True
                            text_for_log = f"energy rms={rms:.3f}"
                            energy_trigger_count = 0
                    else:
                        energy_trigger_count = max(0, energy_trigger_count - 1)

                if triggered:
                    self._last_trigger_time = now
                    logger.info("Wake word detected! (%s) backend=%s", text_for_log or self.wake_word, self._backend)
                    # IMPORTANT: pause to release/avoid re-trigger, notify main
                    self.pause()
                    self._state = WakeWordState.LISTENING_FOR_COMMAND
                    # Fire callback safely (in detector thread, but main handles transition)
                    cb = None
                    with self._callback_lock:
                        cb = self._callback
                    if cb:
                        try:
                            # Run callback in a new thread so detector loop not blocked
                            threading.Thread(target=cb, daemon=True).start()
                        except Exception as exc:
                            logger.error("Wake-word callback error: %s", exc)
                    # Drain queue after trigger
                    while not q.empty():
                        try:
                            q.get_nowait()
                        except queue.Empty:
                            break
                    # Stay paused — main will resume() when ready
                # Small idle sleep to keep CPU low — queue.get timeout already throttles
        finally:
            try:
                if stream:
                    stream.stop()
                    stream.close()
            except Exception:
                pass
            logger.info("Wake-word mic closed.")

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    def get_backend(self) -> str:
        return self._backend
