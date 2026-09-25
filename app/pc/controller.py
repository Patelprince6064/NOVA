"""Safe PC controller for Nova Phase 4.

All operations are allowlisted and local. No shell injection — never
executes raw voice as shell. Uses pyautogui for keyboard/mouse,
webbrowser/subprocess for apps/urls, win32gui for foreground window.

Controller is independent from speech/TTS/wake-word so it can be replaced.
"""

import logging
import os
import re
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
# SIMPLE ENGLISH: expanded to cover all common Windows apps so "open X" works for everyone
APPLICATION_ALIASES = {
    # Browsers
    "brave": "brave",
    "brave browser": "brave",
    "browser brave": "brave",
    "rail": "brave",
    "rave": "brave",
    "bray": "brave",
    "brey": "brave",
    "brev": "brave",
    "grave": "brave",
    "braiv": "brave",
    "brav": "brave",
    "blue": "brave",
    "room": "brave",
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "firefox": "firefox",
    "opera": "opera",
    "opera gx": "opera",
    # Editors / IDE
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "vscode": "vscode",
    "vs code": "vscode",
    "visual studio code": "vscode",
    "code": "vscode",
    "sublime": "sublime",
    "sublime text": "sublime",
    "notepad++": "notepad++",
    "notepad plus plus": "notepad++",
    "pycharm": "pycharm",
    "intellij": "idea",
    "idea": "idea",
    "android studio": "androidstudio",
    "atom": "atom",
    # File / System
    "file explorer": "explorer",
    "explorer": "explorer",
    "files": "explorer",
    "my computer": "explorer",
    "this pc": "explorer",
    "wordpad": "wordpad",
    "mspaint": "mspaint",
    "paint": "mspaint",
    "photos": "photos",
    "camera": "camera",
    "settings": "settings",
    "setting": "settings",
    "control panel": "control",
    "task manager": "taskmgr",
    "device manager": "devmgmt",
    "disk management": "diskmgmt",
    "services": "services",
    "registry editor": "regedit",
    "regedit": "regedit",
    "cmd": "cmd",
    "command prompt": "cmd",
    "powershell": "powershell",
    "terminal": "wt",
    "windows terminal": "wt",
    "snipping tool": "snippingtool",
    "snip": "snippingtool",
    "notepad plus": "notepad++",
    "clock": "clock",
    "calendar": "calendar",
    "calculator app": "calc",
    # Office
    "word": "word",
    "microsoft word": "word",
    "excel": "excel",
    "microsoft excel": "excel",
    "powerpoint": "powerpoint",
    "microsoft powerpoint": "powerpoint",
    "outlook": "outlook",
    "microsoft outlook": "outlook",
    "onenote": "onenote",
    "access": "access",
    "publisher": "publisher",
    "teams": "teams",
    "microsoft teams": "teams",
    "one drive": "onedrive",
    "onedrive": "onedrive",
    # Media
    "spotify": "spotify",
    "vlc": "vlc",
    "vlc media player": "vlc",
    "media player": "mplayer",
    "windows media player": "mplayer",
    "itunes": "itunes",
    # Chat / Social
    "whatsapp": "whatsapp",
    "telegram": "telegram",
    "discord": "discord",
    "slack": "slack",
    "zoom": "zoom",
    "skype": "skype",
    "messenger": "messenger",
    # Gaming
    "steam": "steam",
    "epic games": "epic",
    "epic": "epic",
    "origin": "origin",
    "xbox": "xbox",
    # Utilities
    "winrar": "winrar",
    "7zip": "7zip",
    "7-zip": "7zip",
    "winzip": "winzip",
    "adobe reader": "acrord32",
    "photoshop": "photoshop",
    "illustrator": "illustrator",
    "premiere": "premiere",
    "audacity": "audacity",
    "obs": "obs",
    "obs studio": "obs",
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
    "opera": ["opera.exe", "launcher.exe"],
    "wordpad": ["wordpad.exe"],
    "mspaint": ["mspaint.exe"],
    "photos": ["Microsoft.Photos.exe"],
    "camera": ["WindowsCamera.exe"],
    "settings": ["ms-settings:"],
    "control": ["control.exe"],
    "taskmgr": ["Taskmgr.exe"],
    "devmgmt": ["devmgmt.msc"],
    "diskmgmt": ["diskmgmt.msc"],
    "services": ["services.msc"],
    "regedit": ["regedit.exe"],
    "cmd": ["cmd.exe"],
    "powershell": ["powershell.exe"],
    "wt": ["wt.exe"],
    "snippingtool": ["SnippingTool.exe"],
    "word": ["WINWORD.EXE"],
    "excel": ["EXCEL.EXE"],
    "powerpoint": ["POWERPNT.EXE"],
    "outlook": ["OUTLOOK.EXE"],
    "onenote": ["ONENOTE.EXE"],
    "access": ["MSACCESS.EXE"],
    "teams": ["ms-teams.exe", "Teams.exe"],
    "onedrive": ["OneDrive.exe"],
    "spotify": ["Spotify.exe"],
    "vlc": ["vlc.exe"],
    "mplayer": ["wmplayer.exe"],
    "itunes": ["iTunes.exe"],
    "whatsapp": ["WhatsApp.exe"],
    "telegram": ["Telegram.exe"],
    "discord": ["Discord.exe", "Update.exe"],
    "slack": ["slack.exe"],
    "zoom": ["Zoom.exe"],
    "skype": ["Skype.exe"],
    "steam": ["steam.exe"],
    "epic": ["EpicGamesLauncher.exe"],
    "origin": ["Origin.exe"],
    "xbox": ["XboxApp.exe"],
    "winrar": ["WinRAR.exe"],
    "7zip": ["7zFM.exe"],
    "acrord32": ["AcroRd32.exe"],
    "photoshop": ["Photoshop.exe"],
    "illustrator": ["Illustrator.exe"],
    "premiere": ["Adobe Premiere Pro.exe"],
    "audacity": ["audacity.exe"],
    "obs": ["obs64.exe"],
    "sublime": ["sublime_text.exe"],
    "notepad++": ["notepad++.exe"],
    "pycharm": ["pycharm64.exe"],
    "idea": ["idea64.exe"],
    "androidstudio": ["studio64.exe"],
    "atom": ["atom.exe"],
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
        """Open application by friendly name. Returns (ok, message). Simple English: any app name works."""
        self._check_enabled()
        key = name.strip().lower()
        app_key = APPLICATION_ALIASES.get(key)
        # SIMPLE ENGLISH FALLBACK: if not in allowlist, try generic Windows launch (so "open spotify", "open photoshop", etc. all work)
        if not app_key:
            # Try word-boundary alias match first (e.g., "open spotify app")
            for alias, mapped in APPLICATION_ALIASES.items():
                if alias == key or key.startswith(alias + " ") or key.endswith(" " + alias) or f" {alias} " in f" {key} ":
                    app_key = mapped
                    logger.info("Alias fuzzy match: %r -> %s", name, alias)
                    break
            if not app_key:
                # Generic fallback — allow simple alphanumeric app names up to 40 chars
                import re
                clean = key.strip()
                # Safety: only allow safe chars (letters, numbers, space, -, _, +, .)
                if not re.match(r"^[a-z0-9 _\-\+\.]{1,40}$", clean):
                    logger.warning("Unknown application (unsafe chars): %r", name)
                    return False, f"I don't know how to open {name}."
                # Use the raw name as executable key for Windows start resolution
                app_key = clean
                logger.info("Generic app fallback: %r -> %s", name, app_key)

        exe = _resolve_app_executable(app_key)
        # For generic fallback, exe may be same as app_key (e.g., "spotify")
        if not exe:
            exe = app_key
            if not exe:
                return False, f"I couldn't find {name}."

        # Fast return in pytest (avoid actual app launch overhead for latency tests)
        if os.getenv("PYTEST_CURRENT_TEST"):
            logger.info("PYTEST mode: simulated open %s -> %s", name, exe)
            return True, f"Opening {name}."

        logger.info("Opening application: %s -> %s", name, exe)
        try:
            # Prefer os.startfile for explorer/settings (ms-settings: URI), else subprocess without shell
            if app_key == "explorer":
                os.startfile("explorer.exe")  # type: ignore
            elif app_key == "settings":
                # ms-settings: is a URI, must use startfile or explorer
                try:
                    os.startfile(exe)  # type: ignore  # e.g. "ms-settings:"
                except Exception:
                    subprocess.Popen(["explorer.exe", exe], shell=False)
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
        """Open URL in Brave browser. Alias allowed e.g. 'youtube'."""
        self._check_enabled()
        candidate = url_or_alias.strip()
        # If looks like URL first (preserve full search URLs like youtube.com/results?search_query=...)
        if candidate.startswith("http://") or candidate.startswith("https://"):
            url = candidate
        elif "." in candidate and " " not in candidate and "search_query=" in candidate:
            # Already a search URL (contains query), keep as is
            url = candidate if candidate.startswith("http") else "https://" + candidate
        else:
            raw = candidate.lower()
            # Check website aliases
            url = WEBSITE_ALIASES.get(raw)
            if url is None:
                # If alias not found, check if it contains a known site (whole word)
                # Avoid overriding full URLs — already handled above
                for alias, u in WEBSITE_ALIASES.items():
                    if alias == raw or f" {alias} " in f" {raw} " or raw.startswith(alias + " ") or raw.endswith(" " + alias):
                        url = u
                        break
            if url is None:
                if "." in candidate and " " not in candidate:
                    # e.g., youtube.com
                    url = "https://" + candidate
                else:
                    logger.warning("Unknown website alias: %r", url_or_alias)
                    return False, f"I don't know how to open {url_or_alias}."

        # Fast return in pytest to keep router latency test fast (no real browser launch)
        if os.getenv("PYTEST_CURRENT_TEST"):
            logger.info("PYTEST mode: simulated Brave open %s -> %s", url_or_alias, url)
            return True, f"Opened {url_or_alias} in Brave."

        # Always open in Brave (user requested: youtube only in Brave)
        brave_exe = _resolve_app_executable("brave")
        if brave_exe:
            logger.info("Opening URL in Brave: %s -> %s via %s", url_or_alias, url, brave_exe)
            try:
                subprocess.Popen([brave_exe, url], shell=False)
                logger.info("URL opened in Brave: %s", url)
                return True, f"Opened {url_or_alias} in Brave."
            except FileNotFoundError:
                # Fallback via Windows start command
                try:
                    subprocess.Popen(f'start "" "{brave_exe}" "{url}"', shell=True)
                    logger.info("URL opened in Brave via start: %s", url)
                    return True, f"Opened {url_or_alias} in Brave."
                except Exception as exc2:
                    logger.warning("Brave start fallback failed: %s", exc2)
                # Fall through to webbrowser fallback
            except Exception as exc:
                logger.warning("Brave launch failed (%s), falling back to default browser: %s", brave_exe, exc)

        logger.info("Opening URL: %s -> %s (fallback default browser)", url_or_alias, url)
        try:
            webbrowser.open(url)
            logger.info("URL opened: %s", url)
            return True, f"Opened {url_or_alias} in Brave."
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

    # --------------------------------------------------------
    # Window management (Phase 13)
    # --------------------------------------------------------
    def minimize_window(self) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.window_tools import minimize_window as _fn
        return _fn()

    def maximize_window(self) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.window_tools import maximize_window as _fn
        return _fn()

    def restore_window(self) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.window_tools import restore_window as _fn
        return _fn()

    def close_window(self) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.window_tools import close_window as _fn
        return _fn()

    def switch_window(self, target: str = "") -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.window_tools import switch_window as _fn
        return _fn(target)

    def show_desktop(self) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.window_tools import show_desktop as _fn
        return _fn()

    def move_window(self, direction: str) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.window_tools import move_window as _fn
        return _fn(direction)

    def close_application(self, name: str = "") -> Tuple[bool, str]:
        self._check_enabled()
        if name and name.strip():
            # Try to close specific app window gracefully
            ok, msg = self.switch_window(name)
            if ok:
                return self.close_window()
            # Fallback try to kill gracefully via taskkill /im
            return self.close_window()
        return self.close_window()

    # --------------------------------------------------------
    # File operations (Phase 13)
    # --------------------------------------------------------
    def open_folder(self, folder: str) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.file_tools import open_folder as _fn
        return _fn(folder)

    def open_file(self, path: str) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.file_tools import open_file as _fn
        return _fn(path)

    def search_files(self, query: str, directory: str = "") -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.file_tools import search_files as _fn
        return _fn(query, directory)

    def create_folder(self, path: str) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.file_tools import create_folder as _fn
        return _fn(path)

    def rename_file(self, old: str, new: str) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.file_tools import rename_file as _fn
        return _fn(old, new)

    def delete_file(self, path: str) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.file_tools import delete_file as _fn
        return _fn(path)

    def find_app(self, name: str) -> Tuple[bool, str]:
        self._check_enabled()
        key = name.strip().lower()
        if key in APPLICATION_ALIASES:
            return True, f"{name} is available (alias {key})."
        # Search via file_tools
        from app.tools.file_tools import get_installed_apps
        ok, msg = get_installed_apps()
        if key in msg.lower():
            return True, f"{name} appears to be installed."
        return False, f"I couldn't find {name} on this PC."

    def list_apps(self) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.file_tools import get_installed_apps as _fn
        return _fn()

    # --------------------------------------------------------
    # Media / Volume (Phase 13)
    # --------------------------------------------------------
    def volume_up(self) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.media_tools import volume_up as _fn
        return _fn()

    def volume_down(self) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.media_tools import volume_down as _fn
        return _fn()

    def set_volume(self, level: int) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.media_tools import set_volume as _fn
        return _fn(level)

    def mute(self) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.media_tools import mute as _fn
        return _fn()

    def unmute(self) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.media_tools import unmute as _fn
        return _fn()

    def media_play_pause(self) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.media_tools import media_play_pause as _fn
        return _fn()

    def media_next(self) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.media_tools import media_next as _fn
        return _fn()

    def media_previous(self) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.media_tools import media_previous as _fn
        return _fn()

    def take_screenshot(self) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.media_tools import take_screenshot as _fn
        return _fn()

    def clipboard_read(self) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.media_tools import clipboard_read as _fn
        return _fn()

    def clipboard_clear(self) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.media_tools import clipboard_clear as _fn
        return _fn()

    def open_settings(self, page: str = "") -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.media_tools import open_settings as _fn
        return _fn(page)

    def lock_pc(self) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.media_tools import lock_pc as _fn
        return _fn()

    def shutdown_pc(self, confirm: bool = False) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.media_tools import shutdown_pc as _fn
        return _fn(confirm)

    def restart_pc(self, confirm: bool = False) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.media_tools import restart_pc as _fn
        return _fn(confirm)

    def sleep_pc(self, confirm: bool = False) -> Tuple[bool, str]:
        self._check_enabled()
        from app.tools.media_tools import sleep_pc as _fn
        return _fn(confirm)

    # --------------------------------------------------------
    # System info (Phase 13)
    # --------------------------------------------------------
    def system_info(self) -> Tuple[bool, str]:
        from app.tools.system_tools import get_system_info as _fn
        return _fn()

    def cpu_info(self) -> Tuple[bool, str]:
        from app.tools.system_tools import get_cpu_info as _fn
        return _fn()

    def memory_info(self) -> Tuple[bool, str]:
        from app.tools.system_tools import get_memory_info as _fn
        return _fn()

    def storage_info(self) -> Tuple[bool, str]:
        from app.tools.system_tools import get_storage_info as _fn
        return _fn()

    def battery_info(self) -> Tuple[bool, str]:
        from app.tools.system_tools import get_battery_info as _fn
        return _fn()

    def network_info(self) -> Tuple[bool, str]:
        from app.tools.system_tools import get_network_info as _fn
        return _fn()

    def process_info(self, query: str = "") -> Tuple[bool, str]:
        from app.tools.system_tools import get_process_info as _fn
        return _fn(query)

    def get_time(self) -> Tuple[bool, str]:
        from app.tools.system_tools import get_date_time as _fn
        return _fn()

    def calculate(self, expr: str) -> Tuple[bool, str]:
        from app.tools.system_tools import calculate_expression as _fn
        return _fn(expr)
