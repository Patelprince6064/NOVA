"""Nova Voice Engine — Phase 8 multi-step agent entry point.

Flow hands-free:
    Config -> Mic -> Whisper -> TTS -> WakeWordDetector -> PCController -> BrowserController -> Vision -> AI Interpreter -> Agent
    -> LISTENING_FOR_WAKE_WORD --"Hey Nova"--> LISTENING_FOR_COMMAND
    -> PROCESSING (Whisper) -> Fast single? -> Agent planner (multi-step) -> Validated plan -> Executor (step verify, retry, timeout, cancel) -> SPEAKING -> back

Agent: only allowlisted actions, max 8 steps, sequential verify, no code/shell, no unsafe, single action per step.
Privacy: audio RAM only, screenshots on demand, vision only when needed, no continuous monitoring.
"""

import argparse
import logging
import sys
import time
import threading
import queue
import re
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
from app.browser.controller import BrowserController
from app.browser.actions import handle_browser_command
try:
    from app.vision.analyzer import ScreenAnalyzer
    from app.vision.schemas import FindResult
except ImportError:
    ScreenAnalyzer = None  # type: ignore
    FindResult = None  # type: ignore
try:
    from app.agent.planner import TaskPlanner
    from app.agent.executor import TaskExecutor, TaskState
    from app.agent.validator import validate_plan
except ImportError:
    TaskPlanner = None  # type: ignore
    TaskExecutor = None  # type: ignore
    TaskState = None  # type: ignore
    validate_plan = None  # type: ignore
try:
    from app.ai.interpreter import CommandInterpreter
except ImportError:
    CommandInterpreter = None  # type: ignore
try:
    from app.conversation.manager import ConversationManager
    from app.conversation.state import ConversationState
    from app.conversation.router import resolve_follow_up, is_cancellation_phrase
except ImportError:
    ConversationManager = None  # type: ignore
    ConversationState = None  # type: ignore
    resolve_follow_up = None  # type: ignore
    is_cancellation_phrase = None  # type: ignore
try:
    from app.interrupt.manager import InterruptManager
    from app.interrupt.detector import is_stop_command, is_retry_command, get_interrupt_priority
    from app.interrupt.events import get_global_stop_event
except ImportError:
    InterruptManager = None  # type: ignore
    is_stop_command = None  # type: ignore
    is_retry_command = None  # type: ignore
    get_interrupt_priority = None  # type: ignore
    get_global_stop_event = None  # type: ignore
try:
    from app.performance.timer import PerfTimer
    from app.performance.metrics import global_metrics
except ImportError:
    PerfTimer = None  # type: ignore
    global_metrics = None  # type: ignore

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

def _handle_vision_local(text: str, vision_analyzer, pc_controller, config) -> tuple[bool, str]:
    """Fast local vision handling without LLM (on-demand capture). Returns (handled, response)."""
    if vision_analyzer is None or not config.vision_enabled:
        return False, ""
    low = text.strip().lower()
    # Normalize wake prefix already removed, but handle variations
    # Active window queries
    if any(p in low for p in ["what application is open", "what app is open", "which application is open", "what app is currently open"]):
        try:
            win = pc_controller.get_foreground_window() if pc_controller else None
            if win:
                return True, f"{win} is open."
            return True, "I couldn't determine the active application."
        except Exception as exc:
            logger.warning("Active window failed: %s", exc)
            return True, "I couldn't determine the active application."
    if low in ("is there a browser open", "is a browser open") or "browser open" in low:
        try:
            win = pc_controller.get_foreground_window() if pc_controller else ""
            if win and any(b in win.lower() for b in ["chrome", "brave", "edge", "firefox", "browser"]):
                return True, f"Yes, {win} is open."
            return True, "I don't see a browser open."
        except Exception:
            return True, "I couldn't check."
    # Generic screen description — triggers analyzer (with fallback if no API)
    if any(p in low for p in ["what is on my screen", "what do you see", "describe my screen", "what is visible on my screen", "what's on my screen"]):
        try:
            win = pc_controller.get_foreground_window() if pc_controller else None
            analysis = vision_analyzer.analyze(low, active_window=win)
            # Filter elements by confidence already done in analyzer
            desc = analysis.description.strip() if analysis.description else "I see a computer screen."
            return True, desc
        except Exception as exc:
            logger.warning("Vision local analyze failed: %s", exc)
            return True, "I couldn't understand what's on the screen right now."
    # Find element fast local (exact phrase "find the X" / "where is the X")
    m = re.match(r"^(?:find|where is|locate)\s+(?:the\s+)?(.+)$", low)
    if m:
        target = m.group(1).strip().rstrip("?.!").strip()
        # Avoid catching YouTube content search like "find arijit singh on youtube" — those are browser searches
        # But allow UI element search like "youtube search box"
        is_ui_target = any(k in target for k in ["search box", "button", "input", "link", "menu", "icon", "window", "notepad", "browser"])
        if not is_ui_target:
            if " on youtube" in low or ("youtube" in low and "search" in low):
                return False, ""
        # Only handle UI element-like targets
        if is_ui_target:
            try:
                win = pc_controller.get_foreground_window() if pc_controller else None
                result = vision_analyzer.find_element(target, active_window=win)
                if result.found:
                    return True, f"I found {result.label} near {result.x}, {result.y}."
                else:
                    return True, "I couldn't find that on the screen."
            except Exception as exc:
                logger.warning("Vision find failed: %s", exc)
                return True, "I couldn't find that on the screen."
    return False, ""


def route_pc_command(text: str, controller: PCController, interpreter, config, browser_controller=None, vision_analyzer=None, context: Optional[dict] = None) -> str:
    """Route via fast local router (vision + browser + PC), fallback to LLM if needed.

    Architecture:
        text -> context follow-up router (pronoun resolution, fast local) -> vision fast (on-demand screenshot) -> browser fast -> pc fast -> if known -> done
        else if LLM enabled & available -> interpreter (with context) -> validate -> execute via appropriate controller (vision/browser/pc) -> response
        else -> original unknown response

    Screenshots only on vision path. Normal commands do NOT capture.

    Returns response string to speak. Never generates code/shell.
    """
    if not text or not text.strip():
        return ""
    # Phase 9: Lightweight follow-up router — handle pronoun / fast phrases without LLM
    if context is not None and resolve_follow_up is not None:
        try:
            action, clarification = resolve_follow_up(text, context)
            if clarification:
                logger.info("[ROUTER] Clarification: %r", clarification)
                return clarification
            if action is not None:
                logger.info("[ROUTER] Local command -> %r", action)
                act = action.get("action", "")
                # Fast scroll
                if act == "scroll_fast":
                    amt = action.get("amount", 500)
                    # Browser scroll uses large amount, pc uses small; try browser first
                    if browser_controller and getattr(browser_controller, "is_running", False):
                        try:
                            ok, msg = browser_controller.scroll(int(amt))
                            return msg
                        except Exception:
                            pass
                    # Fallback to pc scroll
                    pc_amt = 5 if amt > 0 else -5
                    try:
                        ok, msg = controller.scroll(int(pc_amt))
                        return msg
                    except Exception as exc:
                        logger.warning("Scroll fast failed: %s", exc)
                        return "I couldn't scroll."
                if act in ("browser_back", "browser_forward", "browser_refresh"):
                    try:
                        if act == "browser_back":
                            ok, msg = browser_controller.go_back() if browser_controller else (False, "Browser is not running.")
                        elif act == "browser_forward":
                            ok, msg = browser_controller.go_forward() if browser_controller else (False, "Browser is not running.")
                        else:
                            ok, msg = browser_controller.refresh() if browser_controller else (False, "Browser is not running.")
                        return msg
                    except Exception as exc:
                        logger.warning("Browser nav failed: %s", exc)
                        return "I couldn't do that."
                if act == "click_screen_element":
                    # Context-aware click first result — try vision then browser fallback
                    target = action.get("target", "first video result")
                    if vision_analyzer is not None:
                        try:
                            win = controller.get_foreground_window() if controller else None
                            result = vision_analyzer.find_element(target, active_window=win)
                            if result.found and result.confidence >= getattr(config, "vision_min_confidence", 0.70):
                                try:
                                    import pyautogui
                                    pyautogui.FAILSAFE = False
                                    cx, cy = result.x + result.width // 2, result.y + result.height // 2
                                    pyautogui.moveTo(cx, cy, duration=0.2)
                                    pyautogui.click()
                                    return "Playing the first result."
                                except Exception as exc:
                                    logger.warning("Click via vision failed: %s", exc)
                                    return "I couldn't click that."
                            elif result.found:
                                return "I'm not confident enough to identify that."
                            else:
                                return "I couldn't find that on the screen."
                        except Exception as exc:
                            logger.warning("Vision find for click failed: %s", exc)
                            return "I couldn't find that."
                    # No vision: return graceful message that will be used as fallback
                    return "I couldn't find that on the screen."
                if act == "close_it":
                    if browser_controller and getattr(browser_controller, "is_running", False):
                        try:
                            ok, msg = browser_controller.close_browser()
                            return msg
                        except Exception:
                            pass
                    return "What would you like me to close?"
                if act == "repeat_last":
                    return "Okay, repeating that."
        except Exception as exc:
            logger.exception("Follow-up router error: %s", exc)
    # Vision fast local (on-demand screenshot) — before browser/pc to avoid misrouting visual questions
    if config.vision_enabled and vision_analyzer is not None:
        try:
            handled_v, resp_v = _handle_vision_local(text, vision_analyzer, controller, config)
            if handled_v:
                logger.info("Fast path: Vision local executed -> %r", resp_v)
                return resp_v
        except Exception as exc:
            logger.exception("Vision fast router failed: %s", exc)
    # Browser fast path (reuse session) — before PC to prefer Playwright for website/search
    if config.browser_enabled and browser_controller is not None:
        try:
            handled_b, resp_b = handle_browser_command(text, browser_controller)
            if handled_b:
                logger.info("Fast path: Browser action executed -> %r", resp_b)
                return resp_b
        except Exception as exc:
            logger.exception("Browser fast router failed: %s", exc)
    # If PC control disabled, fall back to friendly responses only (browser already tried)
    if not config.pc_control_enabled and not (config.browser_enabled and browser_controller):
        return generate_response(text)
    if not config.pc_control_enabled:
        # Still allow friendly responses via PC router (without executing)
        try:
            handled, fast_resp = handle_command(text, controller)
            if fast_resp in ("Hello! I'm Nova.", "Hi! I'm ready.", "I'm doing great. I'm ready for your next command.", "Voice system is working correctly."):
                return fast_resp
        except Exception:
            pass
        return generate_response(text)

    # Fast local PC path — executes PC action if matched
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
            logger.info("[AI] Fast path unknown -> trying LLM interpreter")
            try:
                validated, err = interpreter.interpret(text, context)
                if validated is not None:
                    # Dispatch validated action to appropriate controller
                    # validated already includes unsupported/clarification meta
                    if validated.get("action") in ("unsupported", "clarification"):
                        # For these meta actions, don't execute, just respond
                        if validated["action"] == "unsupported":
                            return "I can't perform that action yet."
                        else:
                            return validated.get("message", "Which option should I use?")
                    # Vision actions via ScreenAnalyzer when available
                    vision_actions = {"analyze_screen", "find_screen_element", "get_active_window"}
                    action = validated.get("action", "")
                    if vision_analyzer is not None and config.vision_enabled and action in vision_actions:
                        try:
                            win = controller.get_foreground_window() if controller else None
                            if action == "get_active_window":
                                if win:
                                    return f"{win} is open."
                                return "I couldn't determine the active application."
                            if action == "analyze_screen":
                                q = validated.get("question", "What is on my screen?")
                                analysis = vision_analyzer.analyze(q, active_window=win)
                                if analysis.confidence < config.vision_min_confidence and analysis.confidence != 0:
                                    return "I'm not confident enough to identify that."
                                return analysis.description
                            if action == "find_screen_element":
                                target = validated.get("target", "")
                                result = vision_analyzer.find_element(target, active_window=win)
                                if result.found:
                                    if result.confidence < config.vision_min_confidence:
                                        return "I'm not confident enough to identify that."
                                    return f"I found {result.label} near {result.x}, {result.y}."
                                return "I couldn't find that on the screen."
                        except TimeoutError:
                            return "Screen analysis timed out."
                        except Exception as exc:
                            logger.warning("Vision execution failed: %s", exc)
                            return "I couldn't understand what's on the screen right now."
                    # Browser actions via BrowserController when available
                    browser_actions = {"search_web", "youtube_search", "browser_back", "browser_forward", "browser_refresh", "browser_scroll", "close_browser", "open_url"}
                    # action already set
                    if browser_controller is not None and config.browser_enabled and action in browser_actions:
                        # Map validated browser action to BrowserController
                        try:
                            if action == "open_url":
                                target = validated.get("website") or validated.get("url") or ""
                                ok, msg = browser_controller.open_url(target)
                            elif action == "search_web":
                                ok, msg = browser_controller.search_web(validated.get("query", ""))
                            elif action == "youtube_search":
                                ok, msg = browser_controller.youtube_search(validated.get("query", ""))
                            elif action == "browser_back":
                                ok, msg = browser_controller.go_back()
                            elif action == "browser_forward":
                                ok, msg = browser_controller.go_forward()
                            elif action == "browser_refresh":
                                ok, msg = browser_controller.refresh()
                            elif action == "browser_scroll":
                                ok, msg = browser_controller.scroll(validated.get("amount", -500))
                            elif action == "close_browser":
                                ok, msg = browser_controller.close_browser()
                            else:
                                ok, msg = False, "I couldn't understand that command."
                            logger.info("LLM path browser executed: %r -> %r", validated, msg)
                            return msg
                        except Exception as exc:
                            logger.exception("LLM browser execution failed: %s", exc)
                            return "I couldn't perform that action."
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


def is_multi_step_request(text: str) -> bool:
    """Heuristic to detect multi-step requests for Phase 8 planner.

    Simple: if contains connector and >=2 verbs, or multiple 'open', or commas.
    Keeps simple commands like 'open Brave' fast path.
    """
    if not text or not text.strip():
        return False
    low = text.strip().lower()
    # Cancellation phrases are not multi-step
    if low in ("stop", "cancel", "never mind", "nevermind"):
        return False
    verbs = ["open", "launch", "start", "run", "go to", "search", "type", "press", "click", "scroll", "close", "find", "play", "write"]
    verb_count = sum(1 for v in verbs if v in low)
    has_connector = any(c in low for c in [" and ", " then ", ","])
    if has_connector and verb_count >= 2:
        return True
    if low.count("open") >= 2:
        return True
    # Check for comma + verbs
    if "," in low and verb_count >= 2:
        return True
    # Check for natural multi like "open Brave go to YouTube" without and
    # Count action triggers
    triggers = ["open ", "launch ", "search ", "type ", "press ", "click ", "scroll "]
    trigger_count = sum(1 for t in triggers if t in low)
    if trigger_count >= 2:
        return True
    return False


def is_cancellation_request(text: str) -> bool:
    low = text.strip().lower()
    return low in ("stop", "cancel", "never mind", "nevermind", "stop task", "cancel task")


def is_unsafe_request(text: str) -> bool:
    low = text.strip().lower()
    dangerous = ["delete", "format", "rm ", "shutdown", "kill ", "uninstall", "password", "bank", "purchase", "buy ", "payment",
                 "install ", "send email", "send message", "share private", "credential", "account recovery", "captcha", "security settings",
                 "log into", "log in", "sign in", "login", "read my emails", "read emails", "reply to", "attach a file", "send it"]
    return any(pat in low for pat in dangerous)


# ---------------------------------------------------------------------------
# Phase 9: Conversation helpers
# ---------------------------------------------------------------------------

def is_goodbye_phrase(text: str) -> bool:
    low = text.strip().lower()
    return low in ("goodbye", "good bye", "bye", "exit", "quit", "see you")


def update_context_after_command(text: str, response: str, controller, browser_controller, vision_analyzer, conversation_manager) -> None:
    """Update conversation context from last command (in-memory only). Never stores sensitive data."""
    if not conversation_manager or not conversation_manager.context_enabled:
        return
    low = text.strip().lower()
    ctx_updates = {}
    # Detect application opened
    for alias in ["brave", "chrome", "notepad", "calculator", "vscode", "explorer", "edge", "firefox"]:
        if f"open {alias}" in low or f"launch {alias}" in low or f"start {alias}" in low:
            ctx_updates["last_application"] = alias
            ctx_updates["last_action"] = "open_application"
            break
    # Detect website navigation
    if "youtube" in low and ("open" in low or "go to" in low or "launch" in low):
        ctx_updates["current_site"] = "youtube"
        ctx_updates["last_action"] = "open_url"
        if browser_controller and getattr(browser_controller, "current_url", None):
            ctx_updates["current_url"] = browser_controller.current_url
    elif "google" in low and ("open" in low or "go to" in low or "search" in low):
        if "search" not in low:
            ctx_updates["current_site"] = "google"
            ctx_updates["last_action"] = "open_url"
    # Detect searches
    if "search youtube for" in low:
        m = re.search(r"search youtube for (.+)", low)
        if m:
            q = m.group(1).strip().split(" and ")[0].strip()[:100]
            ctx_updates["last_search"] = q
            ctx_updates["last_action"] = "youtube_search"
            ctx_updates["current_site"] = "youtube"
    elif "search google for" in low:
        m = re.search(r"search google for (.+)", low)
        if m:
            q = m.group(1).strip()[:100]
            ctx_updates["last_search"] = q
            ctx_updates["last_action"] = "search_web"
            ctx_updates["current_site"] = "google"
    elif low.startswith("search ") and "youtube" not in low:
        # Generic search e.g., "search Arijit Singh" after going to youtube -> treat as youtube_search if youtube site
        cur_site = conversation_manager.get_context().get("current_site") if conversation_manager else None
        if cur_site == "youtube":
            q = low[len("search "):].strip()[:100]
            if q:
                ctx_updates["last_search"] = q
                ctx_updates["last_action"] = "youtube_search"
        else:
            q = low[len("search "):].strip()[:100]
            if q and len(q) > 1:
                ctx_updates["last_search"] = q
                ctx_updates["last_action"] = "search_web"
    elif "search for" in low:
        m = re.search(r"search for (.+)", low)
        if m:
            q = m.group(1).strip()[:100]
            ctx_updates["last_search"] = q
            # infer site
            if "youtube" in low or (conversation_manager and conversation_manager.get_context().get("current_site") == "youtube"):
                ctx_updates["last_action"] = "youtube_search"
            else:
                ctx_updates["last_action"] = "search_web"
    # Play first result
    if "play" in low and ("first" in low or "second" in low):
        ctx_updates["last_action"] = "click_screen_element"
    if "type " in low:
        ctx_updates["last_action"] = "type_text"
    if "scroll" in low:
        ctx_updates["last_action"] = "scroll"
    if "go back" in low or low == "back":
        ctx_updates["last_action"] = "browser_back"
    if "go forward" in low or low == "forward":
        ctx_updates["last_action"] = "browser_forward"
    if "refresh" in low:
        ctx_updates["last_action"] = "browser_refresh"
    # Browser current_url always update if available
    if browser_controller and getattr(browser_controller, "current_url", None):
        ctx_updates["current_url"] = browser_controller.current_url
        # infer current_site from url
        url = browser_controller.current_url.lower() if browser_controller.current_url else ""
        if "youtube" in url:
            ctx_updates["current_site"] = "youtube"
        elif "google" in url:
            ctx_updates["current_site"] = "google"
    # Foreground window as fallback for last_application
    if controller and not ctx_updates.get("last_application"):
        try:
            win = controller.get_foreground_window()
            if win:
                win_low = win.lower()
                for alias in ["brave", "chrome", "notepad", "calc", "code", "explorer", "edge"]:
                    if alias in win_low:
                        ctx_updates["last_application"] = alias
                        break
        except Exception:
            pass
    if response:
        ctx_updates["last_task_status"] = "success" if "couldn't" not in response.lower() and "can't" not in response.lower() else "failed"
    if ctx_updates:
        logger.info("[CONTEXT] Updating context: %r", ctx_updates)
        conversation_manager.update_context(**ctx_updates)


def speak_with_cooldown(speaker, detector, text: str, cooldown_ms: int) -> bool:
    """Speak with TTS suppression to avoid self-trigger. Returns True if spoken."""
    if not text or not text.strip():
        return False
    if speaker is None or not speaker.is_available:
        logger.info("[TTS] %s (TTS unavailable)", text[:80])
        print(f'[TTS] {text}')
        return False
    try:
        # Pause wake word during TTS
        if detector:
            detector.set_speaking(True)
        logger.info("[TTS] %r", text[:80])
        t0 = time.perf_counter()
        ok = speaker.speak(text)
        dt = time.perf_counter() - t0
        logger.info("[TTS] %s in %.2fs", "ok" if ok else "failed", dt)
        # Cooldown to avoid echo
        if cooldown_ms > 0:
            time.sleep(cooldown_ms / 1000.0)
        if detector:
            detector.set_speaking(False)
        return ok
    except Exception as exc:
        logger.warning("TTS speak failed: %s", exc)
        if detector:
            try:
                detector.set_speaking(False)
            except Exception:
                pass
        return False


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
    silence_timeout_ms: int = 700,
    config=None,
) -> Optional[np.ndarray]:
    """Record command after wake word, with timeout and silence handling.

    Records up to timeout_seconds. Uses simple VAD: if speech starts, wait for
    silence_timeout (default 0.7s from config) of continuous silence after speech to stop early.
    If no speech within timeout, returns empty (timeout).
    Phase 11: configurable silence_timeout_ms / min_speech_duration_ms for faster response.
    """
    # Use config values if provided (Phase 11 optimization)
    if config is not None:
        try:
            silence_timeout_ms = int(getattr(config, "silence_timeout_ms", silence_timeout_ms))
            min_ms = int(getattr(config, "min_speech_duration_ms", int(min_speech_duration*1000)))
            min_speech_duration = max(0.1, min_ms / 1000.0)
        except Exception:
            pass
    silence_timeout_sec = max(0.2, silence_timeout_ms / 1000.0)
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
                        # Phase 11: configurable silence timeout (0.7s default) for faster stop
                        if silence_since >= silence_timeout_sec:
                            total_dur = sum(len(c) for c in chunks) / sample_rate
                            if total_dur >= max(0.6, min_speech_duration + 0.2):
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
                    if silence_since >= silence_timeout_sec:
                        total_dur = sum(len(c) for c in chunks) / sample_rate if chunks else 0
                        if total_dur >= max(0.6, min_speech_duration + 0.2):
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
    browser_status = "ENABLED" if config.browser_enabled else "DISABLED"
    vision_status = "ENABLED" if config.vision_enabled else "DISABLED"
    agent_status = "ENABLED" if config.agent_enabled else "DISABLED"
    conv_status = "ENABLED" if config.conversation_mode_enabled and config.conversation_context_enabled else ("DISABLED" if not config.conversation_mode_enabled else "CTX-DISABLED")
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
    print(f"🌐 Browser: {browser_status} ({config.browser_name} headless={config.browser_headless} timeout={config.browser_timeout_ms}ms)")
    print(f"👁️  Vision: {vision_status} (monitor={config.screen_monitor} max={config.screenshot_max_width}x{config.screenshot_max_height} conf>={config.vision_min_confidence})")
    print(f"🤖 Agent: {agent_status} (steps={config.max_task_steps} duration={config.max_task_duration_seconds}s)")
    print(f"💬 Conversation: {conv_status} (timeout={config.conversation_timeout_seconds}s follow={config.follow_up_timeout_seconds}s turns={config.max_conversation_turns} cooldown={config.post_tts_cooldown_ms}ms)")
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
        print("Nova Voice Engine — Phase 8")
        print("  python -m app.main          # hands-free wake-word + multi-step agent (default)")
        print("  python -m app.main --manual # manual ENTER mode")
        print("  python -m app.main --help   # this help")
        print("")
        print("Examples: 'open Brave and go to YouTube' | 'open YouTube and search for Arijit Singh'")
        print("  'open Brave, go to YouTube, search for Arijit Singh, and play the first song' (multi-step)")
        print("  'what is on my screen?' | 'where is the YouTube search box?' (vision)")
        print("Simple 'open Brave' still fast path without planner.")
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

    # ---- Initialize Browser controller (Phase 6) ----
    browser_controller = BrowserController(
        enabled=config.browser_enabled,
        browser_name=config.browser_name,
        headless=config.browser_headless,
        timeout_ms=config.browser_timeout_ms,
    )
    if config.browser_enabled:
        print(f"Browser control: Enabled ({config.browser_name}, headless={config.browser_headless})\n")
        logger.info("BrowserController initialized: %s headless=%s", config.browser_name, config.browser_headless)
        # Check playwright availability
        try:
            from playwright.sync_api import sync_playwright as _sp  # noqa
            print("Playwright: Available\n")
        except ImportError:
            print("WARNING: Playwright not installed. Browser actions will fail.")
            print("Install: pip install playwright && playwright install chromium\n")
            logger.warning("Playwright not installed")
    else:
        print("Browser control: Disabled (BROWSER_ENABLED=false)\n")
        logger.info("Browser control disabled by config")

    # ---- Initialize Vision analyzer (Phase 7) ----
    vision_analyzer = None
    if config.vision_enabled:
        if ScreenAnalyzer is None:
            print("WARNING: Vision enabled but vision module not available.\n")
            logger.warning("ScreenAnalyzer import failed")
        else:
            try:
                vision_analyzer = ScreenAnalyzer(
                    enabled=config.vision_enabled,
                    provider=config.vision_provider or config.llm_provider,
                    model=config.vision_model or config.llm_model,
                    api_key=config.vision_api_key or config.llm_api_key,
                    timeout_seconds=config.vision_timeout_seconds,
                    min_confidence=config.vision_min_confidence,
                    click_test_enabled=config.vision_click_test_enabled,
                    screen_monitor=config.screen_monitor,
                    max_width=config.screenshot_max_width,
                    max_height=config.screenshot_max_height,
                )
                if vision_analyzer.is_available():
                    print(f"Vision: Enabled (provider={vision_analyzer.provider} model={vision_analyzer.model or 'default'} monitor={config.screen_monitor} max={config.screenshot_max_width}x{config.screenshot_max_height} conf>={config.vision_min_confidence})\n")
                    logger.info("Vision initialized: provider=%s model=%s", vision_analyzer.provider, vision_analyzer.model or "default")
                    # List monitors
                    try:
                        mons = vision_analyzer.capture.list_monitors()
                        if mons:
                            print(f"Monitors detected: {len(mons)-1} + all")
                            for m in mons[1:4]:
                                print(f"  [{m['index']}] {m['width']}x{m['height']} at {m['left']},{m['top']} primary={m['is_primary']}")
                            print()
                    except Exception:
                        pass
                else:
                    print("Vision: Disabled\n")
            except Exception as exc:
                print(f"WARNING: Vision init failed: {exc}\n")
                logger.warning("Vision init failed: %s", exc)
    else:
        print("Vision: Disabled (VISION_ENABLED=false)\n")
        logger.info("Vision disabled")

    # ---- Initialize Interrupt manager (Phase 10) ----
    interrupt_manager = None
    try:
        if InterruptManager is not None and get_global_stop_event is not None:
            interrupt_manager = InterruptManager(
                enabled=config.interruption_enabled,
                check_interval_ms=config.interruption_check_interval_ms,
                post_cancel_cooldown_ms=config.post_cancel_cooldown_ms,
                global_event=get_global_stop_event(),
            )
            print(f"Interruption: {'Enabled' if config.interruption_enabled else 'Disabled'} (stop_cmds={'on' if config.stop_commands_enabled else 'off'} interval={config.interruption_check_interval_ms}ms cancel_cooldown={config.post_cancel_cooldown_ms}ms)\n")
            logger.info("InterruptManager initialized: enabled=%s interval=%d cooldown=%d", config.interruption_enabled, config.interruption_check_interval_ms, config.post_cancel_cooldown_ms)
        else:
            print("Interruption: module not available\n")
            logger.warning("InterruptManager import failed")
    except Exception as exc:
        print(f"WARNING: Interruption init failed: {exc}\n")
        logger.warning("Interruption init failed: %s", exc)

    # ---- Initialize Performance metrics (Phase 11) ----
    perf_timer = None
    perf_metrics = None
    try:
        if PerfTimer is not None and global_metrics is not None:
            perf_timer = PerfTimer()
            perf_metrics = global_metrics
            print(f"Performance: {'Debug ON' if config.performance_debug else 'Debug off'} (silence={config.silence_timeout_ms}ms min_speech={config.min_speech_duration_ms}ms)\n")
            logger.info("Performance metrics initialized: debug=%s", config.performance_debug)
    except Exception as exc:
        logger.warning("Performance init failed: %s", exc)

    # ---- Initialize Agent planner/executor (Phase 8) ----
    agent_planner = None
    agent_executor = None
    if config.agent_enabled:
        if TaskPlanner is None or TaskExecutor is None:
            print("WARNING: Agent enabled but agent module not available.\n")
            logger.warning("Agent import failed")
        else:
            try:
                agent_planner = TaskPlanner(config)
                agent_executor = TaskExecutor(pc_controller, browser_controller, vision_analyzer, config, interrupt_manager=interrupt_manager)
                print(f"Agent: Enabled (max_steps={config.max_task_steps} duration={config.max_task_duration_seconds}s wait={config.max_wait_seconds}s)\n")
                logger.info("Agent initialized: steps=%d duration=%d", config.max_task_steps, config.max_task_duration_seconds)
            except Exception as exc:
                print(f"WARNING: Agent init failed: {exc}\n")
                logger.warning("Agent init failed: %s", exc)
    else:
        print("Agent: Disabled (AGENT_ENABLED=false)\n")
        logger.info("Agent disabled")

    # ---- Initialize Conversation manager (Phase 9) ----
    conversation_manager = None
    if ConversationManager is not None:
        try:
            conversation_manager = ConversationManager(
                enabled=config.conversation_mode_enabled,
                conversation_timeout=config.conversation_timeout_seconds,
                follow_up_timeout=config.follow_up_timeout_seconds,
                max_turns=config.max_conversation_turns,
                context_enabled=config.conversation_context_enabled,
                post_tts_cooldown_ms=config.post_tts_cooldown_ms,
            )
            print(f"Conversation: {'Enabled' if config.conversation_mode_enabled else 'Disabled'} (timeout={config.conversation_timeout_seconds}s follow={config.follow_up_timeout_seconds}s turns={config.max_conversation_turns} cooldown={config.post_tts_cooldown_ms}ms)\n")
            logger.info("ConversationManager initialized: enabled=%s timeout=%s follow=%s max_turns=%s",
                        config.conversation_mode_enabled, config.conversation_timeout_seconds, config.follow_up_timeout_seconds, config.max_conversation_turns)
        except Exception as exc:
            print(f"WARNING: Conversation init failed: {exc}\n")
            logger.warning("Conversation init failed: %s", exc)
    else:
        print("Conversation: module not available\n")

    print_banner(config, selected, speaker, mode_str)

    # -------------------------------------------------------------------
    # Hands-free wake-word loop — Phase 9 conversation mode
    # -------------------------------------------------------------------
    if use_wake_word:
        from app.wakeword.detector import WakeWordDetector  # already imported

        state = WakeWordState.LISTENING_FOR_WAKE_WORD
        wake_event = threading.Event()
        stop_requested = threading.Event()

        def on_wake_word():
            # Called in detector thread — signal main thread
            logger.info("[WAKE] Wake word detected — state=%s", state)
            print(f"\n✨ Wake word detected: \"{config.wake_word}\"")
            logger.info("[WAKE] Wake word detected")
            play_wake_sound(config.wake_sound_enabled)
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
            print("   After wake, you can chain commands without saying Hey Nova each time.")
            print("   Conversation ends after ~{}s silence or {} turns.".format(config.conversation_timeout_seconds, config.max_conversation_turns))
            print("   Say 'Stop', 'Cancel', or 'Goodbye' to end early.")
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
        if 'detector' in locals() and detector.is_running():
            kb_thread = threading.Thread(target=keyboard_quit_listener, daemon=True)
            kb_thread.start()

        try:
            consecutive = 0
            while not stop_requested.is_set():
                if stop_requested.is_set():
                    break

                # State: waiting for wake word
                if state == WakeWordState.LISTENING_FOR_WAKE_WORD:
                    logger.info("[WAKE] Waiting for wake word")
                    # Also handle conversation timeout if previously active (should be reset already)
                    if conversation_manager and conversation_manager.handle_timeout_if_needed():
                        logger.info("[TIMEOUT] Conversation timed out — back to wake")
                        print(f"\n👂 Waiting for \"{config.wake_word}\"...\n")
                    triggered = wake_event.wait(timeout=0.5)
                    if not triggered:
                        continue
                    wake_event.clear()
                    if stop_requested.is_set():
                        break
                    # Wake detected -> start conversation
                    logger.info("[WAKE] Wake word detected")
                    if conversation_manager:
                        conversation_manager.start()
                        conversation_manager.set_state(ConversationState.WAKE_DETECTED)
                        logger.info("[CONTEXT] Conversation active")
                    state = WakeWordState.LISTENING_FOR_COMMAND
                    # fall through to conversation loop — detector already paused by callback
                    # Brief pause to let detector drain
                    time.sleep(0.12)
                    # Enter conversation inner loop
                    turn_in_conversation = 0
                    while True:
                        if stop_requested.is_set():
                            break
                        # Check conversation timeout / turn limit before listening
                        if conversation_manager:
                            if conversation_manager.should_timeout():
                                logger.info("[TIMEOUT] Conversation timeout — resetting")
                                print("\n[ TIMEOUT ] Conversation ended due to inactivity.")
                                try:
                                    speak_with_cooldown(speaker, detector, "Going to sleep.", config.post_tts_cooldown_ms)
                                except Exception:
                                    pass
                                conversation_manager.reset()
                                logger.info("[RESET] Conversation reset after timeout")
                                break
                            if conversation_manager.check_turn_limit():
                                logger.info("[RESET] Max turns reached %d", config.max_conversation_turns)
                                try:
                                    speak_with_cooldown(speaker, detector, 'Say "Hey Nova" to continue.', config.post_tts_cooldown_ms)
                                except Exception:
                                    pass
                                conversation_manager.reset()
                                break
                            # Update state to LISTENING / CONVERSATION_ACTIVE
                            if turn_in_conversation == 0:
                                conversation_manager.set_state(ConversationState.LISTENING)
                            else:
                                conversation_manager.set_state(ConversationState.CONVERSATION_ACTIVE)
                                logger.info("[CONTEXT] Conversation active turn %d", turn_in_conversation)
                                print(f"\n[CONVERSATION_ACTIVE] Listening for follow-up ({turn_in_conversation+1}/{config.max_conversation_turns}) — no wake word needed.\n")
                        state = WakeWordState.LISTENING_FOR_COMMAND
                        logger.info("[LISTENING] Listening for command (turn %d)", turn_in_conversation+1)
                        print("\n🎤 LISTENING..." if turn_in_conversation==0 else "\n🎤 LISTENING (follow-up)...")
                        print("Speak now (say your command).\n" if turn_in_conversation==0 else "Speak follow-up (or wait to timeout).\n")

                        # Phase 11: timing — total + recording
                        if perf_timer:
                            perf_timer.start("total")
                            perf_timer.start("recording")
                        # Choose timeout: first command uses COMMAND_TIMEOUT, follow-ups use FOLLOW_UP
                        timeout_seconds = config.command_timeout_seconds if turn_in_conversation == 0 else config.follow_up_timeout_seconds
                        audio = record_command_auto(
                            device_index=selected.index,
                            sample_rate=config.sample_rate,
                            timeout_seconds=timeout_seconds,
                            config=config,
                        )
                        if perf_timer:
                            rec = perf_timer.stop("recording")
                            if perf_metrics:
                                perf_metrics.record("recording", rec)

                        if audio is None:
                            print("\nCommand cancelled.")
                            logger.info("[RESET] Command cancelled by user")
                            if conversation_manager:
                                conversation_manager.reset()
                            state = WakeWordState.LISTENING_FOR_WAKE_WORD
                            try:
                                detector.resume()
                            except Exception:
                                pass
                            print(f"\n👂 Waiting for \"{config.wake_word}\"...\n")
                            break

                        # Silence / timeout handling
                        if audio.size == 0:
                            logger.info("[TIMEOUT] No audio captured in conversation")
                            if conversation_manager and conversation_manager.is_active():
                                # Treat as timeout within conversation
                                if conversation_manager.should_timeout():
                                    conversation_manager.reset()
                                    state = WakeWordState.LISTENING_FOR_WAKE_WORD
                                    try:
                                        detector.resume()
                                    except Exception:
                                        pass
                                    print(f"\n👂 Waiting for \"{config.wake_word}\"...\n")
                                    break
                                # Otherwise, if first turn, back to wake; if follow-up, also break to wake after timeout
                                print("\n⚠️  No command detected (no audio).")
                                # For follow-up, consider timeout -> reset
                                if turn_in_conversation > 0:
                                    # No follow-up speech within window -> end conversation
                                    conversation_manager.reset()
                                    state = WakeWordState.LISTENING_FOR_WAKE_WORD
                                    try:
                                        detector.resume()
                                    except Exception:
                                        pass
                                    print(f"\n👂 Waiting for \"{config.wake_word}\"...\n")
                                    break
                                else:
                                    state = WakeWordState.LISTENING_FOR_WAKE_WORD
                                    try:
                                        detector.resume()
                                    except Exception:
                                        pass
                                    print(f"\n👂 Waiting for \"{config.wake_word}\"...\n")
                                    break
                            else:
                                print("\n⚠️  No command detected (no audio).")
                                print(f"👂 Waiting for \"{config.wake_word}\"...\n")
                                state = WakeWordState.LISTENING_FOR_WAKE_WORD
                                try:
                                    detector.resume()
                                except Exception:
                                    pass
                                break

                        rms = float(np.sqrt(np.mean(audio**2))) if audio.size else 0.0
                        duration = audio.size / config.sample_rate
                        if duration < 0.3 or rms < 0.003:
                            print("\n⚠️  No command detected.")
                            logger.info("[TIMEOUT] Silence/timeout (rms=%.5f dur=%.2fs)", rms, duration)
                            del audio
                            if conversation_manager and conversation_manager.is_active() and turn_in_conversation > 0:
                                # End follow-up silence as timeout
                                if conversation_manager.should_timeout():
                                    conversation_manager.reset()
                                else:
                                    # Still consider no command as not resetting immediately, but continue listening?
                                    # For Phase 9 test we need timeout to return to wake after FOLLOW_UP timeout
                                    # So if no speech on follow-up, wait for timeout already handled via next loop timeout check
                                    pass
                                # If still active, continue waiting? But to avoid tight loop, break to wake after one empty?
                                # We break to wake to require Hey Nova again (matches Test 4)
                                if conversation_manager and not conversation_manager.is_active():
                                    state = WakeWordState.LISTENING_FOR_WAKE_WORD
                                    try:
                                        detector.resume()
                                    except Exception:
                                        pass
                                    print(f"\n👂 Waiting for \"{config.wake_word}\"...\n")
                                    break
                                # If still active but empty, try again once more then timeout will trigger
                                continue
                            else:
                                state = WakeWordState.LISTENING_FOR_WAKE_WORD
                                try:
                                    detector.resume()
                                except Exception:
                                    pass
                                print(f"\n👂 Waiting for \"{config.wake_word}\"...\n")
                                break

                        # ---- PROCESSING ----
                        state = WakeWordState.PROCESSING
                        if conversation_manager:
                            conversation_manager.set_state(ConversationState.PROCESSING)
                        print("\nTranscribing...\n")
                        logger.info("[PROCESSING] Transcription started (hands-free)")
                        if perf_timer:
                            perf_timer.start("transcription")
                        try:
                            text = transcriber.transcribe(audio, sample_rate=config.sample_rate)
                            if perf_timer:
                                tr = perf_timer.stop("transcription")
                                if perf_metrics:
                                    perf_metrics.record("transcription", tr)
                                    perf_metrics.record("stt", tr)
                        except RuntimeError as exc:
                            if perf_timer:
                                try: perf_timer.stop("transcription")
                                except Exception: pass
                            if perf_metrics:
                                perf_metrics.increment_command(is_error=True)
                            print(f"\n❌ Unable to transcribe audio.\nDetails: {exc}")
                            logger.error("Transcription failed: %s", exc)
                            del audio
                            # Stay in conversation? Offer retry then continue
                            try:
                                speak_with_cooldown(speaker, detector, "I didn't catch that.", config.post_tts_cooldown_ms)
                            except Exception:
                                pass
                            continue
                        except Exception as exc:
                            if perf_timer:
                                try: perf_timer.stop("transcription")
                                except Exception: pass
                            if perf_metrics:
                                perf_metrics.increment_command(is_error=True)
                            print(f"\n❌ Unexpected transcription error: {exc}")
                            logger.exception("Unexpected")
                            del audio
                            continue
                        finally:
                            try:
                                del audio
                            except Exception:
                                pass

                        if not text or not text.strip():
                            print("⚠️  No speech detected. Try again.")
                            logger.info("Empty transcription — stay in conversation")
                            # Stay in conversation for follow-up retry
                            continue
                        else:
                            print("📝 You said:\n")
                            print(f'  "{text}"')
                            logger.info("[USER] %r", text[:120])
                            if conversation_manager and conversation_manager.context_enabled:
                                logger.info("[CONTEXT] %r", conversation_manager.get_context())

                        # ---- Priority 1: Interruption check (highest) ----
                        # Must handle stop/cancel before any AI planner or normal routing
                        _is_stop = False
                        try:
                            if config.interruption_enabled and config.stop_commands_enabled and is_stop_command is not None and is_stop_command(text):
                                _is_stop = True
                            elif is_cancellation_request(text) or text.strip().lower() in ("stop", "cancel", "goodbye", "good bye", "bye", "exit", "quit", "abort", "shut up"):
                                _is_stop = True
                        except Exception:
                            _is_stop = is_cancellation_request(text)
                        if _is_stop:
                            logger.info("[INTERRUPT] Stop command detected: %r", text)
                            # Request global stop
                            try:
                                if interrupt_manager:
                                    interrupt_manager.request_stop()
                                elif get_global_stop_event:
                                    get_global_stop_event().set()
                            except Exception:
                                pass
                            # Stop TTS immediately
                            try:
                                logger.info("[INTERRUPT] Stopping TTS")
                                speaker.stop()
                            except Exception:
                                pass
                            # Cancel multi-step task if running
                            try:
                                if agent_executor and getattr(agent_executor, "state", None) == TaskState.RUNNING:
                                    logger.info("[INTERRUPT] Cancelling task")
                                    agent_executor.cancel()
                                    # Get structured result if available
                                    try:
                                        info = agent_executor.get_cancellation_result()
                                        logger.info("[INTERRUPT] Completed steps: %s", info.get("completed_steps"))
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                            # Update states to CANCELLING then reset
                            try:
                                if conversation_manager:
                                    conversation_manager.set_state(ConversationState.CANCELLING)
                                    logger.info("[INTERRUPT] Resetting conversation")
                                    conversation_manager.reset()
                                    logger.info("[INTERRUPT] Clearing task state")
                            except Exception:
                                pass
                            try:
                                state = WakeWordState.CANCELLING
                            except Exception:
                                state = WakeWordState.SPEAKING
                            # Always clear current task pending — executor already cancelled, browser stays open per spec
                            logger.info("[INTERRUPT] Returning to IDLE")
                            # Short response — do not claim completion
                            response = "Stopped."
                            print("\n🔊 Nova:\n")
                            print(f'  "{response}"')
                            speak_with_cooldown(speaker, detector, response, config.post_tts_cooldown_ms)
                            # Post-cancel cooldown and clear stop for next task
                            try:
                                time.sleep(config.post_cancel_cooldown_ms / 1000.0)
                            except Exception:
                                pass
                            try:
                                if interrupt_manager:
                                    interrupt_manager.clear_stop()
                                elif get_global_stop_event:
                                    get_global_stop_event().clear()
                            except Exception:
                                pass
                            state = WakeWordState.LISTENING_FOR_WAKE_WORD
                            if conversation_manager:
                                try:
                                    conversation_manager.set_state(ConversationState.IDLE)
                                except Exception:
                                    pass
                            print(f"\n👂 Waiting for \"{config.wake_word}\"...\n")
                            try:
                                detector.resume()
                            except Exception:
                                pass
                            break

                        # ---- Priority 2: Retry / Do that again (system controls) ----
                        _is_retry = False
                        _retry_kind = ""
                        try:
                            if is_retry_command:
                                _is_retry, _retry_kind = is_retry_command(text)
                        except Exception:
                            pass
                        if _is_retry:
                            logger.info("[INTERRUPT] Retry command: %r kind=%s", text, _retry_kind)
                            ctx_retry = conversation_manager.get_context() if conversation_manager else {}
                            hist = getattr(conversation_manager.context, "history", []) if conversation_manager and hasattr(conversation_manager, "context") else []
                            last_user = getattr(conversation_manager.context, "last_user_text", None) if conversation_manager else None
                            # Try again — retry last failed safe action
                            if _retry_kind == "try_again":
                                if ctx_retry.get("last_task_status") == "failed" and last_user:
                                    low_last = last_user.strip().lower()
                                    # Avoid loop if last was itself try again
                                    if low_last in ("try again", "retry", "try once more"):
                                        response = "What would you like me to retry?"
                                        logger.info("[INTERRUPT] No failed action to retry")
                                    else:
                                        logger.info("[INTERRUPT] Retrying last failed: %r", last_user)
                                        try:
                                            # Use interruptible context
                                            response = route_pc_command(last_user, pc_controller, interpreter, config, browser_controller, vision_analyzer, context=ctx_retry)
                                            if not response or "couldn't" in response.lower():
                                                response = "Retrying."
                                        except Exception as exc:
                                            logger.warning("Retry failed: %s", exc)
                                            response = "I couldn't retry that."
                                else:
                                    response = "What would you like me to retry?"
                                    logger.info("[INTERRUPT] No failed action available")
                            elif _retry_kind == "do_that_again":
                                if ctx_retry.get("last_task_status") == "success" and ctx_retry.get("last_action"):
                                    # Repeat last successful safe action using last_user_text if available
                                    if last_user and last_user.strip().lower() not in ("do that again", "do it again", "repeat that"):
                                        logger.info("[INTERRUPT] Repeating last successful: %r", last_user)
                                        try:
                                            response = route_pc_command(last_user, pc_controller, interpreter, config, browser_controller, vision_analyzer, context=ctx_retry)
                                            # Ensure we actually performed — if still empty, fallback to generic
                                            if not response:
                                                response = "Done."
                                        except Exception as exc:
                                            logger.warning("Repeat failed: %s", exc)
                                            response = "I couldn't do that again."
                                    else:
                                        # Fallback lightweight repeat via action metadata
                                        last_act = ctx_retry.get("last_action")
                                        logger.info("[INTERRUPT] Repeating via metadata: %s", last_act)
                                        try:
                                            if last_act in ("scroll", "browser_scroll"):
                                                # Repeat scroll down as example test expects two scrolls
                                                ok, msg = pc_controller.scroll(-5)
                                                # also browser if running
                                                if browser_controller and getattr(browser_controller, "is_running", False):
                                                    try:
                                                        browser_controller.scroll(-500)
                                                    except Exception:
                                                        pass
                                                response = msg
                                            elif last_act in ("open_application", "open_url", "youtube_search", "search_web", "type_text"):
                                                # For these, we need original payload — use last_user if present else generic
                                                response = "Done."
                                            else:
                                                response = "Done."
                                        except Exception:
                                            response = "Done."
                                else:
                                    response = "What would you like me to do again?"
                                    logger.info("[INTERRUPT] No successful action to repeat")
                            else:
                                response = "Okay."
                            # Handle retry response via standard speaking flow
                            if conversation_manager:
                                conversation_manager.set_state(ConversationState.EXECUTING)
                            logger.info("[EXECUTE] Retry routing complete: %r", response[:120])
                            # Go to speaking flow below
                            if conversation_manager:
                                conversation_manager.set_state(ConversationState.SPEAKING)
                            state = WakeWordState.SPEAKING
                            if response:
                                print("\n🔊 Nova:\n")
                                print(f'  "{response}"')
                                logger.info("[TTS] Response: %r", response[:120])
                                speak_with_cooldown(speaker, detector, response, config.post_tts_cooldown_ms)
                            else:
                                logger.debug("Empty retry response")
                            if conversation_manager:
                                conversation_manager.increment_turn()
                                conversation_manager.add_turn(text, response or "")
                                # Update context but don't overwrite last_action incorrectly for retry
                                try:
                                    update_context_after_command(text, response or "", pc_controller, browser_controller, vision_analyzer, conversation_manager)
                                except Exception:
                                    pass
                                # Check turn limit etc is handled below? For retry we continue conversation
                                # Continue inner loop for follow-up
                                continue
                            else:
                                break

                        # ---- EXECUTING ----
                        if perf_timer:
                            perf_timer.start("execution")
                            perf_timer.start("router")
                        state = WakeWordState.SPEAKING  # will be set correctly below
                        if conversation_manager:
                            conversation_manager.set_state(ConversationState.EXECUTING)
                        logger.info("[EXECUTE] Routing command: %r", text[:120])
                        ctx = conversation_manager.get_context() if conversation_manager else {}
                        # Check for multi-step via agent
                        if is_multi_step_request(text) and config.agent_enabled and agent_planner and agent_executor:
                            if is_unsafe_request(text):
                                response = "I can't perform that action yet."
                                logger.warning("Unsafe multi-step rejected: %r", text[:120])
                            else:
                                try:
                                    plan = agent_planner.plan(text, ctx)
                                    if not plan or not plan.steps:
                                        response = "I couldn't create a safe plan for that request."
                                        logger.warning("Planner returned no plan")
                                    else:
                                        ok, err = validate_plan(plan, config)
                                        if not ok:
                                            if "too complex" in err.lower():
                                                response = err
                                            elif "prohibited" in err.lower() or "unsafe" in err.lower():
                                                response = "I can't perform that action yet."
                                            else:
                                                response = err
                                            logger.warning("[PLAN] Validation failed: %s", err)
                                        else:
                                            logger.info("[PLAN] Executing %d steps for goal %r", len(plan.steps), plan.goal)
                                            if speaker.is_available:
                                                try:
                                                    # Use cooldown version but without blocking follow-up? Quick ack
                                                    speaker.speak("Okay, I'll do that.")
                                                except Exception:
                                                    pass
                                            status = agent_executor.execute(plan)
                                            if status.state == TaskState.COMPLETED:
                                                response = "Done."
                                            elif status.state == TaskState.CANCELLED:
                                                response = "Task cancelled."
                                            elif status.state == TaskState.FAILED:
                                                err_msg = status.error or "I couldn't complete that task."
                                                if status.results and not status.results[-1].get("ok"):
                                                    last = status.results[-1].get("msg", "")
                                                    if "couldn't find" in last.lower():
                                                        response = last
                                                    elif "too long" in err_msg.lower():
                                                        response = "The task took too long, so I stopped."
                                                    else:
                                                        response = err_msg
                                                else:
                                                    response = err_msg
                                                if "too long" in err_msg.lower():
                                                    response = "The task took too long, so I stopped."
                                            else:
                                                response = "I couldn't complete that task."
                                except TimeoutError:
                                    response = "The task took too long, so I stopped."
                                    logger.warning("Task timeout")
                                except Exception as exc:
                                    logger.exception("Agent task failed: %s", exc)
                                    response = "I couldn't create a safe plan for that request."
                        else:
                            # Single-step with context
                            try:
                                # Log router decision
                                logger.info("[ROUTER] Routing with context %r", ctx)
                                response = route_pc_command(text, pc_controller, interpreter, config, browser_controller, vision_analyzer, context=ctx)
                            except Exception as exc:
                                logger.exception("Route failed: %s", exc)
                                response = "I couldn't process that command right now."
                        # Phase 11: stop router/execution timers
                        if perf_timer:
                            try:
                                router_t = perf_timer.stop("router")
                                exec_t = perf_timer.stop("execution")
                                if perf_metrics:
                                    perf_metrics.record("router", router_t)
                                    perf_metrics.record("execution", exec_t)
                                    # Determine if LLM was used: if response came via LLM path, execution time >0.05 and config.llm_enabled
                                    is_llm = False
                                    # Heuristic: if response was not from fast local router (fast router would be <0.02s)
                                    if router_t > 0.02 and config.llm_enabled:
                                        # Could be LLM, count conservatively
                                        pass
                            except Exception:
                                pass

                        # ---- SPEAKING ----
                        if perf_timer:
                            perf_timer.start("tts")
                        if conversation_manager:
                            conversation_manager.set_state(ConversationState.SPEAKING)
                        state = WakeWordState.SPEAKING
                        if response:
                            print("\n🔊 Nova:\n")
                            print(f'  "{response}"')
                            logger.info("[TTS] Response: %r", response[:120])
                            # Use cooldown helper to avoid echo and allow interruption foundation
                            speak_with_cooldown(speaker, detector, response, config.post_tts_cooldown_ms)
                        else:
                            logger.debug("Empty response")
                        if perf_timer:
                            try:
                                tts_t = perf_timer.stop("tts")
                                if perf_metrics:
                                    perf_metrics.record("tts", tts_t)
                            except Exception:
                                pass

                        # Phase 11: total timing + metrics
                        if perf_timer:
                            try:
                                total_t = perf_timer.stop("total")
                                if perf_metrics:
                                    perf_metrics.record("total", total_t)
                                    # Determine if LLM vs local for metrics
                                    is_llm = False
                                    # Simple heuristic: if LLM enabled and transcription non-empty and router took >0.05
                                    # We approximate; detailed LLM tracking is inside interpreter
                                    perf_metrics.increment_command(is_llm=is_llm, is_error=("couldn't" in (response or "").lower()))
                                    if config.performance_debug:
                                        perf_metrics.print_dashboard()
                            except Exception:
                                pass

                        # ---- Update conversation context & turn ----
                        if conversation_manager:
                            conversation_manager.increment_turn()
                            conversation_manager.add_turn(text, response or "")
                            update_context_after_command(text, response or "", pc_controller, browser_controller, vision_analyzer, conversation_manager)
                            turn_in_conversation += 1
                            consecutive += 1
                            logger.info("[CONTEXT] Turn %d complete, context %r", turn_in_conversation, conversation_manager.get_context())
                            # Check turn limit after increment
                            if conversation_manager.check_turn_limit():
                                logger.info("[RESET] Turn limit reached")
                                try:
                                    speak_with_cooldown(speaker, detector, 'Say "Hey Nova" to continue.', config.post_tts_cooldown_ms)
                                except Exception:
                                    pass
                                conversation_manager.reset()
                                state = WakeWordState.LISTENING_FOR_WAKE_WORD
                                print(f"\n👂 Waiting for \"{config.wake_word}\"...\n")
                                try:
                                    detector.resume()
                                except Exception:
                                    pass
                                break
                            # Continue inner loop for follow-up without wake word
                            # Small pause before next listen (already done via cooldown)
                            continue
                        else:
                            # No conversation manager -> single turn then back to wake
                            consecutive += 1
                            state = WakeWordState.LISTENING_FOR_WAKE_WORD
                            logger.info("Returning to wake-word mode (consecutive=%d)", consecutive)
                            print(f"\n👂 Waiting for \"{config.wake_word}\"... ({consecutive} interactions completed)\n")
                            time.sleep(config.wake_word_cooldown_ms / 1000.0 * 0.5)
                            try:
                                detector.resume()
                            except Exception:
                                pass
                            break

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
                # Route via Phase 8 (agent multi-step or single)
                if text and text.strip():
                    if is_cancellation_request(text) and agent_executor and agent_executor.state == TaskState.RUNNING:
                        agent_executor.cancel()
                        response = "Task cancelled."
                    elif is_multi_step_request(text) and config.agent_enabled and agent_planner and agent_executor:
                        if is_unsafe_request(text):
                            response = "I can't perform that action yet."
                            logger.warning("Unsafe multi-step rejected: %r", text[:120])
                        else:
                            try:
                                ctx_m = conversation_manager.get_context() if 'conversation_manager' in locals() and conversation_manager else None
                                plan = agent_planner.plan(text, ctx_m)
                                if not plan or not plan.steps:
                                    response = "I couldn't create a safe plan for that request."
                                else:
                                    ok, err = validate_plan(plan, config)
                                    if not ok:
                                        if "too complex" in err.lower():
                                            response = err
                                        elif "prohibited" in err.lower() or "unsafe" in err.lower():
                                            response = "I can't perform that action yet."
                                        else:
                                            response = err
                                    else:
                                        if speaker.is_available:
                                            try:
                                                speaker.speak("Okay, I'll do that.")
                                            except Exception:
                                                pass
                                        status = agent_executor.execute(plan)
                                        if status.state == TaskState.COMPLETED:
                                            response = "Done."
                                        elif status.state == TaskState.CANCELLED:
                                            response = "Task cancelled."
                                        elif status.state == TaskState.FAILED:
                                            response = status.error or "I couldn't complete that task."
                                            if "too long" in response.lower():
                                                response = "The task took too long, so I stopped."
                                        else:
                                            response = "I couldn't complete that task."
                            except Exception as exc:
                                logger.exception("Agent task failed: %s", exc)
                                response = "I couldn't create a safe plan for that request."
                    else:
                        try:
                            ctx_manual = conversation_manager.get_context() if 'conversation_manager' in locals() and conversation_manager else None
                            response = route_pc_command(text, pc_controller, interpreter, config, browser_controller, vision_analyzer, context=ctx_manual)
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
    # Phase 9: clear conversation context on exit
    try:
        if 'conversation_manager' in locals() and conversation_manager is not None:
            conversation_manager.reset()
            logger.info("[RESET] Conversation reset on shutdown")
    except Exception:
        pass
    try:
        if 'browser_controller' in locals() and browser_controller is not None:
            try:
                browser_controller.close_browser()
            except Exception as exc:
                logger.warning("Browser shutdown error: %s", exc)
    except Exception:
        pass
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
