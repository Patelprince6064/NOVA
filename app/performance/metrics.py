"""In-memory performance metrics for Nova Phase 11 — no DB, no sensitive data."""

import threading
import time
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Tracks avg/min/max latency, command counts, error counts, LLM vs local."""

    def __init__(self):
        self._lock = threading.Lock()
        self.commands = 0
        self.errors = 0
        self.llm_calls = 0
        self.local_commands = 0
        self._timings: Dict[str, List[float]] = {
            "stt": [],
            "router": [],
            "llm": [],
            "execution": [],
            "tts": [],
            "total": [],
            "wake_detection": [],
            "recording": [],
            "transcription": [],
            "browser": [],
            "vision": [],
        }

    def record(self, category: str, seconds: float):
        if seconds is None:
            return
        with self._lock:
            lst = self._timings.setdefault(category, [])
            lst.append(float(seconds))
            # cap at 200 entries to avoid unbounded growth
            if len(lst) > 200:
                lst.pop(0)

    def increment_command(self, is_llm: bool = False, is_error: bool = False):
        with self._lock:
            self.commands += 1
            if is_error:
                self.errors += 1
            if is_llm:
                self.llm_calls += 1
            else:
                self.local_commands += 1

    def _stats(self, arr: List[float]):
        if not arr:
            return (0, 0, 0, 0)
        avg = sum(arr) / len(arr)
        mn = min(arr)
        mx = max(arr)
        return (avg, mn, mx, len(arr))

    def snapshot(self) -> Dict:
        with self._lock:
            out = {
                "commands": self.commands,
                "errors": self.errors,
                "llm_calls": self.llm_calls,
                "local_commands": self.local_commands,
            }
            for k, v in self._timings.items():
                avg, mn, mx, cnt = self._stats(v)
                out[f"avg_{k}"] = avg
                out[f"min_{k}"] = mn
                out[f"max_{k}"] = mx
                out[f"cnt_{k}"] = cnt
            return out

    def print_dashboard(self):
        s = self.snapshot()
        print("\n====================================")
        print(" NOVA PERFORMANCE")
        print("====================================\n")
        print(f"Commands:              {s['commands']}")
        print(f"Average STT:            {s.get('avg_transcription', s.get('avg_stt',0)):.3f}s (cnt {s.get('cnt_transcription', s.get('cnt_stt',0))})")
        print(f"Average Router:         {s.get('avg_router',0):.3f}s")
        print(f"Average LLM:            {s.get('avg_llm',0):.3f}s")
        print(f"Average Execution:      {s.get('avg_execution',0):.3f}s")
        print(f"Average TTS:            {s.get('avg_tts',0):.3f}s")
        print(f"Average Total:          {s.get('avg_total',0):.3f}s")
        print(f"Average Recording:      {s.get('avg_recording',0):.3f}s")
        print(f"Average Browser:        {s.get('avg_browser',0):.3f}s")
        print(f"LLM Calls:              {s['llm_calls']}")
        print(f"Local Commands:         {s['local_commands']}")
        print(f"Errors:                 {s['errors']}")
        print("====================================\n")
        logger.info("Performance dashboard printed: %r", s)

    def reset(self):
        with self._lock:
            self.commands = 0
            self.errors = 0
            self.llm_calls = 0
            self.local_commands = 0
            for k in self._timings:
                self._timings[k].clear()


# Global singleton for easy import
global_metrics = PerformanceMetrics()


def run_benchmark(iterations: int = 20):
    """Simple benchmark for local vs AI commands — no hardware required."""
    import time
    from app.config import Config

    print("Running Nova benchmark...\n")
    # Mock local router performance
    try:
        from app.pc.actions import handle_command
        from app.pc.controller import PCController
        from app.browser.actions import handle_browser_command
        from app.browser.controller import BrowserController

        pc = PCController(enabled=True)
        # Patch _ensure_pyautogui to avoid actual mouse
        try:
            import unittest.mock as mock
            pc._ensure_pyautogui = mock.MagicMock(return_value=mock.MagicMock(click=lambda: None, scroll=lambda x: None, press=lambda x: None, hotkey=lambda *a: None, typewrite=lambda *a, **k: None, FAILSAFE=False))
        except Exception:
            pass
        browser = BrowserController(enabled=False)  # disabled for bench to avoid playwright
        local_cmds = ["open Brave", "open Notepad", "scroll down", "press enter", "go back", "refresh", "stop", "open YouTube", "type hello", "open VS Code"]
        ai_cmds = ["Find the latest AI news and open the most relevant result", "Play the first song from the current YouTube search"]
        metrics = PerformanceMetrics()
        # Benchmark local
        print("Benchmarking local commands...")
        for cmd in local_cmds * (iterations // len(local_cmds) + 1):
            if metrics.commands >= iterations:
                break
            t0 = time.perf_counter()
            # Simulate fast router without LLM
            try:
                # Try pc router
                handled, _ = handle_command(cmd, pc)
                if not handled:
                    # browser disabled, so skip
                    pass
            except Exception:
                metrics.increment_command(is_error=True)
                continue
            dt = time.perf_counter() - t0
            metrics.record("router", dt)
            metrics.record("total", dt + 0.01)  # simulate small overhead
            metrics.increment_command(is_llm=False)
        # Benchmark AI (simulated LLM latency if enabled)
        print("Benchmarking AI commands (simulated)...")
        for cmd in ai_cmds:
            t0 = time.perf_counter()
            time.sleep(0.02)  # simulate LLM 20ms fake for bench
            dt = time.perf_counter() - t0
            metrics.record("llm", dt)
            metrics.record("total", dt + 0.1)
            metrics.increment_command(is_llm=True)
        metrics.print_dashboard()
        snap = metrics.snapshot()
        # Return for programmatic use
        return snap
    except Exception as exc:
        print(f"Benchmark failed: {exc}")
        import traceback; traceback.print_exc()
        return {}


if __name__ == "__main__":
    run_benchmark()
    # Also test timing of import
    print("Benchmark complete. Use PERFORMANCE_DEBUG=true for live dashboard.")
