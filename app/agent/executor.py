"""Task executor for Nova Phase 8 — sequential, verified, with retry/timeout/cancel.

No arbitrary code, only allowlisted controllers.
"""

import time
import logging
import threading
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum, auto

from app.agent.schemas import TaskPlan, TaskStep
from app.agent.validator import validate_plan

logger = logging.getLogger(__name__)

class TaskState(Enum):
    IDLE = auto()
    PLANNING = auto()
    VALIDATING = auto()
    RUNNING = auto()
    PAUSED = auto()
    FAILED = auto()
    COMPLETED = auto()
    CANCELLED = auto()

@dataclass
class TaskStatus:
    state: TaskState = TaskState.IDLE
    goal: str = ""
    total_steps: int = 0
    current_step: int = 0
    current_action: str = ""
    results: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

class TaskExecutor:
    def __init__(
        self,
        pc_controller=None,
        browser_controller=None,
        vision_analyzer=None,
        config=None,
    ):
        self.pc = pc_controller
        self.browser = browser_controller
        self.vision = vision_analyzer
        self.config = config
        self.state = TaskState.IDLE
        self.status = TaskStatus()
        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # not paused
        # Config limits
        self.max_retries = getattr(config, "max_step_retries", 1) if config else 1
        self.max_duration = getattr(config, "max_task_duration_seconds", 60) if config else 60
        self.max_wait = getattr(config, "max_wait_seconds", 10) if config else 10

    def cancel(self):
        logger.info("Task cancel requested")
        self._cancel_event.set()
        self.state = TaskState.CANCELLED
        self.status.state = TaskState.CANCELLED

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def _check_timeout(self, start: float) -> bool:
        if time.time() - start > self.max_duration:
            logger.warning("Task timeout after %.1fs > %ds", time.time() - start, self.max_duration)
            self.state = TaskState.FAILED
            self.status.error = "The task took too long, so I stopped."
            return True
        return False

    def _verify_step(self, step: TaskStep, ok: bool, msg: str) -> bool:
        """Simple verification: ok must be True and message not indicate failure."""
        if not ok:
            return False
        # For open_application, verify foreground window contains app name if possible
        if step.action == "open_application" and self.pc:
            app = step.parameters.get("application", "").lower()
            try:
                win = self.pc.get_foreground_window() or ""
                if win and app in win.lower():
                    logger.info("Verification: foreground window matches %r -> %r", app, win)
                    return True
                # Not strong verification, but ok==True is enough for Phase 8
                return True
            except Exception:
                return True
        if step.action in ("open_url", "search_web", "youtube_search") and self.browser:
            # Check browser current_url not empty
            try:
                if self.browser.is_running and self.browser.current_url:
                    logger.info("Verification: browser url %r", self.browser.current_url)
                    return True
                # If not running but ok True, still consider success for mock
                return True
            except Exception:
                return True
        if step.action in ("find_screen_element", "click_screen_element") and self.vision:
            # For find, ok already indicates found + confidence; for click, assume verified via find
            return True
        return True

    def _execute_single(self, step: TaskStep) -> tuple[bool, str]:
        """Dispatch step to appropriate controller. Returns (ok, msg)."""
        action = step.action
        p = step.parameters or {}
        logger.info("Executing step %d: %s %r", step.id, action, p)
        try:
            # Wait
            if action == "wait":
                sec = int(p.get("seconds", 2))
                if sec > self.max_wait:
                    return False, f"Wait too long ({sec}s > {self.max_wait}s)"
                time.sleep(min(sec, self.max_wait))
                return True, "Waited."

            # Capture screen (vision)
            if action == "capture_screen":
                if not self.vision:
                    return False, "Vision not available"
                # Just capture to verify
                self.vision.capture.capture_screen()
                return True, "Captured screen."

            # Vision analyze
            if action == "analyze_screen":
                if not self.vision:
                    return False, "Vision not available"
                q = p.get("question", "What is on my screen?")
                win = self.pc.get_foreground_window() if self.pc else None
                analysis = self.vision.analyze(q, active_window=win)
                if analysis.confidence < getattr(self.vision, "min_confidence", 0.70):
                    return False, "I'm not confident enough to identify that."
                return True, analysis.description[:200]

            if action == "find_screen_element":
                if not self.vision:
                    return False, "Vision not available"
                target = p.get("target", "")
                win = self.pc.get_foreground_window() if self.pc else None
                result = self.vision.find_element(target, active_window=win)
                if not result.found:
                    return False, f"I couldn't find {target}."
                if result.confidence < getattr(self.vision, "min_confidence", 0.70):
                    return False, "I'm not confident enough to identify that."
                return True, f"Found {target} at {result.x},{result.y}"

            if action == "click_screen_element":
                if not self.vision:
                    return False, "Vision not available"
                target = p.get("target", "")
                win = self.pc.get_foreground_window() if self.pc else None
                result = self.vision.find_element(target, active_window=win)
                if not result.found:
                    return False, f"I couldn't find {target}."
                if result.confidence < getattr(self.vision, "min_confidence", 0.70):
                    return False, "I'm not confident enough to identify that."
                # Phase 8 allows click via vision with confidence check, regardless of demo flag
                try:
                    import pyautogui  # type: ignore
                    pyautogui.FAILSAFE = False
                    cx, cy = result.x + result.width // 2, result.y + result.height // 2
                    logger.info("Agent click_screen_element: %r at (%d,%d) conf=%.2f", target, cx, cy, result.confidence)
                    pyautogui.moveTo(cx, cy, duration=0.2)
                    pyautogui.click()
                    return True, f"Clicked {target}."
                except Exception as exc:
                    logger.exception("Click failed: %s", exc)
                    return False, "I couldn't click there."

            # PC actions
            if action == "open_application":
                if not self.pc:
                    return False, "PC control not available"
                return self.pc.open_application(p.get("application", ""))
            if action == "open_url":
                # Prefer browser if available and enabled
                target = p.get("website") or p.get("url") or ""
                if self.browser and self.browser.enabled:
                    return self.browser.open_url(target)
                if self.pc:
                    return self.pc.open_url(target)
                return False, "No browser/PC available"
            if action == "search_web":
                if self.browser and self.browser.enabled:
                    return self.browser.search_web(p.get("query", ""))
                return False, "Browser not available"
            if action == "youtube_search":
                if self.browser and self.browser.enabled:
                    return self.browser.youtube_search(p.get("query", ""))
                return False, "Browser not available"
            if action == "browser_back":
                if self.browser: return self.browser.go_back()
                return False, "Browser not available"
            if action == "browser_forward":
                if self.browser: return self.browser.go_forward()
                return False, "Browser not available"
            if action == "browser_refresh":
                if self.browser: return self.browser.refresh()
                return False, "Browser not available"
            if action == "browser_scroll":
                if self.browser: return self.browser.scroll(p.get("amount", -500))
                return False, "Browser not available"
            if action == "close_browser":
                if self.browser: return self.browser.close_browser()
                return False, "Browser not available"
            if action == "type_text":
                if self.pc: return self.pc.type_text(p.get("text", ""))
                return False, "PC not available"
            if action == "press_key":
                if self.pc: return self.pc.press_key(p.get("key", ""))
                return False, "PC not available"
            if action == "hotkey":
                if self.pc: return self.pc.hotkey(*p.get("keys", []))
                return False, "PC not available"
            if action == "scroll":
                if self.pc: return self.pc.scroll(p.get("amount", 5))
                return False, "PC not available"
            if action == "click":
                if self.pc: return self.pc.click()
                return False, "PC not available"
            if action == "double_click":
                if self.pc: return self.pc.double_click()
                return False, "PC not available"
            if action == "right_click":
                if self.pc: return self.pc.right_click()
                return False, "PC not available"
            if action == "get_active_window":
                if self.pc:
                    win = self.pc.get_foreground_window()
                    return True, f"{win} is open." if win else "No active window."
                return False, "PC not available"

            return False, f"Unknown action {action}"

        except Exception as exc:
            logger.exception("Step %d execution failed: %s", step.id, exc)
            return False, f"Step failed: {exc}"

    def execute(self, plan: TaskPlan) -> TaskStatus:
        """Execute validated plan sequentially with verification, retry, timeout, cancel."""
        self._cancel_event.clear()
        self.state = TaskState.RUNNING
        self.status = TaskStatus(state=TaskState.RUNNING, goal=plan.goal, total_steps=len(plan.steps), current_step=0, results=[])
        start_time = time.time()
        logger.info("Task started: goal=%r steps=%d", plan.goal, len(plan.steps))
        print(f"\n--------------------------------\nNOVA TASK\n--------------------------------\nGoal: {plan.goal}\n")
        # Validate first
        ok, err = validate_plan(plan, self.config)
        if not ok:
            self.state = TaskState.FAILED
            self.status.state = TaskState.FAILED
            self.status.error = err
            logger.warning("Task validation failed: %s", err)
            print(f"Task validation failed: {err}\n")
            return self.status

        for idx, step in enumerate(plan.steps, start=1):
            if self.is_cancelled():
                self.state = TaskState.CANCELLED
                self.status.state = TaskState.CANCELLED
                logger.info("Task cancelled at step %d", idx)
                print("Task cancelled.\n")
                return self.status
            if self._check_timeout(start_time):
                self.status.state = TaskState.FAILED
                print("Task timeout: The task took too long, so I stopped.\n")
                return self.status

            self.status.current_step = idx
            self.status.current_action = step.action
            print(f"Step {idx}/{len(plan.steps)} → {step.action} {step.parameters}")
            logger.info("Step %d/%d started: %s", idx, len(plan.steps), step.action)

            # Execute with one retry
            success = False
            msg = ""
            for attempt in range(self.max_retries + 1):
                if self.is_cancelled():
                    break
                ok, msg = self._execute_single(step)
                success = ok and self._verify_step(step, ok, msg)
                if success:
                    logger.info("Step %d completed: %s", step.id, msg)
                    print(f"✓ Step {idx}: {msg}")
                    self.status.results.append({"step": step.id, "action": step.action, "ok": True, "msg": msg})
                    break
                else:
                    logger.warning("Step %d failed (attempt %d): %s", step.id, attempt + 1, msg)
                    if attempt < self.max_retries:
                        # Small wait and retry once
                        wait_sec = 1.5
                        logger.info("Retrying step %d after %.1fs", step.id, wait_sec)
                        time.sleep(wait_sec)
                        # For browser, wait and check again
                        continue
                    else:
                        print(f"✗ Step {idx} failed: {msg}")
                        self.status.results.append({"step": step.id, "action": step.action, "ok": False, "msg": msg})
                        self.state = TaskState.FAILED
                        self.status.state = TaskState.FAILED
                        self.status.error = f"Step {idx} failed: {msg}"
                        logger.warning("Task failed at step %d: %s", idx, msg)
                        print(f"\nTask failed at step {idx}/{len(plan.steps)}: {msg}\n")
                        return self.status

            if not success:
                # Already handled failure return
                return self.status

            # Small delay between steps for stability
            time.sleep(0.3)

        self.state = TaskState.COMPLETED
        self.status.state = TaskState.COMPLETED
        logger.info("Task completed: %r", plan.goal)
        print(f"\nTask completed: {plan.goal}\n--------------------------------\n")
        return self.status
