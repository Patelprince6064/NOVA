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

    # YouTube / Google search — DELEGATED TO BRAVE (PC) per user request
    # Image 1 is Playwright chromium overlay (small window), Image 2 is real Brave (full window).
    # User wants ALL searches/YouTube in Brave (Image 2), not overlay. So we intentionally
    # do NOT handle search here — return False to let PCController.open_url (Brave) handle it.
    # This prevents the small white Playwright window from ever opening for searches.
    # Keep this block disabled; PC actions handles youtube_search/google_search via Brave URLs.
    if False:  # placeholder to keep logic visible but disabled
        m = re.match(r"^(?:search|find|look\s*up)\s+(?:youtube\s+for\s+)?(.+?)(?:\s+on\s+youtube)?$", norm)
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
        if "youtube" in norm:
            pass
        else:
            mm = re.match(r"^search\s+google\s+for\s+(.+)$", norm)
            if mm:
                q = mm.group(1).strip()
                ok, msg = controller.search_web(q)
                return True, msg
            mm = re.match(r"^google\s+(.+)$", norm)
            if mm:
                q = mm.group(1).strip()
                if q and len(q) > 2:
                    ok, msg = controller.search_web(q)
                    return True, msg
            mm = re.match(r"^search\s+(?:for\s+)?(.+)$", norm)
            if mm:
                q = mm.group(1).strip()
                if q and len(q) > 1 and "youtube" not in q:
                    ok, msg = controller.search_web(q)
                    return True, msg
    # Delegation: let PC handle search -> Brave
    # Check if norm looks like a search/youtube query, delegate
    youtube_search_indicators = ("search youtube", "youtube search", " on youtube", "play ")
    google_search_indicators = ("search google", "google ")
    search_generic = norm.startswith("search ")
    if any(x in norm for x in youtube_search_indicators) or (search_generic and "youtube" not in norm and len(norm.split()) > 1):
        # Don't handle here — PC will open Brave search URL
        return False, ""
    if any(x in norm for x in google_search_indicators) or (search_generic):
        # Also delegate generic search to PC/Brave
        # But keep Playwright for non-search browser nav (back/forward etc)
        # Quick check: if search pattern, delegate
        if re.match(r"^search\s+(?:for\s+)?.+", norm) or re.match(r"^google\s+.+", norm):
            return False, ""

    # Open website via browser (reuse website aliases, but via BrowserController)
    # NOTE: "open youtube" is intentionally NOT handled here — it is routed to
    # PCController.open_url which opens in Brave per user request.
    # Other sites still use BrowserController; youtube is delegated to Brave.
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
                # Delegate youtube to Brave (PC controller)
                website_key = (matched or target).strip().lower()
                if website_key == "youtube" or website_key.startswith("youtube "):
                    return False, ""
                ok, msg = controller.open_url(matched or target)
                return True, msg
            break
    if norm in WEBSITE_ALIASES:
        if norm == "youtube":
            return False, ""  # let PC/Brave handle it
        ok, msg = controller.open_url(norm)
        return True, msg

    return False, ""
