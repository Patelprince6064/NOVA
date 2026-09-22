"""Lightweight Windows system tray for Nova — background operation.

Uses pystray + Pillow if available, otherwise degrades gracefully (logs only).
Single instance, no second state system — mirrors ConversationState / app health.
"""

import logging
import threading
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Global
_tray_instance = None
_lock = threading.Lock()

class NovaTray:
    def __init__(self, config=None, status_getter=None, control=None):
        """
        status_getter: callable -> str  (Ready/Listening/Processing/Speaking/Paused/Error)
        control: object with pause/resume/stop methods for menu actions
        """
        self.config = config
        self.status_getter = status_getter or (lambda: "Ready")
        self.control = control
        self._icon = None
        self._thread = None
        self._running = False
        self._paused = False

    def _create_image(self):
        """Create a simple icon image (fallback if no .ico)."""
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (64, 64), color=(30, 144, 255))
            d = ImageDraw.Draw(img)
            d.ellipse((16, 16, 48, 48), fill=(255, 255, 255))
            d.text((22, 26), "N", fill=(30, 144, 255))
            return img
        except Exception as exc:
            logger.warning("Pillow not available for tray icon: %s", exc)
            return None

    def _load_icon_path(self):
        # Try assets/nova.ico
        candidates = [
            Path(__file__).resolve().parents[2] / "assets" / "nova.ico",
            Path(__file__).resolve().parents[2] / "assets" / "nova.png",
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return None

    def _menu(self):
        try:
            import pystray
            from pystray import MenuItem as Item, Menu
        except Exception:
            return None

        def _status_text(icon, item):
            return f"Status: {self.status_getter()}"

        def _pause(icon, item):
            self._paused = True
            logger.info("Tray: Pause Listening")
            if self.control and hasattr(self.control, "pause"):
                try: self.control.pause()
                except Exception as exc: logger.warning("Pause failed: %s", exc)

        def _resume(icon, item):
            self._paused = False
            logger.info("Tray: Resume Listening")
            if self.control and hasattr(self.control, "resume"):
                try: self.control.resume()
                except Exception as exc: logger.warning("Resume failed: %s", exc)

        def _test_voice(icon, item):
            logger.info("Tray: Test Voice")
            if self.control and hasattr(self.control, "test_voice"):
                try: self.control.test_voice()
                except Exception: pass

        def _open_logs(icon, item):
            logs_dir = Path(__file__).resolve().parents[2] / "logs"
            logs_dir.mkdir(exist_ok=True)
            try:
                os.startfile(str(logs_dir))  # type: ignore
            except Exception as exc:
                logger.warning("Open logs failed: %s", exc)

        def _settings(icon, item):
            env_path = Path(__file__).resolve().parents[2] / ".env"
            try:
                os.startfile(str(env_path))  # type: ignore
            except Exception:
                # fallback open folder
                try:
                    os.startfile(str(env_path.parent))  # type: ignore
                except Exception as exc:
                    logger.warning("Open settings failed: %s", exc)

        def _restart(icon, item):
            logger.info("Tray: Restart requested")
            if self.control and hasattr(self.control, "restart"):
                try: self.control.restart()
                except Exception: pass

        def _exit(icon, item):
            logger.info("Tray: Exit requested")
            self.stop()
            if self.control and hasattr(self.control, "exit"):
                try: self.control.exit()
                except Exception: pass
            # Ensure process exits
            os._exit(0)

        # Dynamic text items
        return Menu(
            Item(lambda _: f"Nova — {self.status_getter()}", None, enabled=False),
            Item(lambda _: f"Status: {self.status_getter()}", _status_text, enabled=False),
            pystray.Menu.SEPARATOR,
            Item("Pause Listening", _pause, visible=lambda _: not self._paused),
            Item("Resume Listening", _resume, visible=lambda _: self._paused),
            Item("Test Voice", _test_voice),
            Item("Open Logs", _open_logs),
            Item("Settings", _settings),
            Item("Restart", _restart),
            Item("Exit", _exit),
        )

    def start(self):
        """Start tray in background thread. Returns True if started."""
        with _lock:
            if self._running:
                logger.warning("Tray already running")
                return False
            try:
                import pystray  # noqa
            except ImportError:
                logger.warning("pystray not installed — tray disabled. Install: pip install pystray pillow")
                print("Tray: pystray not installed (pip install pystray pillow) — running without tray.")
                self._running = True  # logical running without UI
                return False

            img = self._create_image()
            # Try load .ico file for better icon
            icon_path = self._load_icon_path()
            if icon_path and icon_path.endswith(".ico"):
                try:
                    from PIL import Image
                    img = Image.open(icon_path)
                except Exception:
                    pass

            if img is None:
                logger.warning("Could not create tray image — tray disabled")
                return False

            try:
                import pystray
                self._icon = pystray.Icon("Nova", img, "Nova", menu=self._menu())
                self._thread = threading.Thread(target=self._icon.run, daemon=True, name="NovaTray")
                self._thread.start()
                self._running = True
                logger.info("System tray started")
                print("Tray: running (right-click icon for menu)")
                return True
            except Exception as exc:
                logger.warning("Tray start failed: %s", exc)
                print(f"Tray disabled: {exc}")
                return False

    def stop(self):
        with _lock:
            if not self._running:
                return
            try:
                if self._icon:
                    try:
                        self._icon.stop()
                    except Exception:
                        pass
                self._running = False
                logger.info("System tray stopped")
            except Exception as exc:
                logger.warning("Tray stop failed: %s", exc)

    def update_status(self, status: str):
        """Update tooltip — called when app state changes."""
        try:
            if self._icon:
                self._icon.title = f"Nova — {status}"
        except Exception:
            pass

    @property
    def is_running(self): return self._running
    @property
    def is_paused(self): return self._paused

def get_tray():
    global _tray_instance
    return _tray_instance

def create_tray(config=None, status_getter=None, control=None):
    global _tray_instance
    tray = NovaTray(config=config, status_getter=status_getter, control=control)
    _tray_instance = tray
    return tray
