"""Browser controller for Nova Phase 6 — Playwright, reused session.

No screenshot/vision, no arbitrary clicking, no scraping beyond navigation.
Reuses browser/context/page. Handles timeouts, selector fallback.

Privacy: no cookies/history extraction, no password handling, no screenshots uploaded.
"""

import logging
import time
import urllib.parse
from typing import Optional

logger = logging.getLogger(__name__)

# Website aliases imported from sites.py
from app.browser.sites import WEBSITE_ALIASES, google_search_url, youtube_search_url

# Playwright optional import — handled gracefully if not installed
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    sync_playwright = None  # type: ignore
    PlaywrightTimeout = Exception  # type: ignore


class BrowserController:
    """Manages a single Playwright browser session, reused across commands."""

    def __init__(
        self,
        enabled: bool = True,
        browser_name: str = "chromium",
        headless: bool = False,
        timeout_ms: int = 10000,
    ):
        self.enabled = enabled
        self.browser_name = browser_name.lower().strip() if browser_name else "chromium"
        if self.browser_name not in ("chromium", "firefox", "webkit"):
            logger.warning("BROWSER_NAME %r invalid, using chromium", browser_name)
            self.browser_name = "chromium"
        self.headless = bool(headless)
        self.timeout_ms = max(1000, min(60000, int(timeout_ms)))

        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._started = False
        # state
        self.current_url: Optional[str] = None
        self.current_title: Optional[str] = None

        logger.info("BrowserController init: enabled=%s browser=%s headless=%s timeout=%d",
                    enabled, self.browser_name, self.headless, self.timeout_ms)

    # ------------------------------------------------------------
    # Internal lifecycle
    # ------------------------------------------------------------
    def _check_enabled(self):
        if not self.enabled:
            raise RuntimeError("Browser control is disabled (BROWSER_ENABLED=false)")
        if sync_playwright is None:
            raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install chromium")

    def _ensure_browser(self):
        """Lazy start, reuse existing."""
        self._check_enabled()
        if self._started and self._page and self._browser:
            try:
                # Check if still connected
                if self._page.is_closed() or not self._browser.is_connected():
                    logger.info("Browser session closed unexpectedly, restarting")
                    self._cleanup()
                else:
                    return
            except Exception:
                self._cleanup()

        logger.info("Browser starting: %s headless=%s", self.browser_name, self.headless)
        try:
            self._playwright = sync_playwright().start()
            browser_type = getattr(self._playwright, self.browser_name)
            self._browser = browser_type.launch(headless=self.headless)
            self._context = self._browser.new_context()
            self._page = self._context.new_page()
            self._page.set_default_timeout(self.timeout_ms)
            self._started = True
            logger.info("Browser started")
            print("Browser started.\n")
        except Exception as exc:
            logger.exception("Browser startup failed: %s", exc)
            self._cleanup()
            raise RuntimeError(f"Browser startup failed: {exc}") from exc

    def _cleanup(self):
        try:
            if self._page:
                try:
                    self._page.close()
                except Exception:
                    pass
            if self._context:
                try:
                    self._context.close()
                except Exception:
                    pass
            if self._browser:
                try:
                    self._browser.close()
                except Exception:
                    pass
            if self._playwright:
                try:
                    self._playwright.stop()
                except Exception:
                    pass
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
            self._started = False

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------
    @property
    def is_running(self) -> bool:
        try:
            return bool(self._started and self._browser and self._browser.is_connected() and self._page and not self._page.is_closed())
        except Exception:
            return False

    def get_state(self) -> dict:
        return {
            "running": self.is_running,
            "url": self.current_url,
            "title": self.current_title,
            "browser": self.browser_name,
            "headless": self.headless,
        }

    def open_url(self, url_or_alias: str):
        """Open URL or website alias."""
        self._check_enabled()
        url = self._resolve_url(url_or_alias)
        logger.info("Browser open_url: %r -> %s", url_or_alias, url)
        print(f"Navigation requested: {url}")
        try:
            self._ensure_browser()
            assert self._page is not None
            self._page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
            self.current_url = self._page.url
            try:
                self.current_title = self._page.title()
            except Exception:
                self.current_title = None
            logger.info("Navigation completed: %s title=%r", self.current_url, self.current_title)
            print(f"Navigation completed: {self.current_url}\n")
            return True, f"Opened {url_or_alias}."
        except Exception as exc:
            msg = str(exc)
            if "Timeout" in msg or "timeout" in msg.lower():
                logger.warning("Navigation timeout: %s", msg)
                return False, "The page took too long to load."
            if "not installed" in msg.lower() or "Executable" in msg:
                logger.warning("Browser executable missing: %s", msg)
                return False, "Browser not installed. Run: playwright install chromium"
            logger.exception("Navigation failed: %s", exc)
            return False, "I couldn't open that page."

    def _resolve_url(self, url_or_alias: str) -> str:
        raw = url_or_alias.strip()
        low = raw.lower().strip()
        # alias
        if low in WEBSITE_ALIASES:
            return WEBSITE_ALIASES[low]
        # check alias as word
        for alias, u in WEBSITE_ALIASES.items():
            if alias == low or f" {alias} " in f" {low} ":
                return u
        # already URL
        if low.startswith("http://") or low.startswith("https://"):
            return raw
        if "." in raw and " " not in raw:
            return "https://" + raw
        # fallback: treat as search? For open_url we require valid alias/url, else google
        return raw

    def search_web(self, query: str):
        """Generic Google search."""
        self._check_enabled()
        if not query or not query.strip():
            return False, "I couldn't understand that search."
        url = google_search_url(query)
        logger.info("Browser search_web: %r -> %s", query, url)
        print(f"Search requested: {query}")
        return self.open_url(url)

    def youtube_search(self, query: str):
        """YouTube search via Playwright typing (robust selectors)."""
        self._check_enabled()
        if not query or not query.strip():
            return False, "I couldn't understand that search."
        q = query.strip()
        logger.info("Browser youtube_search: %r", q)
        print(f"YouTube search requested: {q}")
        try:
            self._ensure_browser()
            assert self._page is not None
            # Ensure on YouTube
            yt_url = WEBSITE_ALIASES["youtube"]
            # If not already on YouTube, navigate
            if not self.current_url or "youtube.com" not in (self.current_url or ""):
                self._page.goto(yt_url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                self.current_url = self._page.url
            # Robust YouTube search box selectors
            selectors = [
                "input#search",
                "input[name='search_query']",
                'input[placeholder*="Search"]',
                "#search-input input",
                "ytd-searchbox input",
                "input.ytd-searchbox",
            ]
            search_input = None
            for sel in selectors:
                try:
                    loc = self._page.locator(sel).first
                    loc.wait_for(state="visible", timeout=3000)
                    # Verify it is actually input
                    search_input = loc
                    logger.debug("YouTube selector matched: %s", sel)
                    break
                except Exception:
                    continue
            if search_input is None:
                # Fallback: try URL-based search
                logger.warning("YouTube search box not found via selectors, falling back to URL")
                url = youtube_search_url(q)
                self._page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                self.current_url = self._page.url
                logger.info("YouTube URL fallback completed: %s", self.current_url)
                return True, f"Searched YouTube for {q}."

            # Clear, type, submit
            try:
                search_input.click(timeout=3000)
            except Exception:
                pass
            # Clear existing
            try:
                search_input.fill("", timeout=2000)
            except Exception:
                pass
            search_input.fill(q, timeout=5000)
            # Press Enter
            search_input.press("Enter", timeout=5000)
            # Wait for results
            try:
                self._page.wait_for_load_state("domcontentloaded", timeout=self.timeout_ms)
            except Exception:
                pass
            # Phase 11: condition-based wait, not fixed long sleep
            try:
                self._page.wait_for_selector("ytd-video-renderer, #contents ytd-video-renderer", timeout=1500)
            except Exception:
                time.sleep(0.5)
            self.current_url = self._page.url
            try:
                self.current_title = self._page.title()
            except Exception:
                pass
            logger.info("YouTube search completed: %s", self.current_url)
            return True, f"Searched YouTube for {q}."
        except Exception as exc:
            msg = str(exc)
            if "Timeout" in msg:
                logger.warning("YouTube search timeout: %s", msg)
                return False, "YouTube took too long to load."
            if "not found" in msg.lower() or "selector" in msg.lower():
                logger.warning("YouTube selector failure: %s", msg)
                return False, "I couldn't find the YouTube search box."
            logger.exception("YouTube search failed: %s", exc)
            return False, "I couldn't search YouTube."

    def go_back(self):
        self._check_enabled()
        if not self.is_running:
            return False, "Browser is not running."
        logger.info("Browser go_back")
        try:
            assert self._page is not None
            self._page.go_back(wait_until="domcontentloaded", timeout=self.timeout_ms)
            self.current_url = self._page.url
            return True, "Went back."
        except Exception as exc:
            logger.exception("go_back failed: %s", exc)
            return False, "I couldn't go back."

    def go_forward(self):
        self._check_enabled()
        if not self.is_running:
            return False, "Browser is not running."
        logger.info("Browser go_forward")
        try:
            assert self._page is not None
            self._page.go_forward(wait_until="domcontentloaded", timeout=self.timeout_ms)
            self.current_url = self._page.url
            return True, "Went forward."
        except Exception as exc:
            logger.exception("go_forward failed: %s", exc)
            return False, "I couldn't go forward."

    def refresh(self):
        self._check_enabled()
        if not self.is_running:
            return False, "Browser is not running."
        logger.info("Browser refresh")
        try:
            assert self._page is not None
            self._page.reload(wait_until="domcontentloaded", timeout=self.timeout_ms)
            self.current_url = self._page.url
            return True, "Refreshed."
        except Exception as exc:
            logger.exception("refresh failed: %s", exc)
            return False, "I couldn't refresh the page."

    def scroll(self, amount: int = 500):
        """Scroll via Playwright mouse wheel."""
        self._check_enabled()
        if not self.is_running:
            # If no browser, fallback to success? But we should report not running
            return False, "Browser is not running."
        # Clamp
        amount = max(-2000, min(2000, int(amount)))
        # Playwright scroll: positive down? Use mouse wheel; we map amount sign
        # Our pc scroll used + up - down; for browser we keep same but implement as wheel
        # In playwright, wheel deltaY positive scrolls down
        # Convert: our amount positive = up, so invert for wheel
        delta_y = -amount * 80  # each unit ~80px; invert
        logger.info("Browser scroll amount=%d delta_y=%d", amount, delta_y)
        try:
            assert self._page is not None
            self._page.mouse.wheel(0, delta_y)
            return True, "Done."
        except Exception as exc:
            logger.exception("Browser scroll failed: %s", exc)
            return False, "I couldn't scroll."

    # Alias for compatibility
    def scroll_up(self):
        return self.scroll(500)

    def scroll_down(self):
        return self.scroll(-500)

    def close_browser(self):
        """Close only Nova's browser session."""
        if not self.is_running:
            logger.info("Close browser: not running")
            return True, "Browser is not running."
        logger.info("Browser closing")
        try:
            self._cleanup()
            self.current_url = None
            self.current_title = None
            logger.info("Browser closed")
            print("Browser closed.\n")
            return True, "Closed the browser."
        except Exception as exc:
            logger.exception("Close browser failed: %s", exc)
            return False, "I couldn't close the browser."
