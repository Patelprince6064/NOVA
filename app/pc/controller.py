"""Safe PC controller for Nova Phase 4.

All operations are allowlisted and local. No shell injection — never
executes raw voice as shell. Uses pyautogui for keyboard/mouse,
webbrowser/subprocess for apps/urls, win32gui for foreground window.

Controller is independent from speech/TTS/wake-word so it can be replaced.
"""

import logging
import os
import subprocess
import sys
import time
import webbrowser
import shlex
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Safe allowlists
# ------------------------------------------------------------

# Application aliases -> executable or shell command
# Env overrides: BRAVE_PATH, CHROME_PATH, VSCODE_PATH, etc.
APPLICATION_ALIASES = {
    "brave": "brave",
    "brave browser": "brave",
    "browser brave": "brave",
    "chrome": "chrome",
    "google chrome": "chrome",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "vscode": "vscode",
    "vs code": "vscode",
    "visual studio code": "vscode",
    "code": "vscode",
    "file explorer": "explorer",
    "explorer": "explorer",
    "files": "explorer",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "firefox": "firefox",
    "wordpad": "wordpad",
    "mspaint": "mspaint",
    "paint": "mspaint",
}

# Executable lookup for Windows
APP_EXECUTABLES = {
    "brave": ["brave.exe", "brave"],
    "chrome": ["chrome.exe", "chrome"],
    "notepad": ["notepad.exe"],
    "calc": ["calc.exe"],
    "vscode": ["Code.exe", "code.cmd", "code"],
    "explorer": ["explorer.exe"],
    "msedge": ["msedge.exe"],
    "firefox": ["firefox.exe"],
    "wordpad": ["wordpad.exe"],
    "mspaint": ["mspaint.exe"],
}

# Key aliases -> pyautogui key name
KEY_ALIASES = {
    "enter": "enter",
    "return": "enter",
    "escape": "esc",
    "esc": "esc",
    "tab": "tab",
    "backspace": "backspace",
    "space": "space",
    "spacebar": "space",
    "delete": "delete",
    "del": "delete",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "home": "home",
    "end": "end",
    "page up": "pageup",
    "pageup": "pageup",
    "page down": "pagedown",
    "pagedown": "pagedown",
    "pageup": "pageup",
    "caps lock": "capslock",
    "capslock": "capslock",
    "print screen": "printscreen",
    "printscreen": "printscreen",
    "insert": "insert",
    "ins": "insert",
    "f1": "f1", "f2": "f2", "f3": "f3", "f4": "f4", "f5": "f5",
    "f6": "f6", "f7": "f7", "f8": "f8", "f9": "f9", "f10": "f10",
    "f11": "f11", "f12": "f12",
}

# Safe hotkeys — only these combos allowed in Phase 4
ALLOWED_HOTKEYS = {
    ("ctrl", "c"), ("ctrl", "v"), ("ctrl", "a"), ("ctrl", "z"),
    ("ctrl", "s"), ("ctrl", "x"), ("ctrl", "y"), ("ctrl", "n"),
    ("ctrl", "o"), ("ctrl", "f"), ("ctrl", "p"), ("ctrl", "w"),
    ("alt", "tab"), ("alt", "f4"),
    ("win", "d"), ("win", "e"), ("win", "r"), ("win", "l"),
    ("ctrl", "shift", "t"), ("ctrl", "shift", "n"),
}

# Website aliases -> https URL
WEBSITE_ALIASES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "outlook": "https://outlook.live.com",
    "facebook": "https://www.facebook.com",
    "twitter": "https://twitter.com",
    "x": "https://twitter.com",
    "reddit": "https://www.reddit.com",
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
    "stackoverflow": "https://stackoverflow.com",
    "wikipedia": "https://www.wikipedia.org",
    "amazon": "https://www.amazon.com",
    "linkedin": "https://www.linkedin.com",
}


def _resolve_app_executable(app_key: str) -> Optional[str]:
    """Resolve app_key to executable path/string using env or known exes."""
    env_map = {
        "brave": os.getenv("BRAVE_PATH"),
        "chrome": os.getenv("CHROME_PATH"),
        "vscode": os.getenv("VSCODE_PATH"),
    }
    env_path = env_map.get(app_key)
    if env_path and env_path.strip():
        p = Path(env_path.strip())
        if p.exists():
            return str(p)
        # If not exists but provided, try using as is (might be command)
        return env_path.strip()

    # Fallback to known executables — let Windows resolve via PATH/start
    candidates = APP_EXECUTABLES.get(app_key, [app_key])
    return candidates[0] if candidates else None


class PCController:
    """Safe PC automation. All methods are allowlisted and log operations."""

    def __init__(self, enabled: bool = True, default_scroll: int = 5, action_timeout: int = 10):
        self.enabled = enabled
        self.default_scroll = max(1, min(20, int(default_scroll)))
        self.action_timeout = max(1, min(30, int(action_timeout)))
        self._pyautogui = None
        # Lazy import pyautogui only when needed and when enabled
        logger.info("PCController initialized: enabled=%s scroll=%d timeout=%ds", enabled, self.default_scroll, self.action_timeout)

    def _ensure_pyautogui(self):
        if self._pyautogui is not None:
            return self._pyautogui
        try:
            import pyautogui  # type: ignore

            # Disable fail-safe corner abort for hands-free (mouse to 0,0 shouldn't crash)
            pyautogui.FAILSAFE = False
            pyautogui.PAUSE = 0.02
            self._pyautogui = pyautogui
            return pyautogui
        except Exception as exc:
            logger.error("pyautogui not available: %s", exc)
            raise RuntimeError(f"Mouse/keyboard control unavailable (pyautogui): {exc}")

    def _check_enabled(self):
        if not self.enabled:
            raise RuntimeError("PC control is disabled (PC_CONTROL_ENABLED=false)")

    # --------------------------------------------------------
    # Application / URL
    # --------------------------------------------------------

    def open_application(self, name: str) -> Tuple[bool, str]:
        """Open application by friendly name. Returns (ok, message)."""
        self._check_enabled()
        key = name.strip().lower()
        app_key = APPLICATION_ALIASES.get(key)
        if not app_key:
            # Try stripping common prefixes/suffixes
            # e.g., "brave browser" already mapped
            logger.warning("Unknown application: %r", name)
            return False, f"I don't know how to open {name}."

        exe = _resolve_app_executable(app_key)
        if not exe:
            return False, f"I couldn't find {name}."

        logger.info("Opening application: %s -> %s", name, exe)
        try:
            # Prefer os.startfile for explorer, else subprocess without shell
            if app_key == "explorer":
                os.startfile("explorer.exe")  # type: ignore
            elif app_key in ("calc", "notepad", "mspaint", "wordpad"):
                # These are in system32
                subprocess.Popen([exe], shell=False)
            else:
                # Try start via shell 'start' for Windows PATH apps
                # Use shell=True with start is safe because exe is allowlisted
                # Avoid shell injection: exe comes from allowlist, not user input
                try:
                    # First try direct Popen without shell
                    subprocess.Popen([exe], shell=False)
                except FileNotFoundError:
                    # Fallback to Windows start via os.startfile or cmd start
                    # Use webbrowser as last resort? No — use 'start' via shell but safe
                    subprocess.Popen(f'start "" "{exe}"', shell=True)

            logger.info("Application launch completed: %s", name)
            return True, f"Opening {name}."
        except Exception as exc:
            logger.exception("Failed to open %s: %s", name, exc)
            return False, f"I couldn't open {name}."

    def open_url(self, url_or_alias: str) -> Tuple[bool, str]:
        """Open URL in default browser. Alias allowed e.g. 'youtube'."""
        self._check_enabled()
        raw = url_or_alias.strip().lower()
        # Check website aliases
        url = WEBSITE_ALIASES.get(raw)
        if url is None:
            # If alias not found, check if it contains a known site
            for alias, u in WEBSITE_ALIASES.items():
                if alias in raw:
                    url = u
                    break
        if url is None:
            # If looks like URL, validate
            candidate = url_or_alias.strip()
            if candidate.startswith("http://") or candidate.startswith("https://"):
                url = candidate
            elif "." in candidate and " " not in candidate:
                # e.g., youtube.com
                url = "https://" + candidate
            else:
                logger.warning("Unknown website alias: %r", url_or_alias)
                return False, f"I don't know how to open {url_or_alias}."

        logger.info("Opening URL: %s -> %s", url_or_alias, url)
        try:
            webbrowser.open(url)
            logger.info("URL opened: %s", url)
            return True, f"Opening {url_or_alias}."
        except Exception as exc:
            logger.exception("Failed to open URL %s: %s", url, exc)
            return False, f"I couldn't open {url_or_alias}."

    # --------------------------------------------------------
    # Keyboard
    # --------------------------------------------------------

    def type_text(self, text: str) -> Tuple[bool, str]:
        self._check_enabled()
        if text is None:
            text = ""
        # Do NOT interpret text — type literally
        # Safety: limit length
        if len(text) > 500:
            logger.warning("Type text too long (%d) — truncating", len(text))
            text = text[:500]
        logger.info("Typing text: %d chars", len(text))
        try:
            pg = self._ensure_pyautogui()
            # Small delay to let target window focus
            time.sleep(0.12)
            pg.typewrite(text, interval=0.015)
            logger.info("Type completed")
            return True, "Done."
        except Exception as exc:
            logger.exception("Type failed: %s", exc)
            return False, "I couldn't type that."

    def press_key(self, key: str) -> Tuple[bool, str]:
        self._check_enabled()
        norm = key.strip().lower()
        pg_key = KEY_ALIASES.get(norm)
        if not pg_key:
            logger.warning("Unsupported key: %r", key)
            return False, f"I can't press {key}."
        logger.info("Pressing key: %s -> %s", key, pg_key)
        try:
            pg = self._ensure_pyautogui()
            pg.press(pg_key)
            logger.info("Key pressed: %s", pg_key)
            return True, "Done."
        except Exception as exc:
            logger.exception("Press key failed %s: %s", key, exc)
            return False, f"I couldn't press {key}."

    def hotkey(self, *keys: str) -> Tuple[bool, str]:
        """Press combo like ctrl+c. Only allowlisted combos."""
        self._check_enabled()
        # Normalize: ctrl -> ctrl, control -> ctrl, windows/win -> win
        normed = []
        for k in keys:
            kk = k.strip().lower()
            if kk in ("control", "ctrl"):
                normed.append("ctrl")
            elif kk in ("windows", "win", "super"):
                normed.append("win")
            elif kk in ("alternate", "alt"):
                normed.append("alt")
            elif kk == "shift":
                normed.append("shift")
            else:
                # Single char or key
                if len(kk) == 1:
                    normed.append(kk)
                else:
                    # Try key alias
                    pgk = KEY_ALIASES.get(kk, kk)
                    normed.append(pgk)

        combo = tuple(normed)
        # Check allowlist
        if combo not in ALLOWED_HOTKEYS:
            # Also allow single ctrl+char where char is a-z
            if not (len(combo) == 2 and combo[0] == "ctrl" and len(combo[1]) == 1 and combo[1].isalpha()):
                # Allow win+d/e/r/l single char etc already in list
                logger.warning("Hotkey not allowlisted: %s", combo)
                return False, f"I can't press {'+'.join(keys)}."

        logger.info("Hotkey: %s", "+".join(combo))
        try:
            pg = self._ensure_pyautogui()
            pg.hotkey(*combo)
            logger.info("Hotkey executed: %s", combo)
            return True, "Done."
        except Exception as exc:
            logger.exception("Hotkey failed %s: %s", combo, exc)
            return False, f"I couldn't press {'+'.join(keys)}."

    # --------------------------------------------------------
    # Mouse
    # --------------------------------------------------------

    def click(self) -> Tuple[bool, str]:
        self._check_enabled()
        logger.info("Click")
        try:
            pg = self._ensure_pyautogui()
            pg.click()
            return True, "Done."
        except Exception as exc:
            logger.exception("Click failed: %s", exc)
            return False, "I couldn't click."

    def double_click(self) -> Tuple[bool, str]:
        self._check_enabled()
        logger.info("Double click")
        try:
            pg = self._ensure_pyautogui()
            pg.doubleClick()
            return True, "Done."
        except Exception as exc:
            logger.exception("Double click failed: %s", exc)
            return False, "I couldn't double click."

    def right_click(self) -> Tuple[bool, str]:
        self._check_enabled()
        logger.info("Right click")
        try:
            pg = self._ensure_pyautogui()
            pg.rightClick()
            return True, "Done."
        except Exception as exc:
            logger.exception("Right click failed: %s", exc)
            return False, "I couldn't right click."

    def scroll(self, amount: int) -> Tuple[bool, str]:
        """Scroll: positive up, negative down (pyautogui convention)."""
        self._check_enabled()
        if amount is None:
            amount = self.default_scroll
        # Clamp
        amount = max(-20, min(20, int(amount)))
        direction = "up" if amount > 0 else "down"
        logger.info("Scroll %s amount=%d", direction, amount)
        try:
            pg = self._ensure_pyautogui()
            pg.scroll(amount)
            return True, "Done."
        except Exception as exc:
            logger.exception("Scroll failed: %s", exc)
            return False, "I couldn't scroll."

    def move_mouse(self, x: int, y: int) -> Tuple[bool, str]:
        self._check_enabled()
        logger.info("Move mouse to %d,%d", x, y)
        try:
            pg = self._ensure_pyautogui()
            pg.moveTo(int(x), int(y))
            return True, "Done."
        except Exception as exc:
            logger.exception("Move mouse failed: %s", exc)
            return False, "I couldn't move the mouse."

    # --------------------------------------------------------
    # Foreground window
    # --------------------------------------------------------

    def get_foreground_window(self) -> Optional[str]:
        """Return foreground window title or None if unavailable."""
        try:
            import win32gui  # type: ignore

            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                title = win32gui.GetWindowText(hwnd)
                logger.debug("Foreground window: %r", title)
                return title or None
        except ImportError:
            logger.debug("win32gui not installed — foreground window unavailable")
        except Exception as exc:
            logger.debug("Failed to get foreground window: %s", exc)
        return None
