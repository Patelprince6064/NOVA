"""Nova Voice Engine — Phase 1 entry point.

Flow:
    Load config -> Detect microphone -> Load Whisper model -> Push-to-talk loop.

Privacy: audio stays in RAM, never written to disk.
"""

import logging
import sys
import time
import threading
import queue
from dataclasses import dataclass
from typing import Optional, List

import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None  # handled at runtime with helpful error

from app.config import Config
from app.speech.transcriber import Transcriber

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Microphone helpers
# ---------------------------------------------------------------------------


@dataclass
class MicInfo:
    index: int
    name: str
    channels: int
    samplerate: float


def list_microphones() -> List[MicInfo]:
    """Return available input devices."""
    if sd is None:
        return []
    try:
        devices = sd.query_devices()
    except Exception as exc:
        logger.error("Failed to query audio devices: %s", exc)
        return []

    mics: List[MicInfo] = []
    for idx, dev in enumerate(devices):
        # dev is a dict-like object
        try:
            if dev.get("max_input_channels", 0) > 0:
                mics.append(
                    MicInfo(
                        index=idx,
                        name=dev.get("name", f"Device {idx}"),
                        channels=int(dev.get("max_input_channels", 1)),
                        samplerate=float(dev.get("default_samplerate", 44100)),
                    )
                )
        except Exception:
            continue
    return mics


def select_microphone(mics: List[MicInfo]) -> Optional[MicInfo]:
    """Select microphone: auto-select if only one, otherwise pick default."""
    if not mics:
        return None
    # Prefer the default input device if we can identify it
    if sd is not None:
        try:
            default_input = sd.default.device[0]  # (input, output)
            for m in mics:
                if m.index == default_input:
                    return m
        except Exception:
            pass
    # Fallback: first device
    return mics[0]


def print_microphone_info(mics: List[MicInfo], selected: Optional[MicInfo]) -> None:
    print("\nNova Voice Engine")
    print("-----------------")
    print("\nAvailable microphones:\n")
    if not mics:
        print("  (none found)")
    else:
        for m in mics:
            marker = " *" if selected and m.index == selected.index else ""
            print(f"  [{m.index}] {m.name} ({m.channels}ch, {m.samplerate:.0f} Hz){marker}")
    print()
    if selected:
        print(f"Selected microphone: [{selected.index}] {selected.name}")
    print()


# ---------------------------------------------------------------------------
# Recording — push-to-talk with background stream
# ---------------------------------------------------------------------------

def record_until_enter(
    device_index: int,
    sample_rate: int,
    max_seconds: int,
) -> Optional[np.ndarray]:
    """Record mono float32 audio until user presses ENTER or max duration.

    Uses a background InputStream that fills a queue; the main thread waits
    for ENTER in a blocking input() call while a timer enforces max duration.

    Returns:
        1-D float32 numpy array, or None if recording failed/cancelled.
    """
    if sd is None:
        print("ERROR: sounddevice is not installed. Run: pip install -r requirements.txt")
        return None

    audio_queue: "queue.Queue[np.ndarray]" = queue.Queue()
    stop_event = threading.Event()
    error_holder: List[str] = []

    def callback(indata, frames, time_info, status):
        if status:
            logger.warning("Audio callback status: %s", status)
        if stop_event.is_set():
            return
        # indata shape: (frames, channels) -> take first channel for mono
        audio_queue.put(indata[:, 0].copy())

    # Start stream
    try:
        stream = sd.InputStream(
            device=device_index,
            channels=1,
            samplerate=sample_rate,
            dtype="float32",
            callback=callback,
        )
        stream.start()
    except Exception as exc:
        msg = str(exc).lower()
        if "invalid" in msg or "no device" in msg:
            print(f"\nERROR: Cannot open microphone [{device_index}]: {exc}")
        elif "permission" in msg or "access" in msg:
            print("\nERROR: Microphone permission denied.")
            print("On Windows: Settings > Privacy & security > Microphone")
            print("  -> Enable 'Microphone access' and 'Let apps access your microphone'.")
            print(f"Details: {exc}")
        else:
            print(f"\nERROR: Failed to start recording: {exc}")
        logger.exception("Failed to start InputStream")
        return None

    print("\n🎤 LISTENING...")
    print("Speak now.")
    print(f"(Recording up to {max_seconds}s — press ENTER to stop)\n")
    logger.info("Recording started on device %d sr=%d", device_index, sample_rate)

    # Auto-stop timer
    def auto_stop():
        if not stop_event.is_set():
            print(f"\n⏱  Maximum duration ({max_seconds}s) reached — stopping.")
            stop_event.set()

    timer = threading.Timer(max_seconds, auto_stop)
    timer.start()

    # Wait for ENTER (blocking). User presses ENTER to stop.
    try:
        input()  # second ENTER
        if not stop_event.is_set():
            stop_event.set()
    except (KeyboardInterrupt, EOFError):
        stop_event.set()
        error_holder.append("interrupted")
    finally:
        timer.cancel()
        # Give callback a moment to finish
        time.sleep(0.15)
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass

    if error_holder and error_holder[0] == "interrupted":
        print("\nRecording cancelled.")
        logger.info("Recording interrupted by user.")
        return None

    # Drain queue
    chunks: List[np.ndarray] = []
    while not audio_queue.empty():
        try:
            chunks.append(audio_queue.get_nowait())
        except queue.Empty:
            break

    if not chunks:
        print("No audio captured.")
        logger.warning("No audio chunks captured.")
        return np.zeros(0, dtype=np.float32)

    audio = np.concatenate(chunks, axis=0).astype(np.float32)
    duration = len(audio) / sample_rate
    logger.info("Recording stopped: samples=%d duration=%.2fs", len(audio), duration)
    print(f"\n⏹  Recording stopped — captured {duration:.1f}s of audio.")
    return audio


# ---------------------------------------------------------------------------
# Banner helpers
# ---------------------------------------------------------------------------

def print_banner(config: Config, selected: Optional[MicInfo]) -> None:
    mic_name = selected.name if selected else "None"
    print("=" * 32)
    print("        NOVA VOICE ENGINE")
    print("=" * 32)
    print(f"\nMicrophone: {mic_name}")
    print(f"Model: {config.whisper_model}")
    print(f"Sample Rate: {config.sample_rate} Hz")
    print(f"Max Recording: {config.max_recording_seconds}s")
    print("\nStatus: READY")
    print("\nPress ENTER to speak.")
    print("Press Q + ENTER to quit.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("Nova Voice Engine starting...")

    # ---- Config ----
    config = Config.load()

    # ---- Check sounddevice ----
    if sd is None:
        print("ERROR: Required package 'sounddevice' is not installed.")
        print("Install dependencies: pip install -r requirements.txt")
        print("On Windows you may also need to install audio drivers.")
        sys.exit(1)

    # ---- Microphone detection ----
    mics = list_microphones()
    selected = select_microphone(mics)
    print_microphone_info(mics, selected)

    if not mics or selected is None:
        print("ERROR: No microphone detected.")
        print("Please connect a microphone and restart Nova.")
        logger.error("No microphone found — exiting.")
        sys.exit(1)

    logger.info("Microphone selected: [%d] %s", selected.index, selected.name)

    # ---- Load model once ----
    transcriber = Transcriber(
        model_name=config.whisper_model,
        device=config.whisper_device,
        compute_type=config.whisper_compute_type,
        language=config.language,
    )
    try:
        transcriber.load()
    except RuntimeError as exc:
        print(f"\nERROR: {exc}")
        logger.error("Model loading failed — exiting.")
        sys.exit(1)
    except Exception as exc:
        print(f"\nERROR: Unexpected error loading model: {exc}")
        logger.exception("Unexpected model load error")
        sys.exit(1)

    # ---- Main loop ----
    print_banner(config, selected)

    while True:
        print("\n" + "-" * 32)
        try:
            user_input = input("\nPress ENTER to start recording (Q to quit): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting Nova. Goodbye!")
            break

        if user_input.lower() == "q":
            print("\nExiting Nova. Goodbye!")
            logger.info("User requested quit.")
            break

        # Any other input (including empty ENTER) starts recording
        if user_input != "" and user_input.lower() != "":
            # If user typed something else, treat 'q' already handled, otherwise
            # start recording anyway — be permissive for Phase 1.
            pass

        print("\nPress ENTER again to stop recording.")
        audio = record_until_enter(
            device_index=selected.index,
            sample_rate=config.sample_rate,
            max_seconds=config.max_recording_seconds,
        )

        if audio is None:
            # Interrupted or device error — return to ready state
            print("\nStatus: READY")
            continue

        if audio.size == 0:
            print("\n⚠️  No speech detected. Try again.")
            print("\nStatus: READY")
            continue

        # Silence check before transcription
        rms = float(np.sqrt(np.mean(audio**2))) if audio.size > 0 else 0.0
        duration = audio.size / config.sample_rate
        if duration < 0.3:
            print("\n⚠️  Recording too short. Try speaking a bit longer.")
            print("\nStatus: READY")
            continue
        if rms < 0.003:
            print("\n⚠️  No speech detected (silence). Try again.")
            logger.info("Silence detected (rms=%.5f) — skipping transcription.", rms)
            print("\nStatus: READY")
            continue

        # Transcribe
        print("\nTranscribing...\n")
        logger.info("Starting transcription...")
        try:
            text = transcriber.transcribe(audio, sample_rate=config.sample_rate)
        except RuntimeError as exc:
            print(f"\n❌ Unable to transcribe audio.\nPlease try again.\nDetails: {exc}")
            logger.error("Transcription failed: %s", exc)
            print("\nStatus: READY")
            continue
        except Exception as exc:
            print(f"\n❌ Unexpected transcription error: {exc}\nPlease try again.")
            logger.exception("Unexpected transcription error")
            print("\nStatus: READY")
            continue
        finally:
            # Privacy: release audio buffer immediately
            del audio

        if not text or not text.strip():
            print("⚠️  No speech detected. Try again.")
        else:
            print("📝 You said:\n")
            print(f'  "{text}"')

        print("\nStatus: READY")

    logger.info("Nova Voice Engine stopped.")
    print("\nNova stopped.")


if __name__ == "__main__":
    main()
