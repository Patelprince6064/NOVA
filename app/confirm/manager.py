"""Confirmation manager — handles destructive actions with timeout."""
import time
import threading
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ConfirmationManager:
    def __init__(self, timeout_seconds: int = 10):
        self.timeout = timeout_seconds
        self._pending: Optional[Dict[str, Any]] = None
        self._timestamp: float = 0
        self._lock = threading.Lock()

    def request(self, action: str, params: Dict[str, Any], message: str) -> str:
        with self._lock:
            self._pending = {"action": action, "params": params}
            self._timestamp = time.time()
        logger.info("Confirmation requested: %s %r", action, params)
        return message

    def is_pending(self) -> bool:
        with self._lock:
            if not self._pending:
                return False
            if time.time() - self._timestamp > self.timeout:
                self._pending = None
                return False
            return True

    def get_pending(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if not self._pending:
                return None
            if time.time() - self._timestamp > self.timeout:
                self._pending = None
                return None
            return dict(self._pending)

    def confirm(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if not self._pending:
                return None
            if time.time() - self._timestamp > self.timeout:
                self._pending = None
                return None
            pending = dict(self._pending)
            self._pending = None
            logger.info("Confirmation granted: %r", pending)
            return pending

    def cancel(self):
        with self._lock:
            self._pending = None
            logger.info("Confirmation cancelled")

    def is_confirmation(self, text: str) -> bool:
        low = text.strip().lower()
        return low in ("yes", "yes please", "confirm", "confirm shutdown", "confirm restart", "confirm delete", "go ahead", "proceed", "do it")

    def is_cancellation(self, text: str) -> bool:
        low = text.strip().lower()
        return low in ("no", "cancel", "never mind", "abort", "stop")


_manager: Optional[ConfirmationManager] = None

def get_confirmation_manager(timeout: int = 10) -> ConfirmationManager:
    global _manager
    if _manager is None:
        _manager = ConfirmationManager(timeout_seconds=timeout)
    return _manager
