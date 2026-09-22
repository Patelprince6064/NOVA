"""Nova Voice Engine — Phase 1+2 entry point.

Flow:
    Load config -> Detect microphone -> Load Whisper model -> Init TTS -> Push-to-talk loop
    Record -> Transcribe -> Generate response -> Speak

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
from app.tts.speaker import Speaker

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
# Simple Phase 2 response system (local, no LLM)
# ---------------------------------------------------------------------------

def generate_response(text: str) -> str:
    """Map recognized text to a simple spoken response."""
    if not text or not text.strip():
        return ""
    low = text.strip().lower()

    # Priority: most specific first
    if "how are you" in low:
        return "I'm doing great. I'm ready for your next command."
    if "hello" in low:
        return "Hello! I'm Nova."
    # 'hi' as standalone word — avoid matching inside other words too greedily
    # but keep it simple: check for hi variants
    if low == "hi" or low.startswith("hi ") or low.startswith("hi,") or " hi " in f" {low} " or low.endswith(" hi"):
        return "Hi! I'm ready."
    if "test" in low:
        return "Voice system is working correctly."
    return f"I heard you say: {text.strip()}"


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
    if sd is not None:
        try:
            default_input = sd.default.device[0]  # (input, output)
            for m in mics:
                if m.index == default_input:
                    return m
        except Exception:
            pass
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
    """Record mono float32 audio until user presses ENTER or max duration."""
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
        audio_queue.put(indata[:, 0].copy())

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

    def auto_stop():
        if not stop_event.is_set():
            print(f"\n⏱  Maximum duration ({max_seconds}s) reached — stopping.")
            stop_event.set()

    timer = threading.Timer(max_seconds, auto_stop)
    timer.start()

    try:
        input()
        if not stop_event.is_set():
            stop_event.set()
    except (KeyboardInterrupt, EOFError):
        stop_event.set()
        error_holder.append("interrupted")
    finally:
        timer.cancel()
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

def print_banner(config: Config, selected: Optional[MicInfo], speaker: Optional[Speaker] = None) -> None:
    mic_name = selected.name if selected else "None"
    tts_status = "DISABLED"
    if speaker is not None:
        if speaker.is_available:
            tts_status = "READY"
        elif not speaker.is_enabled:
            tts_status = "DISABLED"
        else:
            tts_status = "UNAVAILABLE"

    print("=" * 32)
    print("        NOVA VOICE ENGINE")
    print("=" * 32)
    print(f"\n🎤 Microphone: {mic_name} — READY")
    print(f"📝 Speech recognition: READY (model={config.whisper_model})")
    print(f"🔊 Voice output: {tts_status} (rate={config.tts_rate} vol={config.tts_volume})")
    print(f"Sample Rate: {config.sample_rate} Hz")
    if speaker and speaker.is_available:
        try:
            vid = speaker._engine.getProperty("voice") if speaker._engine else ""
            print(f"TTS Voice: {vid}")
        except Exception:
            pass
    print("\nStatus: READY")
    print("\nPress ENTER to speak.")
    print("Press Q + ENTER to quit.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("Nova Voice Engine starting...")

    config = Config.load()

    if sd is None:
        print("ERROR: Required package 'sounddevice' is not installed.")
        print("Install dependencies: pip install -r requirements.txt")
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

    # ---- Load Whisper model once ----
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

    # ---- Initialize TTS (once, non-fatal) ----
    speaker = Speaker(
        enabled=config.tts_enabled,
        rate=config.tts_rate,
        volume=config.tts_volume,
        voice=config.tts_voice,
    )
    tts_ok = speaker.initialize()

    if tts_ok:
        print("Text-to-speech: Ready\n")
        # List voices for diagnostics (INFO level also logged)
        try:
            speaker.print_voices()
        except Exception:
            pass
        print('Nova:\n"Voice system initialized."\n')
        logger.info("Speaking startup phrase.")
        try:
            speaker.speak("Voice system initialized.")
        except Exception as exc:
            logger.warning("Startup TTS speak failed: %s", exc)
    else:
        if config.tts_enabled:
            print("WARNING:\nText-to-speech is unavailable.")
            print("Voice input will continue to work.\n")
            logger.warning("TTS unavailable — continuing with STT only.")
        else:
            print("Text-to-speech: Disabled (TTS_ENABLED=false)\n")
            logger.info("TTS disabled by config.")

    # ---- Main loop ----
    print_banner(config, selected, speaker)

    try:
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

            print("\nPress ENTER again to stop recording.")
            audio = record_until_enter(
                device_index=selected.index,
                sample_rate=config.sample_rate,
                max_seconds=config.max_recording_seconds,
            )

            if audio is None:
                print("\nStatus: READY")
                continue

            if audio.size == 0:
                print("\n⚠️  No speech detected. Try again.")
                print("\nStatus: READY")
                continue

            rms = float(np.sqrt(np.mean(audio**2))) if audio.size > 0 else 0.0
            duration = audio.size / config.sample_rate
            if duration < 0.3:
                print("\n⚠️  Recording too short. Try speaking a bit longer.")
                print("\nStatus: READY")
                del audio
                continue
            if rms < 0.003:
                print("\n⚠️  No speech detected (silence). Try again.")
                logger.info("Silence detected (rms=%.5f) — skipping transcription.", rms)
                print("\nStatus: READY")
                del audio
                continue

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
                del audio

            if not text or not text.strip():
                print("⚠️  No speech detected. Try again.")
                print("\nStatus: READY")
                continue
            else:
                print("📝 You said:\n")
                print(f'  "{text}"')

            # ---- Phase 2: generate & speak response ----
            response = generate_response(text)
            if response:
                print("\n🔊 Nova:\n")
                print(f'  "{response}"')
                logger.info("Generated response: %r", response[:120])
                if speaker.is_available:
                    # Time the TTS for performance awareness
                    t0 = time.perf_counter()
                    ok = speaker.speak(response)
                    dt = time.perf_counter() - t0
                    logger.info("TTS speak %s in %.2fs", "ok" if ok else "failed", dt)
                    if not ok:
                        print("(TTS failed — response shown above)")
                else:
                    logger.debug("TTS not available — response shown only.")
            else:
                logger.debug("Empty response — not speaking.")

            print("\nStatus: READY")
    finally:
        # ---- Clean shutdown ----
        logger.info("Shutting down Nova...")
        if 'speaker' in locals() and speaker is not None:
            try:
                speaker.stop()
                speaker.shutdown()
            except Exception as exc:
                logger.warning("Error during TTS shutdown: %s", exc)
        logger.info("Nova Voice Engine stopped.")
        print("\nNova stopped.")


if __name__ == "__main__":
    main()
