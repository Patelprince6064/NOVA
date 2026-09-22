"""Interrupt events for Nova Phase 10 — shared cancellation signal."""

import threading
import time
import logging

logger = logging.getLogger(__name__)


# Global shared event — lightweight
_global_stop_event = threading.Event()


def get_global_stop_event() -> threading.Event:
    """Return global stop event used by all components."""
    return _global_stop_event


def request_global_stop():
    logger.info("[INTERRUPT] Global stop requested")
    _global_stop_event.set()


def clear_global_stop():
    if _global_stop_event.is_set():
        logger.info("[INTERRUPT] Global stop cleared")
    _global_stop_event.clear()


def is_global_stop_requested() -> bool:
    return _global_stop_event.is_set()
