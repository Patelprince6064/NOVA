"""Interrupt manager for Nova Phase 10 — lightweight event-based."""

import threading
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class InterruptManager:
    """Lightweight cancellation manager using threading.Event.

    API:
        request_stop()
        is_stop_requested()
        clear_stop()
        interruptible_wait(seconds) -> bool  # True if completed, False if interrupted
    """

    def __init__(self, enabled: bool = True, check_interval_ms: int = 100, post_cancel_cooldown_ms: int = 300, global_event: Optional[threading.Event] = None):
        self.enabled = enabled
        self.check_interval = max(20, min(500, int(check_interval_ms))) / 1000.0
        self.post_cancel_cooldown = max(0, min(2000, int(post_cancel_cooldown_ms))) / 1000.0
        self._event = global_event if global_event is not None else threading.Event()
        self._lock = threading.Lock()
        logger.info("[INTERRUPT] InterruptManager init enabled=%s interval=%dms cooldown=%dms", enabled, check_interval_ms, post_cancel_cooldown_ms)

    @property
    def event(self) -> threading.Event:
        return self._event

    def request_stop(self):
        if not self.enabled:
            logger.debug("[INTERRUPT] request_stop ignored - disabled")
            return
        with self._lock:
            if not self._event.is_set():
                logger.info("[INTERRUPT] Stop requested")
                self._event.set()

    def is_stop_requested(self) -> bool:
        if not self.enabled:
            return False
        return self._event.is_set()

    def clear_stop(self):
        with self._lock:
            if self._event.is_set():
                logger.info("[INTERRUPT] Stop cleared")
                self._event.clear()

    def interruptible_wait(self, seconds: float) -> bool:
        """Wait `seconds` but return early if stop requested.

        Returns True if wait completed fully, False if interrupted.
        """
        if seconds <= 0:
            return True
        if not self.enabled:
            time.sleep(seconds)
            return True
        # Break into small intervals checking event
        remaining = float(seconds)
        while remaining > 0:
            if self.is_stop_requested():
                logger.info("[INTERRUPT] Wait interrupted after %.2fs remaining %.2fs", seconds - remaining, remaining)
                return False
            chunk = min(self.check_interval, remaining)
            time.sleep(chunk)
            remaining -= chunk
        return True

    def check_and_handle(self) -> bool:
        """Helper: True if stop was requested."""
        return self.is_stop_requested()
