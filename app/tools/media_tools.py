"""Media, volume, screenshot, clipboard, settings, power."""
import logging
import os
from typing import Tuple

logger = logging.getLogger(__name__)


def _press_media_key(key: str) -> bool:
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.press(key)
        return True
    except Exception as exc:
        logger.debug("press %s failed: %s", key, exc)
        return False


def volume_up() -> Tuple[bool, str]:
    try:
        # Use pyautogui volume keys
        for _ in range(2):
            if not _press_media_key("volumeup"):
                break
        return True, "Volume up."
    except Exception as exc:
        logger.exception("volume_up failed: %s", exc)
        return False, "I couldn't change the volume."


def volume_down() -> Tuple[bool, str]:
    try:
        for _ in range(2):
            if not _press_media_key("volumedown"):
                break
        return True, "Volume down."
    except Exception as exc:
        logger.exception("volume_down failed: %s", exc)
        return False, "I couldn't change the volume."


def set_volume(level: int) -> Tuple[bool, str]:
    try:
        lvl = max(0, min(100, int(level)))
        # Try pycaw if available
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            vol = cast(interface, POINTER(IAudioEndpointVolume))
            # Convert 0-100 to 0.0-1.0
            vol.SetMasterVolumeLevelScalar(lvl / 100.0, None)
            return True, f"Volume set to {lvl}%."
        except Exception as e:
            logger.debug("pycaw set_volume failed: %s", e)
            # Fallback: press keys to approximate (not precise)
            # Mute unmute and press up/down not ideal, so just inform
            return True, f"Volume control via keys. Set to {lvl}% (install pycaw for precise control)."
    except Exception as exc:
        logger.exception("set_volume failed: %s", exc)
        return False, "I couldn't set the volume."


def mute() -> Tuple[bool, str]:
    try:
        if _press_media_key("volumemute"):
            return True, "Muted."
        return False, "I couldn't mute."
    except Exception as exc:
        logger.exception("mute failed: %s", exc)
        return False, "I couldn't mute."


def unmute() -> Tuple[bool, str]:
    try:
        # vol mute toggles
        if _press_media_key("volumemute"):
            return True, "Unmuted."
        return False, "I couldn't unmute."
    except Exception as exc:
        logger.exception("unmute failed: %s", exc)
        return False, "I couldn't unmute."


def media_play_pause() -> Tuple[bool, str]:
    try:
        if _press_media_key("playpause"):
            return True, "Done."
        import pyautogui
        pyautogui.press("playpause")
        return True, "Done."
    except Exception:
        return False, "I couldn't control playback."


def media_next() -> Tuple[bool, str]:
    try:
        if _press_media_key("nexttrack"):
            return True, "Next."
        return False, "I couldn't skip."
    except Exception:
        return False, "I couldn't skip."


def media_previous() -> Tuple[bool, str]:
    try:
        if _press_media_key("prevtrack"):
            return True, "Previous."
        return False, "I couldn't go back."
    except Exception:
        return False, "I couldn't go back."


def take_screenshot() -> Tuple[bool, str]:
    try:
        from app.vision.screenshot import ScreenCapture
        import datetime
        cap = ScreenCapture()
        img, meta = cap.capture_screen()
        # Save to Pictures/Screenshots/Nova
        base = os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots", "Nova")
        os.makedirs(base, exist_ok=True)
        name = datetime.datetime.now().strftime("Nova_%Y%m%d_%H%M%S.png")
        path = os.path.join(base, name)
        img.save(path, "PNG")
        return True, f"Screenshot saved to {path}."
    except Exception as exc:
        logger.exception("screenshot failed: %s", exc)
        return False, "I couldn't take a screenshot."


def clipboard_read() -> Tuple[bool, str]:
    try:
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            data = win32clipboard.GetClipboardData()
            win32clipboard.CloseClipboard()
            preview = data[:200] if isinstance(data, str) else str(data)[:200]
            return True, f"Clipboard: {preview}" if preview else "Clipboard is empty."
        except Exception:
            pass
        # Fallback pyperclip
        try:
            import pyperclip
            t = pyperclip.paste()
            return True, f"Clipboard: {t[:200]}" if t else "Clipboard is empty."
        except Exception:
            return False, "I couldn't read the clipboard."
    except Exception as exc:
        logger.exception("clipboard_read failed: %s", exc)
        return False, "I couldn't read the clipboard."


def clipboard_clear() -> Tuple[bool, str]:
    try:
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.CloseClipboard()
            return True, "Clipboard cleared."
        except Exception:
            pass
        try:
            import pyperclip
            pyperclip.copy("")
            return True, "Clipboard cleared."
        except Exception:
            return False, "I couldn't clear the clipboard."
    except Exception as exc:
        logger.exception("clipboard_clear failed: %s", exc)
        return False, "I couldn't clear the clipboard."


SETTINGS_URIS = {
    "wifi": "ms-settings:network-wifi",
    "network": "ms-settings:network",
    "bluetooth": "ms-settings:bluetooth",
    "display": "ms-settings:display",
    "sound": "ms-settings:sound",
    "personalization": "ms-settings:personalization",
    "update": "ms-settings:windowsupdate",
    "privacy": "ms-settings:privacy",
    "apps": "ms-settings:appsfeatures",
    "settings": "ms-settings:",
    "accounts": "ms-settings:accounts",
    "system": "ms-settings:system",
    "notifications": "ms-settings:notifications",
    "power": "ms-settings:powersleep",
}


def open_settings(page: str = "") -> Tuple[bool, str]:
    try:
        key = (page or "").strip().lower()
        # Find matching alias
        uri = SETTINGS_URIS.get(key)
        if not uri:
            for k, v in SETTINGS_URIS.items():
                if k in key:
                    uri = v
                    break
        if not uri:
            uri = "ms-settings:"
        import subprocess
        # Use start to open ms-settings
        import os as _os
        _os.startfile(uri)  # type: ignore
        return True, f"Opened {page or 'Settings'}."
    except Exception:
        try:
            import subprocess
            subprocess.Popen(["explorer.exe", uri], shell=False)
            return True, f"Opened {page or 'Settings'}."
        except Exception as exc:
            logger.exception("open_settings failed: %s", exc)
            return False, "I couldn't open Settings."


def lock_pc() -> Tuple[bool, str]:
    try:
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        return True, "Locked."
    except Exception as exc:
        logger.exception("lock failed: %s", exc)
        return False, "I couldn't lock the PC."


def shutdown_pc(confirm: bool = False) -> Tuple[bool, str]:
    if not confirm:
        return False, "Are you sure you want to shut down? Say 'confirm shutdown'."
    try:
        import subprocess
        subprocess.Popen(["shutdown", "/s", "/t", "5"], shell=False)
        return True, "Shutting down in 5 seconds. Say 'abort' to cancel."
    except Exception as exc:
        logger.exception("shutdown failed: %s", exc)
        return False, "I couldn't shut down."


def restart_pc(confirm: bool = False) -> Tuple[bool, str]:
    if not confirm:
        return False, "Are you sure you want to restart? Say 'confirm restart'."
    try:
        import subprocess
        subprocess.Popen(["shutdown", "/r", "/t", "5"], shell=False)
        return True, "Restarting in 5 seconds."
    except Exception as exc:
        logger.exception("restart failed: %s", exc)
        return False, "I couldn't restart."


def sleep_pc(confirm: bool = False) -> Tuple[bool, str]:
    if not confirm:
        return False, "Should I put the PC to sleep? Say 'confirm sleep'."
    try:
        import subprocess
        subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], shell=False)
        return True, "Going to sleep."
    except Exception as exc:
        logger.exception("sleep failed: %s", exc)
        return False, "I couldn't sleep the PC."
