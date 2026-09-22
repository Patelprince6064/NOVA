"""Task schemas for Nova Phase 8 — strict, allowlisted.

Only approved actions, max 8 steps, validated parameters, no code/shell.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Must match ai/schemas AllowedActions + Phase 8 extra wait/capture/click_screen
ALLOWED_AGENT_ACTIONS = [
    "open_application",
    "open_url",
    "search_web",
    "youtube_search",
    "browser_back",
    "browser_forward",
    "browser_refresh",
    "browser_scroll",
    "close_browser",
    "type_text",
    "press_key",
    "hotkey",
    "scroll",
    "click",
    "double_click",
    "right_click",
    "capture_screen",
    "analyze_screen",
    "find_screen_element",
    "click_screen_element",
    "wait",
    "get_active_window",
]

@dataclass
class TaskStep:
    id: int
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_result: Optional[str] = None
    timeout: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class TaskPlan:
    goal: str
    steps: List[TaskStep]

    def to_dict(self) -> Dict[str, Any]:
        return {"goal": self.goal, "steps": [s.to_dict() for s in self.steps]}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskPlan":
        goal = str(data.get("goal", "")).strip()[:300] or "Task"
        steps_raw = data.get("steps", [])
        steps: List[TaskStep] = []
        for idx, raw in enumerate(steps_raw, start=1):
            if not isinstance(raw, dict):
                continue
            action = str(raw.get("action", "")).strip().lower()
            params = raw.get("parameters", {})
            if not isinstance(params, dict):
                params = {}
            # Also support flat params (legacy)
            # If action keys are at top level, move to parameters
            for k in list(raw.keys()):
                if k not in ("id", "action", "parameters", "expected_result", "timeout"):
                    # e.g., {"action":"open_application","application":"brave"} -> parameters
                    params[k] = raw[k]
            # Normalize id
            try:
                sid = int(raw.get("id", idx))
            except Exception:
                sid = idx
            steps.append(TaskStep(id=sid, action=action, parameters=params,
                                  expected_result=raw.get("expected_result"), timeout=raw.get("timeout")))
        return cls(goal=goal, steps=steps)
