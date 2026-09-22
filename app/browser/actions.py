"""Browser action router for Nova Phase 6 — local fast path."""

import re
import logging
from typing import Tuple

from app.browser.controller import BrowserController
from app.browser.sites import WEBSITE_ALIASES

logger = logging.getLogger(__name__)


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


def handle_browser_command(text: str, controller: BrowserController) -> Tuple[bool, str]:
    """Try to handle browser commands locally. Returns (handled, response).

    If not handled by browser router, caller should try other routers/LLM.
    Handles: open_url, search_web, youtube_search, back/forward/refresh, scroll, close.
    """
    if not text or not text.strip():
        return False, ""
    norm = _normalize(text)
    if not norm:
        return False, ""

    logger.debug("Browser router: %r", norm)

    # Close browser
    if norm in ("close the browser", "close browser", "close nova browser", "exit browser"):
        ok, msg = controller.close_browser()
        return True, msg

    # Navigation back/forward/refresh
    if norm in ("go back", "back", "return", "return to the previous page", "go back to previous page"):
        ok, msg = controller.go_back()
        return True, msg
    if norm in ("go forward", "forward", "go forwards"):
        ok, msg = controller.go_forward()
        return True, msg
    if norm in ("refresh", "refresh the page", "refresh this page", "reload", "reload the page"):
        ok, msg = controller.refresh()
        return True, msg

    # Scroll (browser scroll via Playwright, not pc scroll)
    # We let this be handled here when browser is running; otherwise pc/actions scroll handles
    # Check exact scroll phrases before search handling
    if norm in ("scroll down", "scroll up"):
        amount = 500 if "up" in norm else -500
        # If browser running, use browser scroll, else let caller decide fallback
        if controller.is_running:
            ok, msg = controller.scroll(amount)
            return True, msg
        # else not handled, fall through to pc scroll

    # YouTube search — specific patterns
    # "search youtube for X", "find X on youtube", "look up X on youtube", "youtube search X"
    m = re.match(r"^(?:search|find|look\s*up)\s+(?:youtube\s+for\s+)?(.+?)(?:\s+on\s+youtube)?$", norm)
    # Need to differentiate generic search vs youtube search
    # Check youtube search explicitly first
    youtube_patterns = [
        r"^(?:search\s+youtube\s+for|search\s+youtube|youtube\s+search)\s+(.+)$",
        r"^(?:find|look\s*up)\s+(.+)\s+on\s+youtube$",
        r"^(?:search\s+for\s+)?(.+)\s+on\s+youtube$",
    ]
    for pat in youtube_patterns:
        mm = re.match(pat, norm)
        if mm:
            query = mm.group(1).strip().rstrip(" .")
            if query and query not in ("youtube",):
                ok, msg = controller.youtube_search(query)
                return True, msg

    # Also handle "search youtube for X" where X may be pre-extracted above but need to ensure
    if norm.startswith("search youtube for "):
        q = norm[len("search youtube for "):].strip()
        if q:
            ok, msg = controller.youtube_search(q)
            return True, msg
    if norm.startswith("search youtube "):
        q = norm[len("search youtube "):].strip()
        if q:
            ok, msg = controller.youtube_search(q)
            return True, msg

    # Google search — "search google for X", "google X", "search for X", "look up X"
    # Need to avoid catching youtube search already handled
    if "youtube" in norm:
        # already handled youtube above, if still here, treat as not handled
        pass
    else:
        m_google = None
        # "search google for X"
        mm = re.match(r"^search\s+google\s+for\s+(.+)$", norm)
        if mm:
            q = mm.group(1).strip()
            ok, msg = controller.search_web(q)
            return True, msg
        # "google X" (short)
        mm = re.match(r"^google\s+(.+)$", norm)
        if mm:
            q = mm.group(1).strip()
            # Avoid "google" alone
            if q and len(q) > 2:
                ok, msg = controller.search_web(q)
                return True, msg
        # "search for X" or "search X" — generic web search via google
        mm = re.match(r"^search\s+(?:for\s+)?(.+)$", norm)
        if mm:
            q = mm.group(1).strip()
            # Exclude youtube case already handled, also exclude if q is app-like "brave"
            # But for Phase 6, generic search via google is ok for non-youtube
            # To avoid intercepting "search" alone, require query length
            if q and len(q) > 1 and "youtube" not in q:
                # Don't intercept "search" that was meant as pc? But generic search is browser action
                # Let it be browser search
                ok, msg = controller.search_web(q)
                return True, msg

    # Open website via browser (reuse website aliases, but via BrowserController)
    # "open youtube", "go to youtube", "launch youtube" etc.
    website_triggers = ("open ", "launch ", "start ", "run ", "go to ", "goto ", "take me to ", "bring up ")
    for trig in website_triggers:
        if norm.startswith(trig):
            target = norm[len(trig):].strip().rstrip(" .")
            is_website = False
            matched = None
            if target in WEBSITE_ALIASES:
                is_website = True
                matched = target
            else:
                for alias in WEBSITE_ALIASES:
                    if alias == target or target.startswith(alias + " ") or target.endswith(" " + alias) or f" {alias} " in f" {target} ":
                        is_website = True
                        matched = alias
                        break
            if is_website:
                ok, msg = controller.open_url(matched or target)
                return True, msg
            break
    if norm in WEBSITE_ALIASES:
        ok, msg = controller.open_url(norm)
        return True, msg

    return False, ""
