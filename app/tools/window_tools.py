"""Window management tools — uses Win32 APIs where possible."""
import logging
import time
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def _get_foreground_hwnd():
    try:
        import win32gui
        return win32gui.GetForegroundWindow()
    except Exception:
        return None


def _send_message(hwnd, msg, wparam=0, lparam=0):
    try:
        import win32gui
        import win32con
        win32gui.SendMessage(hwnd, msg, wparam, lparam)
        return True
    except Exception as exc:
        logger.debug("SendMessage failed: %s", exc)
        return False


def minimize_window() -> Tuple[bool, str]:
    try:
        hwnd = _get_foreground_hwnd()
        if not hwnd:
            return False, "I couldn't find the active window."
        import win32gui
        import win32con
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        return True, "Minimized."
    except Exception as exc:
        logger.exception("minimize failed: %s", exc)
        # Fallback via hotkey
        try:
            import pyautogui
            pyautogui.hotkey("win", "down")
            return True, "Minimized."
        except Exception:
            return False, "I couldn't minimize that window."


def maximize_window() -> Tuple[bool, str]:
    try:
        hwnd = _get_foreground_hwnd()
        if not hwnd:
            return False, "I couldn't find the active window."
        import win32gui
        import win32con
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        return True, "Maximized."
    except Exception as exc:
        logger.exception("maximize failed: %s", exc)
        try:
            import pyautogui
            pyautogui.hotkey("win", "up")
            return True, "Maximized."
        except Exception:
            return False, "I couldn't maximize that window."


def restore_window() -> Tuple[bool, str]:
    try:
        hwnd = _get_foreground_hwnd()
        if not hwnd:
            return False, "I couldn't find the active window."
        import win32gui
        import win32con
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        return True, "Restored."
    except Exception as exc:
        logger.exception("restore failed: %s", exc)
        return False, "I couldn't restore that window."


def close_window() -> Tuple[bool, str]:
    try:
        hwnd = _get_foreground_hwnd()
        if not hwnd:
            return False, "I couldn't find the active window."
        import win32gui
        import win32con
        # WM_CLOSE is graceful
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        time.sleep(0.3)
        return True, "Closed."
    except Exception as exc:
        logger.exception("close_window failed: %s", exc)
        try:
            import pyautogui
            pyautogui.hotkey("alt", "f4")
            return True, "Closed."
        except Exception:
            return False, "I couldn't close that window."


def switch_window(target: str = "") -> Tuple[bool, str]:
    try:
        t = (target or "").strip().lower()
        if not t or t in ("previous", "last", "previous window", "last window", "previous app"):
            # Alt+Tab to previous
            try:
                import pyautogui
                pyautogui.hotkey("alt", "tab")
                return True, "Switched."
            except Exception as exc:
                return False, f"I couldn't switch: {exc}"
        # Find window by title substring
        import win32gui

        found = []

        def enum_handler(hwnd, _):
            try:
                title = win32gui.GetWindowText(hwnd)
                if title and t in title.lower() and win32gui.IsWindowVisible(hwnd):
                    found.append((hwnd, title))
            except Exception:
                pass

        win32gui.EnumWindows(enum_handler, None)
        if not found:
            return False, f"I couldn't find {target}."
        # Activate first match
        hwnd, title = found[0]
        try:
            import win32gui
            import win32con
            # Restore if minimized
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            return True, f"Switched to {title}."
        except Exception as exc:
            logger.warning("SetForeground failed: %s", exc)
            # Fallback via alt+tab cycling (not perfect)
            return False, f"I found {title} but couldn't switch to it."
    except Exception as exc:
        logger.exception("switch_window failed: %s", exc)
        return False, "I couldn't switch windows."


def show_desktop() -> Tuple[bool, str]:
    try:
        import pyautogui
        pyautogui.hotkey("win", "d")
        return True, "Desktop shown."
    except Exception as exc:
        logger.exception("show_desktop failed: %s", exc)
        return False, "I couldn't show the desktop."


def move_window(direction: str) -> Tuple[bool, str]:
    """Snap/move window. direction: left/right/top/bottom/maximize/minimize"""
    try:
        d = (direction or "").lower().strip()
        import pyautogui
        if "left" in d:
            pyautogui.hotkey("win", "left")
            return True, "Snapped left."
        if "right" in d:
            pyautogui.hotkey("win", "right")
            return True, "Snapped right."
        if "up" in d or "top" in d:
            pyautogui.hotkey("win", "up")
            return True, "Snapped up."
        if "down" in d or "bottom" in d:
            pyautogui.hotkey("win", "down")
            return True, "Snapped down."
        return False, "I didn't understand where to move it."
    except Exception as exc:
        logger.exception("move_window failed: %s", exc)
        return False, "I couldn't move that window."
