"""Lightweight local follow-up router for Nova Phase 9.

Handles short follow-up commands without LLM when possible.
Uses recent conversation context for pronoun resolution.

Architecture:
  STT text -> normalize -> fast local check -> if simple -> execute via controllers
                                 -> elif ambiguous pronoun without context -> clarification
                                 -> else -> LLM/planner

Safety: never executes arbitrary code; only allowlisted actions.
"""

import re
import logging
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fast local phrases — handled without LLM
# ---------------------------------------------------------------------------
FAST_LOCAL_PHRASES = {
    "scroll down", "scroll up", "scroll",
    "go back", "back", "go forward", "forward",
    "refresh", "refresh the page", "reload", "reload the page",
    "close it", "close that", "close the browser", "close browser",
    "stop", "cancel", "goodbye", "bye",
    "try again", "do that again", "do it again", "repeat that",
    "go back", "continue", "go forward",
}

# Pronoun / reference patterns that need context
AMBIGUOUS_PRONOUN_PATTERNS = [
    r"^open it\.?$",
    r"^open that\.?$",
    r"^go there\.?$",
    r"^click that\.?$",
    r"^click it\.?$",
    r"^search that\.?$",
    r"^play it\.?$",
    r"^type this\.?$",
]

ORDINAL_RESULT_RE = re.compile(r"open the (first|second|third|fourth|fifth|\d+(?:st|nd|rd|th)?) result")
PLAY_RESULT_RE = re.compile(r"play the (first|second|third|fourth|fifth|\d+(?:st|nd|rd|th)?)(?: one| song| video| result)?")
CLICK_RESULT_RE = re.compile(r"click the (first|second|third|fourth|fifth).*")


def _normalize(text: str) -> str:
    if not text:
        return ""
    t = text.strip().lower()
    for pref in ("hey nova,", "hey nova ", "hey nova:", "nova,"):
        if t.startswith(pref):
            t = t[len(pref):].strip()
            break
    t = re.sub(r"\s+", " ", t).strip().rstrip(".,!?")
    return t


def is_cancellation_phrase(text: str) -> bool:
    low = _normalize(text)
    return low in ("stop", "cancel", "goodbye", "bye", "exit", "quit")


def is_fast_local_command(text: str) -> bool:
    """Return True if command should be handled locally without LLM."""
    low = _normalize(text)
    if low in FAST_LOCAL_PHRASES:
        return True
    # exact scroll variants
    if low in ("scroll down", "scroll up", "scroll"):
        return True
    if low in ("go back", "back", "go forward", "forward", "refresh", "reload"):
        return True
    if low in ("stop", "cancel", "try again", "do that again", "do it again"):
        return True
    # Pattern based fast: ordinal results when we have context? Still fast if context allows
    if low in ("scroll down", "scroll up"):
        return True
    return False


def needs_context_resolution(text: str) -> bool:
    low = _normalize(text)
    # Pronouns
    pronouns = [" it", " that", " there", " this"]
    if any(p in f" {low} " or low.endswith(p.strip()) for p in pronouns):
        # Check ambiguous patterns
        for pat in AMBIGUOUS_PRONOUN_PATTERNS:
            if re.match(pat, low):
                return True
        # Also general "it" / "that" as object
        if low in ("open it", "click it", "close it", "search it", "play it", "go there", "search that", "open that", "click that"):
            return True
    if "first one" in low or "second result" in low or "first result" in low:
        return True
    if "the first one" in low or "the second one" in low:
        return True
    return False


def resolve_follow_up(text: str, context: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Try to resolve follow-up command using context.

    Returns (action_dict_or_None, clarification_message_or_None).
    If clarification needed, returns (None, "What would you like me to open?").
    If not needing context resolution, returns (None, None) to let caller handle normally.
    If resolved locally, returns (action_dict, None).
    """
    low = _normalize(text)
    ctx = context or {}

    # Handle cancellation / resets — caller handles reset, but we note
    if is_cancellation_phrase(text):
        return None, None  # let main handle reset

    # ------------------------------------------------------------------
    # Pronoun-ambiguous: open it / go there etc without sufficient context
    # ------------------------------------------------------------------
    if low in ("open it", "open that", "go there", "search that"):
        # Need last_application or current_url or last_search
        if not ctx.get("last_application") and not ctx.get("current_url") and not ctx.get("current_site") and not ctx.get("last_search"):
            return None, "What would you like me to open?"
        # If we have browser context, maybe open last URL? But ambiguous — ask clarification per spec
        # Spec says do NOT guess when ambiguous
        # For "open it" even with context, still ambiguous what "it" is
        if low in ("open it", "open that"):
            return None, "What would you like me to open?"
        if low in ("go there",):
            if ctx.get("current_url"):
                return {"action": "open_url", "website": ctx.get("current_site") or ctx.get("current_url")}, None
            return None, "Where would you like me to go?"
        if low in ("search that",):
            if ctx.get("last_search"):
                return {"action": "search_web", "query": ctx["last_search"]}, None
            return None, "What would you like me to search for?"

    if low in ("click that", "click it", "open it"):
        return None, "What would you like me to open?"

    # ------------------------------------------------------------------
    # Ordinal result: play/open/click the first/second result
    # ------------------------------------------------------------------
    # play the first one / play the first song
    m = re.match(r"^(?:play|open|click)\s+the\s+(first|second|third|fourth|fifth|\d+)(?:\s+(?:one|song|video|result|result)?)?$", low)
    if m or "first one" in low or "second result" in low or "first result" in low:
        # Requires YouTube/search context
        has_search = ctx.get("last_search") or ctx.get("last_action") in ("youtube_search", "search_web", "open_url")
        # Also allow if current_site is youtube
        is_youtube_context = ctx.get("current_site") == "youtube" or (ctx.get("current_url") and "youtube" in str(ctx.get("current_url")).lower())
        if has_search or is_youtube_context or ctx.get("last_action") == "youtube_search":
            # Determine ordinal
            ordinal = 1
            if "second" in low or " 2" in low:
                ordinal = 2
            elif "third" in low:
                ordinal = 3
            # For Phase 9 we map to click first result via vision or browser
            target = f"{ordinal} video result" if ordinal == 1 else f"{ordinal} video result"
            # Use find/click action — executor will handle via vision
            # For simplicity return click_screen_element with target first video result
            # Actually for first, target "first video result"
            label = "first YouTube search result" if ordinal == 1 else f"{ordinal} YouTube search result"
            # We'll return a dict that main can map to vision click
            return {"action": "click_screen_element", "target": label, "ordinal": ordinal}, None
        else:
            return None, "Which result do you mean?"

    # Generic first/second result without verb
    if low in ("the first one", "first one", "the second one", "second one"):
        has_search = ctx.get("last_search") or ctx.get("last_action") in ("youtube_search", "search_web")
        if has_search:
            ordinal = 2 if "second" in low else 1
            label = "first YouTube search result" if ordinal == 1 else "second YouTube search result"
            return {"action": "click_screen_element", "target": label, "ordinal": ordinal}, None
        return None, "Which result do you mean?"

    # ------------------------------------------------------------------
    # Scroll / navigation — context not strictly needed, fast local
    # ------------------------------------------------------------------
    if low in ("scroll down", "scroll up"):
        amount = -500 if "down" in low else 500  # browser amount; pc uses 5
        # Return generic scroll; caller will decide browser vs pc
        return {"action": "scroll_fast", "amount": amount, "raw": low}, None

    if low in ("go back", "back"):
        return {"action": "browser_back"}, None
    if low in ("go forward", "forward"):
        return {"action": "browser_forward"}, None
    if low in ("refresh", "refresh the page", "reload"):
        return {"action": "browser_refresh"}, None

    # Close it / close that -> use last_application or browser
    if low in ("close it", "close that"):
        if ctx.get("last_application") or ctx.get("current_url"):
            # Caller should handle closing last app/browser
            return {"action": "close_it", "target": ctx.get("last_application") or ctx.get("current_site")}, None
        return None, "What would you like me to close?"

    # Try again / do that again — repeat last action
    if low in ("try again", "do that again", "do it again", "repeat that"):
        if ctx.get("last_action"):
            # Return repeat marker; caller can re-execute last action if possible
            return {"action": "repeat_last", "last_action": ctx.get("last_action")}, None
        return None, "What would you like me to try again?"

    # Type this / type that — needs context but generally requires text
    if low.startswith("type ") and ("this" in low or "that" in low) and len(low.split()) <= 3:
        return None, "What would you like me to type?"

    # Not a special follow-up that needs context resolution -> let normal routing handle
    return None, None


def should_use_fast_router(text: str, context: Optional[Dict[str, Any]] = None) -> bool:
    """Determine if command should bypass LLM."""
    low = _normalize(text)
    if is_fast_local_command(text):
        return True
    # Also pronoun resolved cases can be fast
    if context is not None:
        action, clar = resolve_follow_up(text, context)
        if action is not None:
            return True
    # Simple single verbs like scroll/go back are fast
    fast_verbs = ["scroll", "go back", "go forward", "refresh", "stop", "cancel"]
    if any(low == v or low.startswith(v + " ") for v in fast_verbs):
        return True
    return False
