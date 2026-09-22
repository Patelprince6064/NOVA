"""Lightweight timing utilities for Nova Phase 11."""

import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class PerfTimer:
    """Simple per-command timer. Usage: timer.start('stt'); ... ; elapsed = timer.stop('stt')"""

    def __init__(self):
        self._starts: Dict[str, float] = {}
        self._elapsed: Dict[str, float] = {}

    def start(self, key: str):
        self._starts[key] = time.perf_counter()

    def stop(self, key: str) -> float:
        s = self._starts.pop(key, None)
        if s is None:
            return 0.0
        e = time.perf_counter() - s
        self._elapsed[key] = e
        logger.info("[TIMING] %s: %.3fs", key, e)
        # also print concise for user if debug needed
        print(f"[TIMING] {key}: {e:.3f}s")
        return e

    def get(self, key: str) -> float:
        return self._elapsed.get(key, 0.0)

    def all(self) -> Dict[str, float]:
        return dict(self._elapsed)

    def reset(self):
        self._starts.clear()
        self._elapsed.clear()

    def measure(self, key: str):
        """Context manager for timing."""
        class _Ctx:
            def __init__(self, timer, k): self.timer=timer; self.k=k
            def __enter__(self): self.timer.start(self.k)
            def __exit__(self, *a): self.timer.stop(self.k)
        return _Ctx(self, key)
