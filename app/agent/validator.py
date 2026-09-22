"""Plan validator for Nova Phase 8 — strict safety."""

import re
import logging
from typing import Tuple, Optional

from app.agent.schemas import TaskPlan, TaskStep, ALLOWED_AGENT_ACTIONS
from app.pc.controller import APPLICATION_ALIASES, WEBSITE_ALIASES, KEY_ALIASES, ALLOWED_HOTKEYS

logger = logging.getLogger(__name__)

# Dangerous patterns that must reject entire task
DANGEROUS_PATTERNS = [
    "delete", "format", "rm ", "shutdown", "kill ", "uninstall", "password", "bank", "purchase", "buy ", "payment",
    "install ", "send email", "send message", "share private", "credential", "account recovery", "captcha", "security settings",
    "log into", "log in", "sign in", "login", "read my emails", "read emails", "reply to", "attach a file", "send it",
]

MAX_WAIT_SECONDS = 10  # default, overridden by config


def _validate_step_params(step: TaskStep, config) -> Tuple[bool, str]:
    action = step.action
    params = step.parameters or {}

    # Normalize wait
    if action == "wait":
        sec = params.get("seconds", params.get("wait", params.get("duration", 2)))
        try:
            sec = int(sec)
        except Exception:
            return False, "wait requires integer seconds"
        max_wait = getattr(config, "max_wait_seconds", MAX_WAIT_SECONDS) if config else MAX_WAIT_SECONDS
        if not 0 < sec <= max_wait:
            return False, f"wait seconds out of range (1-{max_wait})"
        step.parameters = {"seconds": sec}
        return True, ""

    if action == "open_application":
        app = params.get("application") or params.get("app") or params.get("name")
        if not isinstance(app, str) or not app.strip():
            return False, "open_application requires application"
        key = app.strip().lower()
        if key not in APPLICATION_ALIASES:
            # Check word-aware
            found = None
            for alias in APPLICATION_ALIASES:
                if alias == key or f" {alias} " in f" {key} ":
                    found = alias
                    break
            if found is None and ("/" in app or "\\" in app or app.strip().lower().endswith(".exe")):
                return False, "Application must be alias, not path"
            if found is None:
                return False, f"Unknown application '{app}'"
        return True, ""

    if action == "open_url":
        website = params.get("website") or params.get("site")
        url = params.get("url") or params.get("link")
        if isinstance(website, str) and website.strip():
            key = website.strip().lower()
            if key not in WEBSITE_ALIASES:
                # check word-aware
                found = any(alias == key or f" {alias} " in f" {key} " for alias in WEBSITE_ALIASES)
                if not found:
                    return False, f"Unknown website '{website}'"
            return True, ""
        if isinstance(url, str) and url.strip():
            u = url.strip()
            if " " in u:
                return False, "Invalid URL"
            if not (u.startswith("http://") or u.startswith("https://") or "." in u):
                return False, "Invalid URL"
            return True, ""
        return False, "open_url requires website or url"

    if action in ("search_web", "youtube_search"):
        q = params.get("query") or params.get("q") or params.get("text")
        if not isinstance(q, str) or not q.strip():
            return False, f"{action} requires query"
        if len(q) > 300:
            return False, "Query too long"
        return True, ""

    if action == "type_text":
        t = params.get("text") or params.get("content", "")
        if not isinstance(t, str):
            return False, "type_text requires text"
        if len(t) > 500:
            return False, "type_text too long"
        return True, ""

    if action == "press_key":
        k = params.get("key")
        if not isinstance(k, str) or k.strip().lower() not in KEY_ALIASES:
            return False, f"Unsupported key '{k}'"
        return True, ""

    if action == "hotkey":
        keys = params.get("keys") or params.get("key")
        if isinstance(keys, str):
            keys = [x.strip().lower() for x in re.split(r"[+\s]+", keys) if x.strip()]
        if not isinstance(keys, list) or not keys:
            return False, "hotkey requires keys list"
        # Normalize
        norm = []
        for k in keys:
            kk = k.strip().lower()
            if kk in ("control", "ctrl"):
                norm.append("ctrl")
            elif kk in ("windows", "win"):
                norm.append("win")
            elif kk in ("alternate", "alt"):
                norm.append("alt")
            else:
                norm.append(kk)
        combo = tuple(norm)
        if combo not in ALLOWED_HOTKEYS and not (len(combo)==2 and combo[0]=="ctrl" and len(combo[1])==1 and combo[1].isalpha()):
            return False, f"Hotkey not allowlisted {keys}"
        step.parameters = {"keys": norm}
        return True, ""

    if action in ("scroll", "browser_scroll"):
        amt = params.get("amount", params.get("seconds"))
        if amt is None:
            # direction fallback
            d = params.get("direction", "")
            if isinstance(d, str) and d.lower() in ("up","down"):
                amt = 5 if d.lower()=="up" else -5
            else:
                amt = 5
        try:
            amt = int(amt)
        except Exception:
            return False, "scroll amount must be int"
        if not -2000 <= amt <= 2000:
            return False, "scroll amount out of range"
        step.parameters = {"amount": amt}
        return True, ""

    if action in ("click", "double_click", "right_click", "browser_back", "browser_forward", "browser_refresh", "close_browser", "get_active_window", "capture_screen"):
        return True, ""

    if action in ("analyze_screen",):
        q = params.get("question") or params.get("q") or ""
        if q and not isinstance(q, str):
            return False, "analyze_screen question must be string"
        if isinstance(q, str) and len(q) > 300:
            return False, "question too long"
        return True, ""

    if action in ("find_screen_element", "click_screen_element"):
        target = params.get("target") or params.get("label") or params.get("query")
        if not isinstance(target, str) or not target.strip():
            return False, f"{action} requires target"
        if len(target) > 100:
            return False, "target too long"
        # No path injection
        if "/" in target or "\\" in target and len(target) > 30:
            # allow youtube search box etc but not paths
            pass
        return True, ""

    return True, ""


def validate_plan(plan: TaskPlan, config=None) -> Tuple[bool, str]:
    """Validate entire plan. Returns (is_valid, error)."""
    if not isinstance(plan, TaskPlan):
        return False, "Invalid plan type"
    if not plan.goal or not plan.goal.strip():
        return False, "Missing goal"
    if not plan.steps or len(plan.steps) == 0:
        return False, "Plan has no steps"
    max_steps = getattr(config, "max_task_steps", 8) if config else 8
    if len(plan.steps) > max_steps:
        return False, f"Task too complex: {len(plan.steps)} steps exceeds max {max_steps}. That task is too complex for me right now."
    # Check dangerous in goal
    low_goal = plan.goal.lower()
    for pat in DANGEROUS_PATTERNS:
        if pat in low_goal:
            return False, f"Task rejected: contains prohibited '{pat}'"
    # Validate each step
    for step in plan.steps:
        if step.action not in ALLOWED_AGENT_ACTIONS:
            return False, f"Unknown action '{step.action}' at step {step.id}. Never generate code/shell."
        # No code/shell in parameters
        params_str = str(step.parameters).lower()
        if "import " in params_str or "exec(" in params_str or "eval(" in params_str or "os.system" in params_str or "subprocess" in params_str:
            return False, f"Step {step.id} contains prohibited code"
        ok, err = _validate_step_params(step, config)
        if not ok:
            return False, f"Step {step.id} invalid: {err}"
        # Check dangerous in step params
        param_text = " ".join(str(v).lower() for v in step.parameters.values() if isinstance(v, str))
        for pat in DANGEROUS_PATTERNS:
            if pat in param_text:
                return False, f"Step {step.id} contains prohibited '{pat}'"
    # Check duplicate ids and sequential
    ids = [s.id for s in plan.steps]
    if len(ids) != len(set(ids)):
        return False, "Duplicate step ids"
    logger.info("Plan validated: goal=%r steps=%d", plan.goal, len(plan.steps))
    return True, ""
