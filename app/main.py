"""Nova Voice Engine — Phase 5 natural language + PC control entry point.

Flow hands-free:
    Config -> Mic -> Whisper -> TTS -> WakeWordDetector -> PCController -> AI Interpreter
    -> LISTENING_FOR_WAKE_WORD --"Hey Nova"--> LISTENING_FOR_COMMAND
    -> PROCESSING (Whisper) -> Fast local router -> LLM (if needed, validated) -> PC action -> SPEAKING -> back

Privacy: audio RAM only, LLM only gets transcribed text when needed, no shell/code exec, validated actions only.
"""

import argparse
import logging
import sys
import time
import threading
import queue
from dataclasses import dataclass
from typing import Optional, List

import numpy as np

# Ensure UTF-8 output on Windows (emoji)
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    import sounddevice as sd
except ImportError:
    sd = None  # handled at runtime

from app.config import Config
from app.speech.transcriber import Transcriber
from app.tts.speaker import Speaker
from app.wakeword.detector import WakeWordDetector, WakeWordState
from app.pc.controller import PCController
from app.pc.actions import handle_command, execute_structured_action
try:
    from app.ai.interpreter import CommandInterpreter
except ImportError:
    CommandInterpreter = None  # type: ignore

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
# Response system (Phase 2 local, no LLM)
# ---------------------------------------------------------------------------

def generate_response(text: str) -> str:
    if not text or not text.strip():
        return ""
    low = text.strip().lower()
    if "how are you" in low:
        return "I'm doing great. I'm ready for your next command."
    if "hello" in low:
        return "Hello! I'm Nova."
    if low == "hi" or low.startswith("hi ") or low.startswith("hi,") or " hi " in f" {low} " or low.endswith(" hi"):
        return "Hi! I'm ready."
    if "test" in low:
        return "Voice system is working correctly."
    return f"I heard you say: {text.strip()}"


# ---------------------------------------------------------------------------
# Phase 5: Natural language routing helper (fast local + LLM fallback)
# ---------------------------------------------------------------------------

def route_pc_command(text: str, controller: PCController, interpreter, config) -> str:
    """Route via fast local router, fallback to LLM if needed.

    Architecture:
        text -> fast handle_command -> if known (PC or friendly) -> done
        else if LLM enabled & available -> interpreter -> validate -> execute -> response
        else -> original unknown response

    Returns response string to speak.
    """
    if not text or not text.strip():
        return ""
    # If PC control disabled, fall back to friendly responses only
    if not config.pc_control_enabled:
        return generate_response(text)

    # Fast local path — executes PC action if matched
    try:
        handled, fast_resp = handle_command(text, controller)
    except Exception as exc:
        logger.exception("Fast router failed: %s", exc)
        handled, fast_resp = False, "I couldn't understand that command."

    # Cases where fast router succeeded (PC action or friendly hello)
    friendly_set = {
        "Hello! I'm Nova.",
        "Hi! I'm ready.",
        "I'm doing great. I'm ready for your next command.",
        "Voice system is working correctly.",
    }
    if handled:
        # PC action executed locally — immediate response, no LLM needed
        logger.info("Fast path: PC action executed -> %r", fast_resp)
        return fast_resp
    if fast_resp in friendly_set:
        logger.info("Fast path: friendly response -> %r", fast_resp)
        return fast_resp
    if fast_resp == "I can handle one basic action at a time right now.":
        logger.info("Fast path: multi-step rejected")
        return fast_resp
    # If fast_resp is "I can't perform..." -> unknown/ambiguous, try LLM
    if fast_resp == "I can't perform that action yet.":
        if interpreter is not None and interpreter.is_available():
            logger.info("Fast path unknown -> trying LLM interpreter")
            try:
                validated, err = interpreter.interpret(text)
                if validated is not None:
                    # Dispatch validated action to PC controller
                    # validated already includes unsupported/clarification meta
                    if validated.get("action") in ("unsupported", "clarification"):
                        # For these meta actions, don't execute PC, just respond
                        if validated["action"] == "unsupported":
                            return "I can't perform that action yet."
                        else:
                            return validated.get("message", "Which option should I use?")
                    ok, msg = execute_structured_action(validated, controller)
                    logger.info("LLM path executed: %r -> %r", validated, msg)
                    return msg
                else:
                    logger.info("LLM interpreted no action (err=%s), returning fast response", err)
                    if err and "timeout" in err.lower():
                        return "I couldn't process that command right now."
                    # For validation failures, treat as unknown
                    if err and "Validation" in err:
                        return "I couldn't understand that command."
                    # LLM unavailable / empty -> keep fast response but generic
                    return "I couldn't understand that command." if "LLM not configured" in err else fast_resp
            except Exception as exc:
                logger.warning("LLM route error: %s", exc)
                return "I couldn't process that command right now."
        else:
            # LLM disabled or no key -> keep fast path response (handles local commands still work)
            logger.debug("LLM not available, returning fast path unknown")
            return fast_resp

    # Fallback: return fast_resp for any other case (including empty)
    return fast_resp


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
                mics.append(MicInfo(index=idx, name=dev.get("name", f"Device {idx}"), channels=int(dev.get("max_input_channels", 1)), samplerate=float(dev.get("default_samplerate", 44100))))
        except Exception:
            continue
    return mics


def select_microphone(mics: List[MicInfo]) -> Optional[MicInfo]:
    if not mics:
        return None
    if sd is not None:
        try:
            default_input = sd.default.device[0]
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
# Manual recording (Phase 1 compat — push-to-talk)
# ---------------------------------------------------------------------------

def record_until_enter(device_index: int, sample_rate: int, max_seconds: int) -> Optional[np.ndarray]:
    if sd is None:
        print("ERROR: sounddevice not installed. Run: pip install -r requirements.txt")
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
        stream = sd.InputStream(device=device_index, channels=1, samplerate=sample_rate, dtype="float32", callback=callback)
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
# Hands-free command recording (after wake word)
# ---------------------------------------------------------------------------

def record_command_auto(
    device_index: int,
    sample_rate: int,
    timeout_seconds: int,
    silence_threshold: float = 0.015,
    min_speech_duration: float = 0.3,
) -> Optional[np.ndarray]:
    """Record command after wake word, with timeout and silence handling.

    Records up to timeout_seconds. Uses simple VAD: if speech starts, wait for
    ~1.2s of continuous silence after speech to stop early. If no speech within
    timeout, returns empty (timeout).
    """
    if sd is None:
        print("ERROR: sounddevice not installed.")
        return None

    audio_queue: "queue.Queue[np.ndarray]" = queue.Queue()
    stop_event = threading.Event()

    def callback(indata, frames, time_info, status):
        if status:
            logger.debug("Command audio status: %s", status)
        if stop_event.is_set():
            return
        audio_queue.put(indata[:, 0].copy())

    try:
        stream = sd.InputStream(device=device_index, channels=1, samplerate=sample_rate, dtype="float32", callback=callback)
        stream.start()
    except Exception as exc:
        msg = str(exc).lower()
        if "permission" in msg or "access" in msg:
            print("\nERROR: Microphone permission denied during command.")
            print("Windows Settings → Privacy & security → Microphone → Enable access")
        else:
            print(f"\nERROR: Failed to start command recording: {exc}")
        logger.exception("Failed to start command InputStream")
        return None

    print("\n🎤 LISTENING...")
    print("Speak now (say your command).\n")
    logger.info("Command recording started: timeout=%ds sr=%d", timeout_seconds, sample_rate)

    # Wake sound
    # (played by caller before this, but keep log)

    start_time = time.time()
    chunks: List[np.ndarray] = []
    has_speech = False
    speech_start_time: Optional[float] = None
    silence_since = 0.0
    # Collect stats for VAD
    last_rms_log = 0.0

    # Non-blocking collection loop with timeout
    try:
        while True:
            elapsed = time.time() - start_time
            if elapsed >= timeout_seconds:
                logger.info("Command timeout after %.1fs", elapsed)
                break

            try:
                chunk = audio_queue.get(timeout=0.12)
                chunks.append(chunk)
                # Simple VAD per chunk
                rms = float(np.sqrt(np.mean(chunk**2))) if chunk.size else 0.0
                # Log occasionally
                if time.time() - last_rms_log > 0.8:
                    logger.debug("Command RMS: %.4f thr=%.3f has_speech=%s", rms, silence_threshold, has_speech)
                    last_rms_log = time.time()

                is_speech = rms > silence_threshold
                if is_speech:
                    if not has_speech:
                        has_speech = True
                        speech_start_time = time.time()
                        logger.info("Speech started (rms=%.4f)", rms)
                    silence_since = 0.0
                else:
                    if has_speech:
                        silence_since += 0.12  # approx chunk duration
                        # If we have had 1.2s of continuous silence after speech started and at least 0.6s speech, stop early
                        if silence_since >= 1.2:
                            # Ensure we captured at least 0.6s of audio total with speech
                            total_dur = sum(len(c) for c in chunks) / sample_rate
                            if total_dur >= 0.6:
                                logger.info("Silence after speech (%.1fs) — stopping early", silence_since)
                                break
                # Drain extra queued chunks quickly
                while not audio_queue.empty():
                    try:
                        extra = audio_queue.get_nowait()
                        chunks.append(extra)
                    except queue.Empty:
                        break
            except queue.Empty:
                # No chunk this interval — count as silence if we had speech
                if has_speech:
                    silence_since += 0.12
                    if silence_since >= 1.2:
                        total_dur = sum(len(c) for c in chunks) / sample_rate if chunks else 0
                        if total_dur >= 0.6:
                            logger.info("Silence timeout after speech — stopping")
                            break
                continue
    except (KeyboardInterrupt, EOFError):
        print("\nCommand cancelled.")
        logger.info("Command recording interrupted.")
        try:
            stream.stop(); stream.close()
        except Exception:
            pass
        return None
    finally:
        stop_event.set()
        time.sleep(0.08)
        try:
            stream.stop(); stream.close()
        except Exception:
            pass
        # Drain remaining
        while not audio_queue.empty():
            try:
                chunks.append(audio_queue.get_nowait())
            except queue.Empty:
                break

    if not chunks:
        logger.info("Command: no audio captured (timeout)")
        return np.zeros(0, dtype=np.float32)

    audio = np.concatenate(chunks, axis=0).astype(np.float32)
    duration = len(audio) / sample_rate
    rms_total = float(np.sqrt(np.mean(audio**2))) if audio.size else 0.0
    logger.info("Command recording finished: dur=%.2fs rms=%.4f has_speech=%s", duration, rms_total, has_speech)
    print(f"⏹  Captured {duration:.1f}s of audio.")
    # If duration too short and no speech, treat as silence
    if duration < min_speech_duration and rms_total < silence_threshold:
        logger.info("Command too short/silent — will be treated as timeout.")
    return audio


def play_wake_sound(enabled: bool) -> None:
    """Play short beep on wake word if enabled."""
    if not enabled:
        return
    try:
        # Windows native beep
        import winsound  # type: ignore

        # Very short, non-annoying
        winsound.Beep(1000, 180)
        logger.debug("Wake sound played (winsound)")
    except Exception:
        # Fallback: console bell visual
        print("🔔")
        logger.debug("Wake sound fallback (print bell)")


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

def print_banner(config: Config, selected: Optional[MicInfo], speaker: Optional[Speaker], mode: str) -> None:
    mic_name = selected.name if selected else "None"
    tts_status = "DISABLED"
    if speaker is not None:
        if speaker.is_available:
            tts_status = "READY"
        elif not speaker.is_enabled:
            tts_status = "DISABLED"
        else:
            tts_status = "UNAVAILABLE"
    wake_status = "DISABLED" if not config.wake_word_enabled else f"READY (\"{config.wake_word}\")"
    pc_status = "ENABLED" if config.pc_control_enabled else "DISABLED"
    llm_status = "ENABLED" if config.llm_enabled and config.llm_api_key else ("DISABLED (no key)" if config.llm_enabled else "DISABLED")
    print("=" * 32)
    print("        NOVA VOICE ENGINE")
    print("=" * 32)
    print(f"\n🎤 Microphone: {mic_name} — READY")
    print(f"📝 Speech recognition: READY (model={config.whisper_model})")
    print(f"🔊 Voice output: {tts_status} (rate={config.tts_rate} vol={config.tts_volume})")
    print(f"👂 Wake word: {wake_status}")
    if config.wake_word_enabled:
        print(f"   Threshold: {config.wake_word_threshold}  Cooldown: {config.wake_word_cooldown_ms}ms  Timeout: {config.command_timeout_seconds}s")
    print(f"🖥️  PC control: {pc_status} (scroll={config.default_scroll_amount} timeout={config.action_timeout_seconds}s)")
    print(f"🧠 Natural language: {llm_status} (provider={config.llm_provider} model={config.llm_model or 'default'})")
    print(f"Sample Rate: {config.sample_rate} Hz")
    print(f"Mode: {mode}")
    print("\nStatus: READY")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Nova Voice Engine", add_help=False)
    parser.add_argument("--manual", action="store_true", help="Force manual ENTER mode (disable wake-word)")
    parser.add_argument("--help", action="store_true", help="Show help")
    args, _unknown = parser.parse_known_args()
    if args.help:
        print("Nova Voice Engine — Phase 5")
        print("  python -m app.main          # hands-free wake-word + natural language (default)")
        print("  python -m app.main --manual # manual ENTER mode")
        print("  python -m app.main --help   # this help")
        print("")
        print("Examples: 'open Brave' | 'Could you launch my Brave browser?'")
        print("  'open YouTube' | 'Take me to YouTube' | 'type Hello World' | 'press Control C'")
        sys.exit(0)

    logger.info("Nova Voice Engine starting...")

    config = Config.load()

    # Override wake-word via manual flag
    use_wake_word = config.wake_word_enabled and not args.manual
    mode_str = "HANDS-FREE (wake-word)" if use_wake_word else "MANUAL (press ENTER)"
    if args.manual and config.wake_word_enabled:
        logger.info("Manual mode forced via --manual — wake-word disabled for this run.")

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
        print("If microphone is connected, check Windows Settings → Privacy & security → Microphone")
        logger.error("No microphone found — exiting.")
        sys.exit(1)

    logger.info("Microphone selected: [%d] %s", selected.index, selected.name)

    # ---- Load Whisper model once ----
    transcriber = Transcriber(model_name=config.whisper_model, device=config.whisper_device, compute_type=config.whisper_compute_type, language=config.language)
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
    speaker = Speaker(enabled=config.tts_enabled, rate=config.tts_rate, volume=config.tts_volume, voice=config.tts_voice)
    tts_ok = speaker.initialize()

    if tts_ok:
        print("Text-to-speech: Ready\n")
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

    # ---- Initialize PC controller (Phase 4) ----
    pc_controller = PCController(
        enabled=config.pc_control_enabled,
        default_scroll=config.default_scroll_amount,
        action_timeout=config.action_timeout_seconds,
    )
    if config.pc_control_enabled:
        print(f"PC control: Enabled (scroll={config.default_scroll_amount})\n")
        # Log foreground window for diagnostics
        try:
            fg = pc_controller.get_foreground_window()
            if fg:
                logger.info("Foreground window at startup: %r", fg)
                print(f"Current window: {fg}\n")
        except Exception:
            pass
    else:
        print("PC control: Disabled (PC_CONTROL_ENABLED=false)\n")
        logger.info("PC control disabled by config.")

    # ---- Initialize AI interpreter (Phase 5) ----
    interpreter = None
    if config.llm_enabled:
        if CommandInterpreter is None:
            print("WARNING: LLM enabled but ai module not available.\n")
            logger.warning("CommandInterpreter import failed")
        elif not config.llm_api_key:
            print("WARNING: LLM_ENABLED=true but LLM_API_KEY is empty — LLM will be unavailable.")
            print("Local commands will still work.\n")
            logger.warning("LLM enabled but no API key")
            try:
                interpreter = CommandInterpreter(config)
            except Exception as exc:
                logger.warning("Failed to init interpreter without key: %s", exc)
        else:
            try:
                interpreter = CommandInterpreter(config)
                if interpreter.is_available():
                    print(f"Natural language: Enabled (provider={config.llm_provider} model={config.llm_model or 'default'})\n")
                    logger.info("LLM interpreter available: %s %s", config.llm_provider, config.llm_model or "default")
                else:
                    print("Natural language: LLM not available (check API key/provider).\n")
                    logger.warning("LLM interpreter not available after init")
            except Exception as exc:
                print(f"WARNING: Failed to initialize LLM interpreter: {exc}")
                logger.warning("LLM init failed: %s", exc)
    else:
        print("Natural language: Local only (LLM_ENABLED=false) — fast router active.\n")
        logger.info("LLM disabled, using fast local router only")

    print_banner(config, selected, speaker, mode_str)

    # -------------------------------------------------------------------
    # Hands-free wake-word loop
    # -------------------------------------------------------------------
    if use_wake_word:
        from app.wakeword.detector import WakeWordDetector  # already imported

        state = WakeWordState.LISTENING_FOR_WAKE_WORD
        wake_event = threading.Event()
        stop_requested = threading.Event()

        def on_wake_word():
            # Called in detector thread — signal main thread
            logger.info("Wake word callback fired — state=%s", state)
            print(f"\n✨ Wake word detected: \"{config.wake_word}\"")
            play_wake_sound(config.wake_sound_enabled)
            # Transition will be handled in main loop
            wake_event.set()

        detector = WakeWordDetector(
            wake_word=config.wake_word,
            threshold=config.wake_word_threshold,
            cooldown_ms=config.wake_word_cooldown_ms,
            device_index=selected.index,
            sample_rate=config.sample_rate,
            enabled=True,
        )

        # Handle mic permission / startup failure
        started = detector.start(on_wake_word)
        if not started:
            print("\nWARNING: Wake-word detector failed to start — falling back to manual mode.")
            print("Press ENTER to speak, Q+ENTER to quit.\n")
            logger.warning("Detector failed to start — falling back to manual")
            use_wake_word = False
        else:
            print(f"\n👂 Waiting for \"{config.wake_word}\"...")
            print("   Say the wake word hands-free. No keyboard needed.")
            print("   Press Ctrl+C or type Q+ENTER then press ENTER to quit.\n")
            logger.info("Wake-word engine initialized (backend=%s) — waiting", detector.get_backend())
            print(f"[Wake-word backend: {detector.get_backend()}]\n")
            if detector.get_backend() == "dummy":
                print("NOTE: Using dummy energy detector (vosk model not found).")
                print("For accurate 'Hey Nova' phrase detection, install Vosk:")
                print("  pip install vosk")
                print("  Download https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
                print("  Extract to nova/models/vosk-model-small-en-us-0.15\n")

        # Keyboard quit listener (non-blocking) for hands-free mode
        def keyboard_quit_listener():
            try:
                while not stop_requested.is_set():
                    # Use input with timeout via polling? Simpler: blocking input in daemon thread
                    # This allows Q+ENTER to quit even in wake mode
                    line = sys.stdin.readline()
                    if not line:
                        continue
                    if line.strip().lower() == "q":
                        print("\nQuit requested via keyboard.")
                        stop_requested.set()
                        wake_event.set()  # unblock main
                        break
            except Exception:
                pass

        kb_thread = None
        if detector.is_running():
            kb_thread = threading.Thread(target=keyboard_quit_listener, daemon=True)
            kb_thread.start()

        try:
            consecutive = 0
            while not stop_requested.is_set():
                # Check for quit via keyboard
                if stop_requested.is_set():
                    break

                # State: waiting for wake word
                if state == WakeWordState.LISTENING_FOR_WAKE_WORD:
                    logger.info("State: LISTENING_FOR_WAKE_WORD — waiting for wake word")
                    # Wait for wake event (with timeout to allow checking stop)
                    triggered = wake_event.wait(timeout=0.5)
                    if not triggered:
                        # No wake yet; continue waiting. Also show heartbeat every ~10s?
                        continue
                    # Wake detected
                    wake_event.clear()
                    if stop_requested.is_set():
                        break
                    state = WakeWordState.LISTENING_FOR_COMMAND
                    logger.info("State: LISTENING_FOR_COMMAND")
                    # Detector is already paused by callback; now record command
                    # Ensure mic released by detector before recording (detector paused, stream still open but not reading)
                    # Brief pause to let detector drain
                    time.sleep(0.12)

                    # ---- Record command (timeout based) ----
                    audio = record_command_auto(
                        device_index=selected.index,
                        sample_rate=config.sample_rate,
                        timeout_seconds=config.command_timeout_seconds,
                    )

                    if audio is None:
                        print("\nCommand cancelled.")
                        state = WakeWordState.LISTENING_FOR_WAKE_WORD
                        logger.info("Returning to wake-word mode (cancelled)")
                        detector.resume()
                        print(f"\n👂 Waiting for \"{config.wake_word}\"...\n")
                        continue

                    # Silence / timeout handling
                    if audio.size == 0:
                        print("\n⚠️  No command detected (no audio).")
                        print(f"👂 Waiting for \"{config.wake_word}\"...\n")
                        state = WakeWordState.LISTENING_FOR_WAKE_WORD
                        logger.info("No command detected — returning to wake")
                        detector.resume()
                        continue

                    rms = float(np.sqrt(np.mean(audio**2))) if audio.size else 0.0
                    duration = audio.size / config.sample_rate
                    if duration < 0.3 or rms < 0.003:
                        print("\n⚠️  No command detected.")
                        print(f"👂 Waiting for \"{config.wake_word}\"...\n")
                        logger.info("Silence/timeout (rms=%.5f dur=%.2fs) — returning to wake", rms, duration)
                        del audio
                        state = WakeWordState.LISTENING_FOR_WAKE_WORD
                        detector.resume()
                        continue

                    # ---- PROCESSING ----
                    state = WakeWordState.PROCESSING
                    print("\nTranscribing...\n")
                    logger.info("Transcription started (hands-free)")
                    try:
                        text = transcriber.transcribe(audio, sample_rate=config.sample_rate)
                    except RuntimeError as exc:
                        print(f"\n❌ Unable to transcribe audio.\nDetails: {exc}")
                        logger.error("Transcription failed: %s", exc)
                        del audio
                        state = WakeWordState.LISTENING_FOR_WAKE_WORD
                        detector.resume()
                        print(f"\n👂 Waiting for \"{config.wake_word}\"...\n")
                        continue
                    except Exception as exc:
                        print(f"\n❌ Unexpected transcription error: {exc}")
                        logger.exception("Unexpected")
                        del audio
                        state = WakeWordState.LISTENING_FOR_WAKE_WORD
                        detector.resume()
                        print(f"\n👂 Waiting for \"{config.wake_word}\"...\n")
                        continue
                    finally:
                        try:
                            del audio
                        except Exception:
                            pass

                    if not text or not text.strip():
                        print("⚠️  No speech detected. Try again.")
                        print(f"👂 Waiting for \"{config.wake_word}\"...\n")
                        state = WakeWordState.LISTENING_FOR_WAKE_WORD
                        logger.info("Empty transcription — back to wake")
                        detector.resume()
                        continue
                    else:
                        print("📝 You said:\n")
                        print(f'  "{text}"')
                        logger.info("Transcription: %r (hands-free)", text[:120])

                    # ---- SPEAKING (Phase 5: fast local + LLM) ----
                    state = WakeWordState.SPEAKING
                    try:
                        response = route_pc_command(text, pc_controller, interpreter, config)
                    except Exception as exc:
                        logger.exception("Route failed: %s", exc)
                        response = "I couldn't process that command right now."
                    if response:
                        print("\n🔊 Nova:\n")
                        print(f'  "{response}"')
                        logger.info("Response: %r", response[:120])
                        if speaker.is_available:
                            # Suppress wake-word during TTS
                            detector.set_speaking(True)
                            t0 = time.perf_counter()
                            ok = speaker.speak(response)
                            dt = time.perf_counter() - t0
                            logger.info("TTS %s in %.2fs", "ok" if ok else "failed", dt)
                            detector.set_speaking(False)
                            if not ok:
                                print("(TTS failed — response shown above)")
                        # Cooldown already applied via set_speaking resume timer
                    else:
                        logger.debug("Empty response")

                    consecutive += 1
                    state = WakeWordState.LISTENING_FOR_WAKE_WORD
                    logger.info("Returning to wake-word mode (consecutive=%d)", consecutive)
                    print(f"\n👂 Waiting for \"{config.wake_word}\"... ({consecutive} interactions completed)\n")
                    # Ensure detector resumed (speak path already resumes via timer, but ensure)
                    # Small delay to avoid immediate echo
                    time.sleep(config.wake_word_cooldown_ms / 1000.0 * 0.5)
                    if not detector.is_running():
                        detector.resume()
                    else:
                        # If still paused, resume now (in case speak path timer not yet fired)
                        try:
                            detector.resume()
                        except Exception:
                            pass

        except KeyboardInterrupt:
            print("\nExiting Nova. Goodbye!")
            stop_requested.set()
        finally:
            logger.info("Shutting down hands-free mode...")
            try:
                detector.stop()
            except Exception as exc:
                logger.warning("Detector stop error: %s", exc)
            # Fall through to common shutdown

    # -------------------------------------------------------------------
    # Manual fallback loop (Phase 1/2 compat)
    # -------------------------------------------------------------------
    if not use_wake_word:
        # Already printed banner; manual loop
        if not args.manual and not config.wake_word_enabled:
            print("\n👋 Wake-word disabled — using manual ENTER mode.")
            print("   Tip: enable hands-free: set WAKE_WORD_ENABLED=true and restart without --manual\n")
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
                audio = record_until_enter(device_index=selected.index, sample_rate=config.sample_rate, max_seconds=config.max_recording_seconds)

                if audio is None:
                    print("\nStatus: READY")
                    continue
                if audio.size == 0:
                    print("\n⚠️  No speech detected. Try again.")
                    print("\nStatus: READY")
                    continue
                rms = float(np.sqrt(np.mean(audio**2))) if audio.size else 0.0
                duration = audio.size / config.sample_rate
                if duration < 0.3:
                    print("\n⚠️  Recording too short. Try speaking a bit longer.")
                    print("\nStatus: READY")
                    del audio
                    continue
                if rms < 0.003:
                    print("\n⚠️  No speech detected (silence). Try again.")
                    logger.info("Silence detected (rms=%.5f)", rms)
                    print("\nStatus: READY")
                    del audio
                    continue
                print("\nTranscribing...\n")
                logger.info("Starting transcription (manual)...")
                try:
                    text = transcriber.transcribe(audio, sample_rate=config.sample_rate)
                except RuntimeError as exc:
                    print(f"\n❌ Unable to transcribe audio.\nPlease try again.\nDetails: {exc}")
                    logger.error("Transcription failed: %s", exc)
                    print("\nStatus: READY")
                    continue
                except Exception as exc:
                    print(f"\n❌ Unexpected transcription error: {exc}\nPlease try again.")
                    logger.exception("Unexpected")
                    print("\nStatus: READY")
                    continue
                finally:
                    try:
                        del audio
                    except Exception:
                        pass
                if not text or not text.strip():
                    print("⚠️  No speech detected. Try again.")
                else:
                    print("📝 You said:\n")
                    print(f'  "{text}"')
                # Route via Phase 5 helper (fast + LLM)
                if text and text.strip():
                    try:
                        response = route_pc_command(text, pc_controller, interpreter, config)
                    except Exception as exc:
                        logger.exception("Route failed: %s", exc)
                        response = "I couldn't process that command right now."
                else:
                    response = ""
                if response:
                    print("\n🔊 Nova:\n")
                    print(f'  "{response}"')
                    logger.info("Generated response: %r", response[:120])
                    if speaker.is_available:
                        t0 = time.perf_counter()
                        ok = speaker.speak(response)
                        dt = time.perf_counter() - t0
                        logger.info("TTS %s in %.2fs", "ok" if ok else "failed", dt)
                print("\nStatus: READY")
        except KeyboardInterrupt:
            print("\nExiting Nova. Goodbye!")

    # ---- Common clean shutdown ----
    logger.info("Shutting down Nova...")
    try:
        if 'speaker' in locals() and speaker is not None:
            try:
                speaker.stop()
                speaker.shutdown()
            except Exception as exc:
                logger.warning("TTS shutdown error: %s", exc)
    except Exception:
        pass
    logger.info("Nova Voice Engine stopped.")
    print("\nNova stopped.")


if __name__ == "__main__":
    main()
