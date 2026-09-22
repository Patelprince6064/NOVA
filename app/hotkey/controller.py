"""Global hotkey controller for Nova — lightweight, safe fallback.

Default:
  ctrl+shift+n → toggle listening
  ctrl+shift+x → stop task

Uses `keyboard` library if available, otherwise degrades gracefully.
No large dependency forced.
"""

import logging
import threading

logger = logging.getLogger(__name__)

class HotkeyController:
    def __init__(self, config=None, toggle_callback=None, stop_callback=None):
        self.enabled = bool(getattr(config, "global_hotkey_enabled", False)) if config else False
        self.toggle_hotkey = getattr(config, "toggle_hotkey", "ctrl+shift+n") if config else "ctrl+shift+n"
        self.stop_hotkey = getattr(config, "stop_hotkey", "ctrl+shift+x") if config else "ctrl+shift+x"
        self.toggle_cb = toggle_callback
        self.stop_cb = stop_callback
        self._running = False
        self._handles = []

    def start(self):
        if not self.enabled:
            logger.info("Global hotkey disabled (GLOBAL_HOTKEY_ENABLED=false)")
            return False
        try:
            import keyboard  # type: ignore
        except ImportError:
            logger.warning("keyboard not installed — global hotkeys disabled. Install: pip install keyboard")
            print("Hotkeys disabled (pip install keyboard for ctrl+shift+n / ctrl+shift+x)")
            return False

        try:
            # Normalize hotkeys (keyboard lib uses 'ctrl+shift+n')
            toggle = self.toggle_hotkey.replace(" ", "").lower()
            stop = self.stop_hotkey.replace(" ", "").lower()
            h1 = keyboard.add_hotkey(toggle, self._on_toggle, suppress=False)
            h2 = keyboard.add_hotkey(stop, self._on_stop, suppress=False)
            self._handles = [h1, h2]
            self._running = True
            logger.info("Global hotkeys registered: toggle=%s stop=%s", toggle, stop)
            print(f"Hotkeys: {toggle} = toggle, {stop} = stop")
            return True
        except Exception as exc:
            logger.warning("Hotkey registration failed (may need admin): %s", exc)
            print(f"Hotkeys not registered: {exc} (try running without global hotkeys)")
            return False

    def _on_toggle(self):
        logger.info("Hotkey: toggle listening")
        if self.toggle_cb:
            try: self.toggle_cb()
            except Exception as exc: logger.warning("Toggle callback failed: %s", exc)

    def _on_stop(self):
        logger.info("Hotkey: stop task")
        if self.stop_cb:
            try: self.stop_cb()
            except Exception as exc: logger.warning("Stop callback failed: %s", exc)

    def stop(self):
        if not self._running:
            return
        try:
            import keyboard
            for h in self._handles:
                try: keyboard.remove_hotkey(h)
                except Exception: pass
            self._running = False
            logger.info("Global hotkeys unregistered")
        except Exception as exc:
            logger.warning("Hotkey stop failed: %s", exc)
