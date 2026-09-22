"""Command router for Nova Phase 4.

Converts normalized voice text into safe PC actions. One action per
utterance — multi-step is rejected with guidance.

Safe pipeline:
  Voice -> normalize -> intent match -> allowlisted controller call -> response
Never: os.system(user_text) or subprocess with shell user text.
"""

import logging
import re
from typing import Tuple, Optional

from app.pc.controller import PCController, WEBSITE_ALIASES, APPLICATION_ALIASES

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
    # Remove leading wake word if still present
    for prefix in ("hey nova,", "hey nova ", "hey nova:", "nova,"):
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
    if norm in ("hello", "hello nova"):
        return False, "Hello! I'm Nova."
    if norm in ("hi", "hi nova", "hey"):
        return False, "Hi! I'm ready."
    if norm == "test" or norm == "test nova":
        return False, "Voice system is working correctly."

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

    # 6. OPEN WEBSITE — check website aliases before app (youtube etc)
    # Patterns: open youtube, go to youtube, launch youtube, open github etc.
    website_triggers = ("open ", "launch ", "start ", "run ", "go to ", "goto ")
    for trig in website_triggers:
        if norm.startswith(trig):
            target = norm[len(trig):].strip().rstrip(" .")
            # Check website alias with word boundaries (avoid single-char alias false positives like 'x' in 'explorer')
            is_website = False
            matched_alias = None
            if target in WEBSITE_ALIASES:
                is_website = True
                matched_alias = target
            else:
                for alias in WEBSITE_ALIASES:
                    # word-boundary check: alias as whole word in target
                    if alias == target or target.startswith(alias + " ") or target.endswith(" " + alias) or f" {alias} " in f" {target} ":
                        is_website = True
                        matched_alias = alias
                        break
            if is_website:
                ok, msg = controller.open_url(matched_alias or target)
                return True, msg
            # Break after first website check — continue to app check if not website
            break

    # Also handle bare "open youtube" without trigger? Already handled above
    # Check if norm itself is website alias with open implied?
    if norm in WEBSITE_ALIASES:
        ok, msg = controller.open_url(norm)
        return True, msg

    # 7. OPEN APPLICATION — open/launch/start/run <app>
    # Allow "open brave", "launch notepad", etc.
    for trig in ("open ", "launch ", "start ", "run ", "go to "):
        if norm.startswith(trig):
            target = norm[len(trig):].strip().rstrip(" .")
            # Try website first already done, now app
            # Normalize target for app aliases (brave browser etc)
            if target in APPLICATION_ALIASES:
                ok, msg = controller.open_application(target)
                return True, msg
            # Check if target contains alias substring (word-aware)
            for alias in APPLICATION_ALIASES:
                if alias == target or target == alias:
                    ok, msg = controller.open_application(alias)
                    return True, msg
                # word boundary: alias as whole word in target
                if alias in target and (alias in target.split() or f" {alias} " in f" {target} " or target.startswith(alias + " ") or target.endswith(" " + alias)):
                    ok, msg = controller.open_application(alias)
                    if ok or "don't know" not in msg:
                        return True, msg
            # Also handle case where target is within alias (e.g., "vs code" alias contains "code"? Already covered)
            for alias in APPLICATION_ALIASES:
                if target in alias and len(target.split()) == 1 and len(alias.split()) <= 2:
                    # e.g., target "code" -> alias "vs code"
                    if alias.endswith(" " + target) or alias == target:
                        ok, msg = controller.open_application(alias)
                        return True, msg
            # If not alias, but maybe user said open url like open google.com -> handled as website below?
            # Try as URL fallback
            if "." in target or target.startswith("http"):
                ok, msg = controller.open_url(target)
                if ok:
                    return True, msg
            # Unknown app
            # Only return if target looked like app intent (open X)
            # To avoid false positives for "open something complicated", return unknown app response
            # Check if target is plausible app word (single word or two words)
            if 1 <= len(target.split()) <= 3:
                # Try as app anyway — controller will give not-found msg
                ok, msg = controller.open_application(target)
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
