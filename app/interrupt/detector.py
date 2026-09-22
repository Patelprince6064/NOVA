"""Stop command detector for Nova Phase 10 — highest priority routing."""

import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Configurable list — also in Config
DEFAULT_STOP_COMMANDS = [
    "stop",
    "cancel",
    "never mind",
    "nevermind",
    "abort",
    "stop nova",
    "nova stop",
    "nova cancel",
    "shut up",
    "forget it",
    "don't do that",
    "dont do that",
]

# Natural variations that should be treated as stop without LLM
STOP_VARIATIONS = [
    "stop that",
    "cancel this",
    "stop this",
    "cancel that",
    "never mind",
    "nevermind",
    "forget it",
    "abort",
    "shut up",
    "nova stop",
    "nova cancel",
    "stop nova",
]

def _normalize(text: str) -> str:
    if not text:
        return ""
    t = text.strip().lower()
    # strip leading hey nova
    for pref in ("hey nova,", "hey nova ", "hey nova:", "nova,"):
        if t.startswith(pref):
            t = t[len(pref):].strip()
            break
    t = re.sub(r"\s+", " ", t).strip().rstrip(".,!?")
    return t

def is_stop_command(text: str, stop_commands: List[str] = None) -> bool:
    """Return True if text is a stop/cancel command (highest priority)."""
    if not text or not text.strip():
        return False
    low = _normalize(text)
    commands = stop_commands or DEFAULT_STOP_COMMANDS
    # direct match
    if low in commands:
        return True
    # check variations via word boundaries
    if low in STOP_VARIATIONS:
        return True
    # also handle "stop that please" -> starts with stop
    for cmd in commands:
        if low == cmd or low.startswith(cmd + " ") or low.startswith(cmd + "."):
            return True
    # Specific phrases
    if low in ("stop", "cancel", "abort", "shut up", "never mind", "nevermind", "forget it"):
        return True
    if low.startswith("stop ") and len(low.split()) <= 4:
        # e.g. stop that, stop this now
        return True
    if low.startswith("cancel ") and len(low.split()) <= 3:
        return True
    if low.startswith("dont do that") or low.startswith("don't do that"):
        return True
    # Hey nova prefixed already stripped, but also handle nova stop patterns
    if "nova stop" in low or "nova cancel" in low:
        return True
    return False


def is_retry_command(text: str) -> Tuple[bool, str]:
    """Check for try again / do that again — priority 2 but not emergency."""
    if not text:
        return False, ""
    low = _normalize(text)
    if low in ("try again", "retry", "try once more", "again", "retry that"):
        return True, "try_again"
    if low in ("do that again", "do it again", "repeat that", "do that once more", "run that again"):
        return True, "do_that_again"
    return False, ""


def get_interrupt_priority(text: str) -> int:
    """Return priority 1..3 for routing."""
    if is_stop_command(text):
        return 1
    is_retry, _ = is_retry_command(text)
    if is_retry:
        return 2
    return 3
