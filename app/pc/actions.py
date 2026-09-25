"""Command router for Nova Phase 4.

Converts normalized voice text into safe PC actions. One action per
utterance — multi-step is rejected with guidance.

Safe pipeline:
  Voice -> normalize -> intent match -> allowlisted controller call -> response
Never: os.system(user_text) or subprocess with shell user text.
"""

import logging
import re
import urllib.parse
from typing import Tuple, Optional

from app.pc.controller import PCController, WEBSITE_ALIASES, APPLICATION_ALIASES
from app.browser.sites import youtube_search_url, google_search_url

logger = logging.getLogger(__name__)

# Phrases that indicate multiple actions (Phase 8 will handle)
MULTI_ACTION_MARKERS = [
    " and then ",
    " then ",
]


def _normalize(text: str) -> str:
    """Lowercase, collapse whitespace, strip leading hey nova."""
    if not text:
        return ""
    t = text.strip().lower()
    # Remove leading wake word if still present (include common Whisper mishearings: Noah/Noa/Nora)
    for prefix in (
        "hey nova,", "hey nova ", "hey nova:", "nova,",
        "hey noah,", "hey noah ", "hey noah:", "noah,",
        "hey noa,", "hey noa ", "hey noa:", "noa,",
        "hay nova,", "hay nova ", "hay nova:", "hay noah,", "hay noah ",
        "hey nora,", "hey nora ",
    ):
        if t.startswith(prefix):
            t = t[len(prefix):].strip()
            break
    # Collapse whitespace
    t = re.sub(r"\s+", " ", t).strip()
    # Remove trailing punctuation
    t = t.rstrip(".,!?")
    return t


def _detect_multi_action(text: str) -> bool:
    """Heuristically detect multi-step requests like 'open brave and go to youtube'."""
    low = text.lower()
    # Count action verbs
    verbs = ["open", "launch", "start", "run", "go to", "type", "press", "click", "scroll"]
    verb_count = sum(1 for v in verbs if v in low)
    if verb_count >= 2 and any(m in low for m in MULTI_ACTION_MARKERS):
        return True
    # Comma + multiple verbs
    if "," in low and verb_count >= 2:
        # e.g., "open brave, go to youtube, search..."
        if low.count("open") >= 2 or ("open" in low and "go to" in low):
            return True
    return False


def get_supported_commands() -> str:
    return """
Supported (one per utterance):
  - Open app: "open Notepad", "launch Brave", "start Calculator", "run VS Code", "open File Explorer"
  - Open website: "open YouTube", "go to GitHub", "launch Google"
  - Type: "type Hello World" (literally types following text)
  - Press key: "press Enter", "press Escape", "press Tab", "press Space"
  - Hotkey: "press Control C", "press Control V", "press Control A", "press Control Z", "press Alt Tab", "press Windows D"
  - Mouse: "click", "double click", "right click", "scroll up", "scroll down"
  - Windows: "minimize this window", "maximize this window", "switch to Chrome", "show desktop", "close this window"
  - Files: "open Downloads", "create folder called Projects", "find my pdf files", "open resume.pdf"
  - Media/Volume: "increase volume", "set volume to 50", "mute", "pause", "next song", "take screenshot"
  - System: "what's my CPU usage", "how much RAM", "battery level", "am I connected to Wi-Fi", "what's on my screen"
  - Friendly: "hello", "hi", "how are you", "test"
Files: aliases via APPLICATION_ALIASES, websites via WEBSITE_ALIASES, keys via KEY_ALIASES.
"""


def handle_command(text: str, controller: PCController) -> Tuple[bool, str]:
    """Route text to a PC action and return (handled, response).

    handled True means a PC action was attempted (even if failed).
    For non-PC friendly phrases (hello etc) handled False but response still returned.
    For unknown, returns (False, \"I can't perform that action yet.\")

    Multi-action -> (False, \"I can handle one basic action at a time right now.\")
    """
    if not text or not text.strip():
        return False, ""

    raw = text.strip()
    norm = _normalize(text)
    if not norm:
        return False, ""

    logger.info("Routing command: raw=%r norm=%r", raw[:120], norm[:120])

    # Confirmation handling for destructive actions (timeout 10s)
    try:
        from app.confirm.manager import get_confirmation_manager
        cm = get_confirmation_manager()
        if norm in ("yes", "yes please", "confirm", "confirm shutdown", "confirm restart", "confirm delete", "confirm sleep", "go ahead", "proceed", "do it"):
            pending = cm.confirm()
            if pending:
                action = pending.get("action")
                params = pending.get("params", {})
                logger.info("Executing confirmed action: %s %r", action, params)
                # Dispatch with confirm=True where needed
                if action in ("shutdown_pc", "restart_pc", "sleep_pc"):
                    ok, msg = getattr(controller, action)(confirm=True)
                    return True, msg
                if action == "delete_file":
                    ok, msg = controller.delete_file(params.get("path",""))
                    return True, msg
                # generic
                ok, msg = controller.delete_file(params.get("path","")) if action == "delete_file" else (False, "Confirmed.")
                return True, msg
            else:
                # No pending but explicit "confirm <action>" -> direct execution with confirmation
                if norm == "confirm shutdown":
                    ok, msg = controller.shutdown_pc(confirm=True)
                    return True, msg
                if norm == "confirm restart":
                    ok, msg = controller.restart_pc(confirm=True)
                    return True, msg
                if norm == "confirm sleep":
                    ok, msg = controller.sleep_pc(confirm=True)
                    return True, msg
                if norm == "confirm delete":
                    return True, "Which file should I delete? Say 'delete <filename>'."
                # No pending but user said yes — treat as no-op friendly
                if cm.is_pending() is False and norm == "yes":
                    # Might be confirmation for agent? just ignore
                    pass
        if norm in ("no", "cancel", "never mind") and cm.is_pending():
            cm.cancel()
            return True, "Cancelled."
    except Exception:
        pass

    # Accent fix: whisper mishears "open brave" as "oh one room"/"open rail" (Indian accent)
    if norm in ("oh, one room", "oh one room", "oh, one room.", "o one room", "open one room"):
        logger.info("Accent fix: '%s' -> open brave", norm)
        norm = "open brave"
        raw = "open brave"

    # Multi-step guard
    if _detect_multi_action(norm):
        logger.info("Multi-action detected: %r", norm[:120])
        return False, "I can handle one basic action at a time right now."

    # Friendly Phase 2 responses (no PC action) — keep them working
    if "how are you" in norm:
        return False, "I'm doing great. I'm ready for your next command."
    if norm == "hello" or "hello" in norm.split() or norm.startswith("hello "):
        # 'hello' as hello -> friendly, but allow 'hello world' typed? Type takes precedence if explicit "type"
        # If norm is exactly hello-ish, return friendly; type already checked below first
        if norm in ("hello", "hello nova", "hi", "hey"):
            return False, "Hello! I'm Nova." if "hello" in norm else "Hi! I'm ready."
    # More precise: if norm is hello or hi standalone
    if norm in ("hello", "hello nova", "hello noah"):
        return False, "Hello! I'm Nova."
    if norm in ("hi", "hi nova", "hi noah", "hey"):
        return False, "Hi! I'm ready."
    if norm == "test" or norm == "test nova" or norm == "test noah":
        return False, "Voice system is working correctly."
    # Wake-word alone (Whisper mishearing: "hey Noah" -> "hey Nova") - don't error
    if norm in ("hey nova", "hey noah", "hey noa", "hay nova", "hay noah", "hey nora", "nova", "noah", "noa"):
        return False, "Yes? I'm listening."

    # --------------------------------------------------
    # Order matters: most specific first
    # --------------------------------------------------

    # 1. TYPE — "type <anything>" literally
    # Must be checked before other intents that contain 'type'
    if norm.startswith("type "):
        payload = raw.strip()[len("type "):].lstrip()  # preserve original case after "type "
        # Also handle "type hello world" where normalize removed type — use raw extraction preserving case
        # Fallback: extract after first "type " case-insensitive
        m = re.match(r"(?i)^type\s+(.+)$", raw.strip())
        if m:
            payload = m.group(1)
        # Do NOT interpret payload
        ok, msg = controller.type_text(payload)
        if ok:
            return True, "Done."
        else:
            return True, msg

    # 2. HOTKEY — "press control c", "press ctrl c", "press alt tab", etc.
    # Check before generic press key
    hotkey_match = re.match(r"^(press\s+)?(control|ctrl)\s+([a-z0-9])$", norm)
    if hotkey_match:
        key = hotkey_match.group(3)
        ok, msg = controller.hotkey("ctrl", key)
        return True, msg
    # ctrl+shift combos
    hotkey_match2 = re.match(r"^(press\s+)?(control|ctrl)\s+shift\s+([a-z])$", norm)
    if hotkey_match2:
        key = hotkey_match2.group(3)
        ok, msg = controller.hotkey("ctrl", "shift", key)
        return True, msg
    # alt tab, alt f4, win d/e/r/l
    if norm in ("press alt tab", "alt tab", "press alt+tab"):
        ok, msg = controller.hotkey("alt", "tab")
        return True, msg
    if norm in ("press alt f4", "alt f4"):
        ok, msg = controller.hotkey("alt", "f4")
        return True, msg
    if norm in ("press windows d", "press window d", "press win d", "win d", "windows d"):
        ok, msg = controller.hotkey("win", "d")
        return True, msg
    if norm in ("press windows e", "press win e", "win e"):
        ok, msg = controller.hotkey("win", "e")
        return True, msg
    # Generic hotkey pattern "press control a" etc already handled; catch remaining allowlisted
    # Explicit ctrl+s/x/y/n/o/f/p/w
    m_hot = re.match(r"^press\s+(control|ctrl)\s+([a-z])$", norm)
    if m_hot and m_hot.group(2) in ("s", "x", "y", "n", "o", "f", "p", "w", "a", "c", "v", "z"):
        ok, msg = controller.hotkey("ctrl", m_hot.group(2))
        return True, msg

    # 3. PRESS KEY — "press enter", "press escape", etc.
    if norm.startswith("press "):
        key_part = norm[len("press "):].strip()
        # Remove "control" already handled, so remaining is single key
        # Handle "press enter" -> key = enter
        # Also handle "press page up" etc
        ok, msg = controller.press_key(key_part)
        # If press_key failed, maybe it was "press control c" already handled, else unknown key
        if "can't press" not in msg.lower() or key_part in ("enter", "escape", "tab", "space", "backspace", "delete", "up", "down", "left", "right", "home", "end", "page up", "page down"):
            return True, msg
        # If unknown key but press prefix, still return that response (allowlisted safety)
        # Don't fall through to open — it's a press intent
        return True, msg

    # 4. SCROLL — "scroll up/down" etc.
    if norm in ("scroll up", "scroll down", "scroll"):
        amount = controller.default_scroll if "up" in norm else -controller.default_scroll if "down" in norm else controller.default_scroll
        # default scroll up if just "scroll"
        if norm == "scroll":
            amount = -controller.default_scroll  # default down
        ok, msg = controller.scroll(amount)
        return True, msg
    if norm.startswith("scroll "):
        rest = norm[len("scroll "):].strip()
        if "up" in rest:
            ok, msg = controller.scroll(controller.default_scroll)
            return True, msg
        if "down" in rest:
            ok, msg = controller.scroll(-controller.default_scroll)
            return True, msg

    # 5. CLICK variants
    if norm in ("click", "left click", "single click"):
        ok, msg = controller.click()
        return True, msg
    if norm in ("double click", "double-click", "doubleclick"):
        ok, msg = controller.double_click()
        return True, msg
    if norm in ("right click", "right-click", "rightclick"):
        ok, msg = controller.right_click()
        return True, msg

    # 5a. WINDOW MANAGEMENT — minimize/maximize/close/switch/desktop/snap
    if any(p in norm for p in ("minimize this", "minimize current", "minimize window", "minimise")):
        ok, msg = controller.minimize_window()
        return True, msg
    if any(p in norm for p in ("maximize this", "maximize current", "maximize window")):
        ok, msg = controller.maximize_window()
        return True, msg
    if norm in ("restore this window", "restore window", "restore this"):
        ok, msg = controller.restore_window()
        return True, msg
    if norm in ("close this window", "close this app", "close current window", "close window", "exit window"):
        ok, msg = controller.close_window()
        return True, msg
    if norm in ("show desktop", "show my desktop", "minimize all"):
        ok, msg = controller.show_desktop()
        return True, msg
    if norm in ("show all windows", "show my open windows", "show windows"):
        ok, msg = controller.hotkey("win", "tab")
        return True, msg
    # switch window
    m = re.match(r"^(?:switch to|go to|open)\s+(.+)$", norm)
    if m and any(w in norm for w in ("switch to", "go to")) and "youtube" not in norm and "google" not in norm:
        target = m.group(1).strip()
        # Only treat as window switch if target looks like app name already running, not a website open
        if target in APPLICATION_ALIASES or target in ("chrome", "brave", "vs code", "notepad", "calculator", "explorer", "word", "excel", "spotify", "discord"):
            ok, msg = controller.switch_window(target)
            return True, msg
        # Try generic switch — if phrase is "switch window" or "switch to previous"
        if target in ("previous window", "previous app", "last window", "last app"):
            ok, msg = controller.switch_window(target)
            return True, msg
    if norm in ("switch window", "switch windows", "alt tab", "switch to previous window", "go to previous app", "previous window"):
        ok, msg = controller.switch_window("previous")
        return True, msg
    if norm.startswith("switch to ") and len(norm.split()) <= 4:
        target = norm[len("switch to "):].strip()
        if target and target not in WEBSITE_ALIASES:
            ok, msg = controller.switch_window(target)
            if "couldn't find" not in msg:
                return True, msg
    # snap/move
    if "snap" in norm or "move this window" in norm or "put this window" in norm:
        if "left" in norm:
            ok, msg = controller.move_window("left")
            return True, msg
        if "right" in norm:
            ok, msg = controller.move_window("right")
            return True, msg
        if "top" in norm or "up" in norm:
            ok, msg = controller.move_window("top")
            return True, msg
        if "bottom" in norm or "down" in norm:
            ok, msg = controller.move_window("down")
            return True, msg
    # close application specific
    m = re.match(r"^(?:close|exit|quit)\s+(.+)$", norm)
    if m:
        target = m.group(1).strip()
        # Filter: "close this tab" is browser, not app
        if target in ("this tab", "current tab", "this browser tab"):
            return False, ""
        if target in ("this app", "this application", "current window", "this window", "this"):
            ok, msg = controller.close_window()
            return True, msg
        # Check if target is app alias
        if target in APPLICATION_ALIASES or target in ("chrome", "brave", "notepad", "vs code", "code", "calculator", "explorer", "word", "excel", "spotify", "discord", "slack", "zoom"):
            ok, msg = controller.close_application(target)
            return True, msg
        if 1 <= len(target.split()) <= 3:
            # Try generic close
            ok, msg = controller.close_application(target)
            if ok or "don't know" not in msg:
                return True, msg

    # 5b. FILE EXPLORER & FILE OPERATIONS
    # open known folders: downloads/documents/desktop/pictures etc
    if any(p in norm for p in ("open downloads", "open my downloads", "downloads folder", "open documents", "open desktop", "open pictures", "open videos", "open music")):
        for alias in ("downloads", "documents", "desktop", "pictures", "videos", "music"):
            if alias in norm:
                ok, msg = controller.open_folder(alias)
                return True, msg
    # create folder
    m = re.match(r"^(?:create|make)\s+(?:a\s+)?(?:new\s+)?folder\s+(?:called|named|with name)?\s*(.+)?$", norm)
    if m:
        name = (m.group(1) or "").strip().rstrip(" .")
        # Clean up common filler
        name = re.sub(r"^(called|named)\s+", "", name).strip()
        name = name.strip('"\'')
        if name and len(name) < 50 and re.match(r"^[\w\-\s]+$", name):
            ok, msg = controller.create_folder(name)
            return True, msg
        if "folder" in norm and not name:
            return True, "What should I name the folder?"
    # search files
    if norm.startswith("find ") and ("file" in norm or "folder" in norm or "pdf" in norm or ".pdf" in norm or "resume" in norm):
        # "find my pdf files", "find files named resume", "find python files"
        q = norm[len("find "):].strip()
        # Remove filler
        q = re.sub(r"^(my|the)\s+", "", q)
        q = re.sub(r"\s+files?$", "", q)
        q = q.strip()
        if q and len(q) < 100:
            ok, msg = controller.search_files(q)
            return True, msg
    if norm.startswith("search ") and ("file" in norm or "folder" in norm):
        q = re.sub(r"^search\s+(?:for\s+)?", "", norm).strip()
        if q:
            ok, msg = controller.search_files(q)
            return True, msg
    # open file / folder
    m = re.match(r"^open\s+(.+?\.(?:pdf|docx?|xlsx?|pptx?|txt|png|jpg|jpeg|zip|py|js|html))$", norm)
    if m:
        path = m.group(1).strip()
        ok, msg = controller.open_file(path)
        return True, msg
    # what apps installed
    if any(p in norm for p in ("what apps", "installed apps", "list apps", "show apps", "what applications")):
        ok, msg = controller.list_apps()
        return True, msg
    if ("is " in norm and "installed" in norm) or ("find " in norm and any(a in norm for a in APPLICATION_ALIASES)):
        m = re.search(r"(?:is|find)\s+(.+?)\s+installed", norm)
        if m:
            app = m.group(1).strip()
            ok, msg = controller.find_app(app)
            return True, msg
        m = re.match(r"^find\s+(.+)$", norm)
        if m and m.group(1).strip() in APPLICATION_ALIASES:
            ok, msg = controller.find_app(m.group(1).strip())
            return True, msg

    # 5c. VOLUME / MEDIA
    if norm in ("increase volume", "turn the volume up", "volume up", "raise volume", "louder", "turn volume up"):
        ok, msg = controller.volume_up()
        return True, msg
    if norm in ("decrease volume", "turn the volume down", "volume down", "lower volume", "lower the volume", "quieter", "turn volume down"):
        ok, msg = controller.volume_down()
        return True, msg
    m = re.match(r"^(?:set\s+)?volume\s+to\s+(\d{1,3})\s*%?$", norm)
    if m:
        lvl = int(m.group(1))
        if 0 <= lvl <= 100:
            ok, msg = controller.set_volume(lvl)
            return True, msg
    if norm in ("mute", "mute volume", "mute audio", "mute the volume"):
        ok, msg = controller.mute()
        return True, msg
    if norm in ("unmute", "unmute volume", "unmute audio"):
        ok, msg = controller.unmute()
        return True, msg
    # media keys
    if norm in ("pause", "pause music", "pause song", "pause video", "pause playback"):
        ok, msg = controller.media_play_pause()
        return True, msg
    if norm in ("resume", "play", "resume music", "resume song", "continue"):
        # Note: bare "play" without query is media resume, not youtube search (youtube needs query)
        if norm == "play" or norm in ("resume", "resume music"):
            ok, msg = controller.media_play_pause()
            return True, msg
    if norm in ("next song", "next track", "skip", "skip song", "next video", "go to next video"):
        ok, msg = controller.media_next()
        return True, msg
    if norm in ("previous song", "previous track", "go back song", "previous video"):
        ok, msg = controller.media_previous()
        return True, msg

    # 5d. SYSTEM INFO
    if any(p in norm for p in ("cpu usage", "cpu info", "processor usage")):
        ok, msg = controller.cpu_info()
        return True, msg
    if any(p in norm for p in ("ram usage", "memory usage", "how much ram", "how much memory")):
        ok, msg = controller.memory_info()
        return True, msg
    if any(p in norm for p in ("storage", "disk space", "free storage", "how much storage", "how much space", "show my drives", "disk usage")):
        ok, msg = controller.storage_info()
        return True, msg
    if any(p in norm for p in ("battery level", "battery percentage", "how much battery", "is the charger", "battery status")):
        ok, msg = controller.battery_info()
        return True, msg
    if any(p in norm for p in ("network status", "wifi status", "internet", "am i connected", "is wifi on", "what's my ip", "my ip address", "current network")):
        ok, msg = controller.network_info()
        return True, msg
    if any(p in norm for p in ("system information", "system info", "computer info", "windows version", "what windows", "computer name", "what's my gpu")):
        ok, msg = controller.system_info()
        return True, msg
    if any(p in norm for p in ("what's using", "most cpu", "most memory", "running applications", "is chrome running", "is vs code running", "process info", "show running")):
        q = norm
        ok, msg = controller.process_info(q)
        return True, msg
    # time/date
    if any(p in norm for p in ("what time is it", "what's the time", "current time", "what time", "what's today's date", "what day is today", "today's date")):
        ok, msg = controller.get_time()
        return True, msg
    # calculate
    if norm.startswith("calculate ") or norm.startswith("what is ") and any(op in norm for op in ("plus", "minus", "times", "divided", "percent", "+", "-", "*", "/")):
        expr = re.sub(r"^(calculate|what is)\s+", "", norm).strip()
        ok, msg = controller.calculate(expr)
        return True, msg
    # screenshot
    if any(p in norm for p in ("take a screenshot", "take screenshot", "screenshot my screen", "capture the screen", "capture screen")):
        ok, msg = controller.take_screenshot()
        return True, msg
    # clipboard
    if norm in ("what's in my clipboard", "what is in my clipboard", "show clipboard", "read clipboard"):
        ok, msg = controller.clipboard_read()
        return True, msg
    if norm in ("clear my clipboard", "clear clipboard", "empty clipboard"):
        ok, msg = controller.clipboard_clear()
        return True, msg
    # copy/paste/select etc via text
    if norm in ("copy this", "copy that", "copy", "copy the selected text"):
        ok, msg = controller.hotkey("ctrl", "c")
        return True, msg
    if norm in ("paste", "paste it", "paste that"):
        ok, msg = controller.hotkey("ctrl", "v")
        return True, msg
    if norm in ("cut that", "cut this", "cut"):
        ok, msg = controller.hotkey("ctrl", "x")
        return True, msg
    if norm in ("select all", "select everything", "select the next word", "move to beginning", "move to end"):
        if "select all" in norm or "select everything" in norm:
            ok, msg = controller.hotkey("ctrl", "a")
            return True, msg
        if "beginning" in norm:
            ok, msg = controller.press_key("home")
            return True, msg
        if "end" in norm:
            ok, msg = controller.press_key("end")
            return True, msg
    if norm in ("undo", "undo that"):
        ok, msg = controller.hotkey("ctrl", "z")
        return True, msg
    if norm in ("redo", "redo that"):
        ok, msg = controller.hotkey("ctrl", "y")
        return True, msg
    # settings — handle both "settings" and singular "setting" (Whisper often drops the 's')
    if "open" in norm and ("settings" in norm or "setting" in norm):
        # "open wifi settings", "open bluetooth settings" etc
        for page in ("wifi", "bluetooth", "display", "sound", "personalization", "update", "privacy", "apps", "accounts", "system"):
            if page in norm:
                ok, msg = controller.open_settings(page)
                return True, msg
        if "settings" in norm or "setting" in norm:
            ok, msg = controller.open_settings("")
            return True, msg
    # lock / shutdown / restart / sleep
    if norm in ("lock my pc", "lock pc", "lock the pc", "lock computer"):
        ok, msg = controller.lock_pc()
        return True, msg
    if any(p in norm for p in ("shut down", "shutdown", "restart", "sleep", "hibernate")):
        try:
            from app.confirm.manager import get_confirmation_manager
            cm = get_confirmation_manager()
        except Exception:
            cm = None
        if "shut down" in norm or "shutdown" in norm:
            # require confirmation
            if "confirm" in norm:
                ok, msg = controller.shutdown_pc(confirm=True)
                return True, msg
            else:
                if cm:
                    cm.request("shutdown_pc", {}, "")
                ok, msg = controller.shutdown_pc(confirm=False)
                return True, msg
        if "restart" in norm:
            if "confirm" in norm:
                ok, msg = controller.restart_pc(confirm=True)
                return True, msg
            else:
                if cm:
                    cm.request("restart_pc", {}, "")
                ok, msg = controller.restart_pc(confirm=False)
                return True, msg
        if "sleep" in norm or "hibernate" in norm:
            if "confirm" in norm:
                ok, msg = controller.sleep_pc(confirm=True)
                return True, msg
            else:
                if cm:
                    cm.request("sleep_pc", {}, "")
                ok, msg = controller.sleep_pc(confirm=False)
                return True, msg
    # delete file — requires confirmation
    if "delete" in norm and ("file" in norm or "folder" in norm or "this" in norm or "that" in norm):
        # Extract path if provided, else ask
        m = re.search(r"delete\s+(?:this\s+)?(?:file\s+)?(.+)", norm)
        path = (m.group(1).strip() if m else "").strip()
        # Filter generic "delete this file" with no name -> ask confirmation for current
        if not path or path in ("this file", "this", "that", "file", "folder"):
            # Ask confirmation
            try:
                from app.confirm.manager import get_confirmation_manager
                cm = get_confirmation_manager()
                # For demo, treat "this file" as no path yet — ask
                return True, "Are you sure you want me to delete it? Say 'confirm delete'."
            except Exception:
                return True, "Are you sure you want me to delete it? Say 'confirm delete'."
        # Has path
        try:
            from app.confirm.manager import get_confirmation_manager
            cm = get_confirmation_manager()
            if "confirm" in norm:
                ok, msg = controller.delete_file(path)
                return True, msg
            else:
                cm.request("delete_file", {"path": path}, "")
                return True, f"This will move {path} to the Recycle Bin. Say 'confirm delete' to continue."
        except Exception:
            pass
        # Fallback without manager
        ok, msg = controller.delete_file(path)
        return True, msg
    if "rename" in norm:
        m = re.search(r"rename\s+(.+?)\s+to\s+(.+)", norm)
        if m:
            old = m.group(1).strip()
            new = m.group(2).strip()
            ok, msg = controller.rename_file(old, new)
            return True, msg
    if "copy" in norm and "file" in norm and "to" in norm:
        m = re.search(r"copy\s+(?:this\s+)?(?:file\s+)?(?:(.+?)\s+)?to\s+(.+)", norm)
        if m:
            src = (m.group(1) or "this file").strip()
            dst = m.group(2).strip()
            # For natural "copy this file to Documents" — need to infer src as current file, ask clarification if needed
            if src in ("this file", "this", "that"):
                return True, "Which file should I copy? Please say the file name."
            try:
                import shutil, os
                # Resolve dst as folder alias
                from app.tools.file_tools import _resolve_known_folder
                dst_path = _resolve_known_folder(dst) or dst
                if os.path.isdir(dst_path):
                    dst_path = os.path.join(dst_path, os.path.basename(src))
                shutil.copy2(src, dst_path)
                return True, f"Copied to {dst}."
            except Exception as exc:
                return True, f"I couldn't copy: {exc}"
    if "move" in norm and "file" in norm and "to" in norm:
        m = re.search(r"move\s+(?:this\s+)?(?:file\s+)?(?:(.+?)\s+)?to\s+(.+)", norm)
        if m:
            src = (m.group(1) or "this file").strip()
            dst = m.group(2).strip()
            if src in ("this file", "this", "that"):
                return True, "Which file should I move? Please say the file name."
            try:
                import shutil, os
                from app.tools.file_tools import _resolve_known_folder
                dst_path = _resolve_known_folder(dst) or dst
                if os.path.isdir(dst_path):
                    dst_path = os.path.join(dst_path, os.path.basename(src))
                shutil.move(src, dst_path)
                return True, f"Moved to {dst}."
            except Exception as exc:
                return True, f"I couldn't move: {exc}"
    # what can you do help
    if norm in ("what can you do", "what can you do nova", "help", "help me", "how do i control windows", "what are your commands"):
        return False, "I can open and control apps, manage windows, type and click, control your browser, search files, control media and volume, read system information, understand your screen, and handle short multi-step tasks. Try: open Chrome, minimize window, set volume to 50, take screenshot, or what's my battery level."

    # 5b. SEARCH IN BRAVE — handle search/youtube before open (per user: Image 2 Brave, not Image 1 small overlay)
    # All youtube/google searches should open in Brave, not Playwright overlay.
    # "search youtube for X", "find X on youtube", "play X", "search X"
    # Delegate "play ... on youtube" and generic "play ... song" to agent (multi-step search + click) — don't handle as single search
    if norm.startswith("play ") and "youtube" in norm:
        # e.g., "play daylight song on new youtube" -> let agent do search + play first video
        return False, ""
    # Also delegate any "search ... and play ..." combined request to agent
    if "play" in norm and "youtube" in norm and "search" in norm:
        return False, ""
    # SIMPLE ENGLISH: any "play <name>" -> delegate to agent for YouTube search+play (so "play guman" works)
    if norm.startswith("play ") and len(norm.split()) >= 2:
        return False, ""
    # Generic play song without explicit youtube should also play in YouTube (Image: Play the delay song)
    if norm.startswith("play ") and ("song" in norm or "music" in norm):
        return False, ""
    youtube_patterns = [
        r"^(?:search\s+youtube\s+for|search\s+youtube|youtube\s+search)\s+(.+)$",
        r"^(?:find|look\s*up)\s+(.+)\s+on\s+(?:new\s+)?youtube$",
        r"^(?:search\s+for\s+)?(.+?)\s+on\s+(?:new\s+)?youtube$",
        r"^play\s+(.+?)(?:\s+on\s+(?:new\s+)?youtube)?$",
    ]
    for pat in youtube_patterns:
        mm = re.match(pat, norm)
        if mm:
            query = mm.group(1).strip().rstrip(" .")
            # Clean trailing filler like "on new", "song on new" already handled, strip "on new"
            query = re.sub(r"\s+on\s+new\s*$", "", query, flags=re.IGNORECASE).strip()
            query = re.sub(r"\s+new\s*$", "", query, flags=re.IGNORECASE).strip()
            if query and query not in ("youtube",) and len(query) > 1:
                # Avoid false positive where query is app-like
                # e.g., "play youtube" alone is already handled as open
                if query.lower() in WEBSITE_ALIASES:
                    continue
                # Clean query that still contains leading "play " or trailing "song on new youtube"
                if query.lower().startswith("play "):
                    query = query[5:].strip()
                url = youtube_search_url(query)
                ok, msg = controller.open_url(url)
                return True, msg
    # Also direct "search youtube for X" explicit
    if norm.startswith("search youtube for "):
        q = norm[len("search youtube for "):].strip()
        if q:
            url = youtube_search_url(q)
            ok, msg = controller.open_url(url)
            return True, msg
    if norm.startswith("search youtube "):
        q = norm[len("search youtube "):].strip()
        if q:
            url = youtube_search_url(q)
            ok, msg = controller.open_url(url)
            return True, msg
    # Google / generic search -> Brave Google
    if "youtube" not in norm:
        mm = re.match(r"^search\s+google\s+for\s+(.+)$", norm)
        if mm:
            q = mm.group(1).strip()
            url = google_search_url(q)
            ok, msg = controller.open_url(url)
            return True, msg
        mm = re.match(r"^google\s+(.+)$", norm)
        if mm:
            q = mm.group(1).strip()
            if q and len(q) > 2:
                url = google_search_url(q)
                ok, msg = controller.open_url(url)
                return True, msg
        mm = re.match(r"^search\s+(?:for\s+)?(.+)$", norm)
        if mm:
            q = mm.group(1).strip()
            if q and len(q) > 1 and "youtube" not in q:
                # Don't handle "search brave" etc.
                if q.lower() not in APPLICATION_ALIASES and q.lower() not in WEBSITE_ALIASES:
                    url = google_search_url(q)
                    ok, msg = controller.open_url(url)
                    return True, msg

    # 6. OPEN APPLICATION — check app FIRST so "open spotify/vlc/word" opens desktop app (simple English)
    # All application open commands — expanded allowlist in controller.py
    for trig in ("open ", "launch ", "start ", "run ", "go to "):
        if norm.startswith(trig):
            target = norm[len(trig):].strip().rstrip(" .")
            # Ambiguous generic browser should not be fast-path — let LLM clarify
            if target in ("browser", "my browser", "the browser", "my browser please", "the browser please"):
                logger.info("Ambiguous browser request: %r -> defer to LLM/clarification", target)
                return False, "I can't perform that action yet."
            # Direct alias match
            if target in APPLICATION_ALIASES:
                ok, msg = controller.open_application(target)
                return True, msg
            # Word-boundary alias match (handles "spotify app", "vlc player")
            for alias in APPLICATION_ALIASES:
                if alias == target or target == alias:
                    ok, msg = controller.open_application(alias)
                    return True, msg
                if alias in target and (alias in target.split() or f" {alias} " in f" {target} " or target.startswith(alias + " ") or target.endswith(" " + alias)):
                    ok, msg = controller.open_application(alias)
                    if ok or "don't know" not in msg:
                        return True, msg
            # Reverse match: target is substring of alias (e.g., "code" -> "vs code")
            for alias in APPLICATION_ALIASES:
                if target in alias and len(target.split()) == 1 and len(alias.split()) <= 2:
                    if alias.endswith(" " + target) or alias == target:
                        ok, msg = controller.open_application(alias)
                        return True, msg
            # If looks like URL, prefer website fallback below — don't return yet, break to website check
            if "." in target or target.startswith("http"):
                # Defer to website open below
                break
            # Plausible app name (1-3 words) — try generic controller fallback (opens any installed app)
            if 1 <= len(target.split()) <= 4:
                # Only try as app if not obviously a website phrase
                if target not in WEBSITE_ALIASES and not any(target == w or target.startswith(w + " ") for w in WEBSITE_ALIASES):
                    ok, msg = controller.open_application(target)
                    # If controller could handle (generic fallback), return it
                    if ok or "don't know" not in msg:
                        return True, msg
            # No app match — fall through to website check
            break

    # 7. OPEN WEBSITE — fallback if not handled as app (youtube, google, etc.)
    website_triggers = ("open ", "launch ", "start ", "run ", "go to ", "goto ")
    for trig in website_triggers:
        if norm.startswith(trig):
            target = norm[len(trig):].strip().rstrip(" .")
            is_website = False
            matched_alias = None
            if target in WEBSITE_ALIASES:
                is_website = True
                matched_alias = target
            else:
                for alias in WEBSITE_ALIASES:
                    if alias == target or target.startswith(alias + " ") or target.endswith(" " + alias) or f" {alias} " in f" {target} ":
                        is_website = True
                        matched_alias = alias
                        break
            if is_website:
                ok, msg = controller.open_url(matched_alias or target)
                return True, msg
            break
    # Bare website alias without trigger (e.g., just "youtube")
    if norm in WEBSITE_ALIASES:
        # Only if not already handled as app (e.g., spotify app vs website)
        if norm not in APPLICATION_ALIASES:
            ok, msg = controller.open_url(norm)
            return True, msg
        # If alias exists in both, prefer app for bare word? For youtube bare still website
        if norm in ("youtube", "google", "github", "gmail"):
            ok, msg = controller.open_url(norm)
            return True, msg

    # 8. Also handle "open <url>" without website mapping but looks like domain
    if norm.startswith("open ") and ("." in norm or "http" in norm):
        target = norm[len("open "):].strip()
        ok, msg = controller.open_url(target)
        return True, msg

    # 9. Fallback: legacy hello etc already handled; if still unknown -> safe reject
    # Check for dangerous patterns explicitly and reject (never execute)
    # Skip if already confirmed (e.g. "confirm shutdown" handled above)
    dangerous = ["delete", "format", "rm ", "shutdown", "kill ", "uninstall", "password", "send email", "send message"]
    if "confirm" not in norm and any(d in norm for d in dangerous):
        logger.warning("Rejected potentially dangerous command: %r", norm[:120])
        return False, "I can't perform that action yet."

    # Unknown command
    logger.info("Unsupported command: %r", norm[:120])
    return False, "I can't perform that action yet."


def execute_structured_action(data: dict, controller: PCController) -> tuple[bool, str]:
    """Execute validated structured action via PC controller. Returns (ok, response)."""
    if not isinstance(data, dict):
        return False, "I couldn't understand that command."
    action = data.get("action", "")
    if action == "unsupported":
        reason = data.get("reason", "")
        logger.info("LLM unsupported: %r", reason)
        return False, "I can't perform that action yet."
    if action == "clarification":
        msg = data.get("message", "Which option should I use?")
        logger.info("LLM clarification: %r", msg)
        return False, msg

    try:
        if action == "open_application":
            app = data.get("application", "")
            ok, msg = controller.open_application(app)
            return ok, msg if ok else msg
        if action == "close_application":
            app = data.get("application") or data.get("target") or ""
            ok, msg = controller.close_application(app)
            return ok, msg
        if action in ("minimize_window", "maximize_window", "restore_window", "close_window", "show_desktop"):
            fn = getattr(controller, action, None)
            if fn:
                ok, msg = fn()
                return ok, msg
        if action == "switch_window":
            target = data.get("target") or data.get("application") or ""
            ok, msg = controller.switch_window(target)
            return ok, msg
        if action == "move_window":
            direction = data.get("direction", "left")
            ok, msg = controller.move_window(direction)
            return ok, msg
        if action == "open_url":
            website = data.get("website")
            url = data.get("url")
            target = website if website else url
            if not target:
                return False, "I couldn't understand that command."
            # website vs url
            if website:
                ok, msg = controller.open_url(website)
            else:
                ok, msg = controller.open_url(url)
            return ok, msg
        if action == "type_text":
            text = data.get("text", "")
            ok, msg = controller.type_text(text)
            return ok, msg
        if action == "press_key":
            key = data.get("key", "")
            ok, msg = controller.press_key(key)
            return ok, msg
        if action == "hotkey":
            keys = data.get("keys", [])
            if not isinstance(keys, list):
                return False, "I couldn't understand that command."
            ok, msg = controller.hotkey(*keys)
            return ok, msg
        if action in ("copy", "paste", "cut", "select_all", "undo", "redo"):
            mapping = {"copy": ("ctrl","c"), "paste": ("ctrl","v"), "cut": ("ctrl","x"), "select_all": ("ctrl","a"), "undo": ("ctrl","z"), "redo": ("ctrl","y")}
            keys = mapping.get(action, ())
            if keys:
                ok, msg = controller.hotkey(*keys)
                return ok, msg
        if action == "scroll":
            amount = data.get("amount")
            if amount is None:
                direction = data.get("direction", "")
                if isinstance(direction, str) and direction.lower() == "up":
                    amount = controller.default_scroll
                elif isinstance(direction, str) and direction.lower() == "down":
                    amount = -controller.default_scroll
                else:
                    amount = controller.default_scroll
            ok, msg = controller.scroll(int(amount))
            return ok, msg
        if action == "click":
            ok, msg = controller.click()
            return ok, msg
        if action == "double_click":
            ok, msg = controller.double_click()
            return ok, msg
        if action == "right_click":
            ok, msg = controller.right_click()
            return ok, msg
        if action == "move_mouse":
            x = data.get("x", 0); y = data.get("y", 0)
            ok, msg = controller.move_mouse(int(x), int(y))
            return ok, msg
        # File ops
        if action == "open_folder":
            folder = data.get("folder") or data.get("path") or data.get("target") or ""
            ok, msg = controller.open_folder(folder)
            return ok, msg
        if action == "open_file":
            path = data.get("path") or data.get("file") or ""
            ok, msg = controller.open_file(path)
            return ok, msg
        if action == "search_files":
            query = data.get("query") or data.get("text") or ""
            directory = data.get("directory") or ""
            ok, msg = controller.search_files(query, directory)
            return ok, msg
        if action == "create_folder":
            path = data.get("path") or data.get("folder") or data.get("name") or ""
            ok, msg = controller.create_folder(path)
            return ok, msg
        if action in ("rename_file", "rename_folder"):
            old = data.get("old") or data.get("src") or data.get("path") or ""
            new = data.get("new") or data.get("dst") or data.get("target") or ""
            ok, msg = controller.rename_file(old, new)
            return ok, msg
        if action in ("copy_file", "move_file"):
            src = data.get("src") or data.get("old") or ""
            dst = data.get("dst") or data.get("new") or ""
            # For copy/move use simple rename logic with copy
            if action == "copy_file":
                try:
                    import shutil, os
                    shutil.copy2(src, dst)
                    return True, f"Copied to {dst}."
                except Exception as exc:
                    return False, f"I couldn't copy: {exc}"
            else:
                try:
                    import shutil
                    shutil.move(src, dst)
                    return True, f"Moved to {dst}."
                except Exception as exc:
                    return False, f"I couldn't move: {exc}"
        if action == "delete_file":
            path = data.get("path") or data.get("file") or ""
            ok, msg = controller.delete_file(path)
            return ok, msg
        if action == "list_apps":
            ok, msg = controller.list_apps()
            return ok, msg
        if action == "find_app":
            app = data.get("application") or data.get("target") or ""
            ok, msg = controller.find_app(app)
            return ok, msg
        # Media
        if action == "volume_up":
            ok, msg = controller.volume_up()
            return ok, msg
        if action == "volume_down":
            ok, msg = controller.volume_down()
            return ok, msg
        if action == "set_volume":
            lvl = data.get("level") or data.get("volume") or data.get("amount") or 50
            ok, msg = controller.set_volume(int(lvl))
            return ok, msg
        if action == "mute":
            ok, msg = controller.mute()
            return ok, msg
        if action == "unmute":
            ok, msg = controller.unmute()
            return ok, msg
        if action == "media_play_pause":
            ok, msg = controller.media_play_pause()
            return ok, msg
        if action == "media_next":
            ok, msg = controller.media_next()
            return ok, msg
        if action == "media_previous":
            ok, msg = controller.media_previous()
            return ok, msg
        # Screenshot/clipboard
        if action == "take_screenshot":
            ok, msg = controller.take_screenshot()
            return ok, msg
        if action == "clipboard_read":
            ok, msg = controller.clipboard_read()
            return ok, msg
        if action == "clipboard_clear":
            ok, msg = controller.clipboard_clear()
            return ok, msg
        # Settings/power
        if action == "open_settings":
            page = data.get("page") or data.get("target") or ""
            ok, msg = controller.open_settings(page)
            return ok, msg
        if action == "lock_pc":
            ok, msg = controller.lock_pc()
            return ok, msg
        if action in ("shutdown_pc", "restart_pc", "sleep_pc"):
            confirm = bool(data.get("confirm"))
            fn = getattr(controller, action, None)
            if fn:
                ok, msg = fn(confirm=confirm)
                return ok, msg
        # System info
        if action == "system_info":
            ok, msg = controller.system_info()
            return ok, msg
        if action == "cpu_info":
            ok, msg = controller.cpu_info()
            return ok, msg
        if action == "memory_info":
            ok, msg = controller.memory_info()
            return ok, msg
        if action == "storage_info":
            ok, msg = controller.storage_info()
            return ok, msg
        if action == "battery_info":
            ok, msg = controller.battery_info()
            return ok, msg
        if action == "network_info":
            ok, msg = controller.network_info()
            return ok, msg
        if action == "process_info":
            q = data.get("query") or data.get("target") or ""
            ok, msg = controller.process_info(q)
            return ok, msg
        if action == "get_time":
            ok, msg = controller.get_time()
            return ok, msg
        if action == "calculate":
            expr = data.get("expression") or data.get("text") or ""
            ok, msg = controller.calculate(expr)
            return ok, msg
    except Exception as exc:
        logger.exception("Structured action execution failed %r: %s", data, exc)
        return False, "I couldn't perform that action."

    return False, "I couldn't understand that command."
