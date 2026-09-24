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
    dangerous = ["delete", "format", "rm ", "shutdown", "kill ", "uninstall", "password", "send email", "send message"]
    if any(d in norm for d in dangerous):
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
    except Exception as exc:
        logger.exception("Structured action execution failed %r: %s", data, exc)
        return False, "I couldn't perform that action."

    return False, "I couldn't understand that command."
