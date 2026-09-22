"""Task planner for Nova Phase 8 — LLM with strict prompt, fallback heuristic.

Never generates code/shell, only allowed structured actions. Max 8 steps.
"""

import json
import re
import logging
from typing import Optional

from app.config import Config
from app.agent.schemas import TaskPlan, TaskStep

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are Nova's task planner — strict, safe.

Convert the user's multi-step request into a short plan (1-8 steps). Use ONLY allowed actions: open_application, open_url, search_web, youtube_search, browser_back, browser_forward, browser_refresh, browser_scroll, close_browser, type_text, press_key, hotkey, scroll, click, double_click, right_click, capture_screen, analyze_screen, find_screen_element, click_screen_element, wait, get_active_window.

RULES:
- Return ONLY valid JSON: {"goal": string, "steps": [{"id": 1, "action": "...", "parameters": {...}}]}
- Never generate executable Python, PowerShell, CMD, bash, shell commands, page.click() code, or arbitrary tool names.
- Never invent actions or parameters. Use alias only for applications/websites.
- Max 8 steps. If request needs more, return {"goal": "...", "steps": []} with empty and we will reject as too complex.
- If request is unsafe (delete files, format, passwords, banking, purchases, installs, email, captcha), return {"goal": "unsafe", "steps": [], "error": "unsafe"}
- If multi-step but simple, produce minimal steps. One action per step.
- For "open Brave, go to YouTube, search for X" → open_application brave → open_url youtube → youtube_search X
- For "search YouTube for X and play first result" → youtube_search → find_screen_element (target first video result) → click_screen_element
- Always use alias: brave, chrome, notepad, calculator, vscode, file explorer, youtube, google, github, etc.
- Wait steps: {"action": "wait", "parameters": {"seconds": 2}} (1-10 seconds only)

EXAMPLE 1:
User: "Open Brave and go to YouTube"
{"goal": "Open Brave and YouTube", "steps": [{"id":1,"action":"open_application","parameters":{"application":"brave"}},{"id":2,"action":"open_url","parameters":{"website":"youtube"}}]}

EXAMPLE 2:
User: "Open Brave, go to YouTube, search for Arijit Singh, and play the first song"
{"goal": "Play Arijit Singh on YouTube", "steps": [{"id":1,"action":"open_application","parameters":{"application":"brave"}},{"id":2,"action":"open_url","parameters":{"website":"youtube"}},{"id":3,"action":"youtube_search","parameters":{"query":"Arijit Singh"}},{"id":4,"action":"find_screen_element","parameters":{"target":"first video result"}},{"id":5,"action":"click_screen_element","parameters":{"target":"first video result"}}]}

Return ONLY JSON.
"""


class TaskPlanner:
    def __init__(self, config: Config):
        self.enabled = config.agent_enabled
        self.max_steps = config.max_task_steps
        self.llm_enabled = config.llm_enabled
        self.provider = config.llm_provider
        self.model = config.llm_model or "gpt-4o-mini"
        self.api_key = config.llm_api_key
        self.timeout = config.llm_timeout_seconds
        key_hint = (self.api_key[:4] + "…") if self.api_key else "none"
        logger.info("TaskPlanner init: enabled=%s max_steps=%d llm=%s model=%s key=%s", self.enabled, self.max_steps, self.llm_enabled, self.model, key_hint)

    def is_available(self) -> bool:
        return bool(self.enabled)

    def plan(self, user_request: str) -> Optional[TaskPlan]:
        """Generate plan via LLM or heuristic fallback. Returns None if planner disabled."""
        if not self.enabled:
            logger.debug("Planner disabled")
            return None
        if not user_request or not user_request.strip():
            return None
        # First try LLM if available
        if self.llm_enabled and self.api_key and self.provider == "openai":
            try:
                plan = self._plan_via_llm(user_request)
                if plan:
                    logger.info("Planner LLM generated: goal=%r steps=%d", plan.goal, len(plan.steps))
                    return plan
            except Exception as exc:
                logger.warning("LLM planner failed, falling back to heuristic: %s", exc)
        # Fallback heuristic — deterministic for testing without LLM
        plan = self._plan_heuristic(user_request)
        if plan:
            logger.info("Planner heuristic generated: goal=%r steps=%d", plan.goal, len(plan.steps))
        return plan

    def _plan_via_llm(self, text: str) -> Optional[TaskPlan]:
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai not installed")
        client = OpenAI(api_key=self.api_key, timeout=self.timeout)
        # Truncate long request
        txt = text.strip()[:800]
        try:
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                    {"role": "user", "content": txt},
                ],
                temperature=0.1,
                max_tokens=800,
                timeout=self.timeout,
                response_format={"type": "json_object"} if "gpt-4" in self.model or "mini" in self.model else None,
            )
        except TypeError:
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                    {"role": "user", "content": txt},
                ],
                temperature=0.1,
                max_tokens=800,
                timeout=self.timeout,
            )
        raw = resp.choices[0].message.content.strip() if resp.choices and resp.choices[0].message.content else ""
        # Extract JSON
        json_str = self._extract_json(raw)
        if not json_str:
            raise ValueError(f"No JSON in LLM output: {raw[:200]}")
        data = json.loads(json_str)
        # Handle unsafe marker
        if data.get("error") == "unsafe" or data.get("goal") == "unsafe":
            return TaskPlan(goal="unsafe", steps=[])
        plan = TaskPlan.from_dict(data)
        return plan

    def _extract_json(self, raw: str) -> Optional[str]:
        if not raw:
            return None
        s = raw.strip()
        if "```" in s:
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, re.DOTALL)
            if m:
                return m.group(1).strip()
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            return s[start:end+1]
        return None

    def _plan_heuristic(self, text: str) -> Optional[TaskPlan]:
        """Simple deterministic planner for tests without LLM — splits on 'and' / ',' and maps keywords."""
        low = text.strip().lower()
        # Remove leading hey nova
        for pref in ("hey nova,", "hey nova ", "hey nova:", "nova,"):
            if low.startswith(pref):
                low = low[len(pref):].strip()
                break
        original = text.strip()
        # Split on connectors that indicate multi-step
        # Use regex to split on commas and 'and' but keep phrases
        parts = re.split(r",\s*|\s+and\s+|\s+then\s+", low)
        parts = [p.strip() for p in parts if p.strip()]
        # If single part but contains multiple verbs, treat as multi-step heuristic
        # For testing, we will generate at most len(parts) steps
        goal = original[:120]
        steps = []
        sid = 1

        for part in parts:
            part = part.strip()
            if not part:
                continue
            # Map part to action
            # We reuse simple keyword mapping
            if any(k in part for k in ["open brave", "launch brave", "start brave"]):
                steps.append(TaskStep(id=sid, action="open_application", parameters={"application": "brave"}))
                sid += 1
            elif any(k in part for k in ["open chrome", "launch chrome"]):
                steps.append(TaskStep(id=sid, action="open_application", parameters={"application": "chrome"}))
                sid += 1
            elif "open notepad" in part or "launch notepad" in part:
                steps.append(TaskStep(id=sid, action="open_application", parameters={"application": "notepad"}))
                sid += 1
            elif "open vs code" in part or "open vscode" in part or "open code" in part:
                steps.append(TaskStep(id=sid, action="open_application", parameters={"application": "vscode"}))
                sid += 1
            elif "open file explorer" in part or "open explorer" in part:
                steps.append(TaskStep(id=sid, action="open_application", parameters={"application": "explorer"}))
                sid += 1
            elif "open youtube" in part or "go to youtube" in part or "launch youtube" in part:
                steps.append(TaskStep(id=sid, action="open_url", parameters={"website": "youtube"}))
                sid += 1
            elif "open google" in part or "go to google" in part:
                steps.append(TaskStep(id=sid, action="open_url", parameters={"website": "google"}))
                sid += 1
            elif "search youtube for" in part:
                m = re.search(r"search youtube for (.+)", part)
                q = m.group(1).strip() if m else part.split("for")[-1].strip()
                # Remove trailing "and play..." if still in part
                q = re.split(r"\s+and\s+", q)[0].strip().rstrip(" .")
                steps.append(TaskStep(id=sid, action="youtube_search", parameters={"query": q.strip().title() if q else "test"}))
                sid += 1
            elif "search google for" in part:
                m = re.search(r"search google for (.+)", part)
                q = m.group(1).strip() if m else part.split("for")[-1].strip()
                steps.append(TaskStep(id=sid, action="search_web", parameters={"query": q}))
                sid += 1
            elif "search for" in part and "youtube" not in part:
                m = re.search(r"search for (.+)", part)
                q = m.group(1).strip() if m else ""
                q = re.split(r"\s+and\s+", q)[0].strip().rstrip(" .")
                # If overall request is YouTube-related, treat as youtube_search
                if "youtube" in low:
                    steps.append(TaskStep(id=sid, action="youtube_search", parameters={"query": q}))
                else:
                    steps.append(TaskStep(id=sid, action="search_web", parameters={"query": q}))
                sid += 1
            elif any(k in part for k in ["play the first", "click the first", "first video", "first result"]):
                # Two steps: find + click
                steps.append(TaskStep(id=sid, action="find_screen_element", parameters={"target": "first video result"}))
                sid += 1
                steps.append(TaskStep(id=sid, action="click_screen_element", parameters={"target": "first video result"}))
                sid += 1
            elif "type" in part:
                m = re.search(r"type (.+)", part)
                q = m.group(1).strip() if m else ""
                if q:
                    steps.append(TaskStep(id=sid, action="type_text", parameters={"text": q}))
                    sid += 1
            elif "scroll" in part:
                amt = -500 if "down" in part else 500
                steps.append(TaskStep(id=sid, action="browser_scroll", parameters={"amount": amt}))
                sid += 1
            elif "go back" in part or part.strip() == "back":
                steps.append(TaskStep(id=sid, action="browser_back", parameters={}))
                sid += 1
            elif "go forward" in part:
                steps.append(TaskStep(id=sid, action="browser_forward", parameters={}))
                sid += 1
            elif "refresh" in part:
                steps.append(TaskStep(id=sid, action="browser_refresh", parameters={}))
                sid += 1
            else:
                # Generic fallback: try to detect youtube_search for "search for X" without google/youtube prefix
                if "search" in part and "youtube" in part:
                    # Extract query after for
                    m = re.search(r"for (.+)", part)
                    if m:
                        q = m.group(1).split(" and ")[0].strip()
                        steps.append(TaskStep(id=sid, action="youtube_search", parameters={"query": q}))
                        sid += 1
                # else ignore

        # If no steps derived but multi-step markers present, fallback to single youtube_search for whole
        if not steps and len(parts) > 1:
            # Try to extract overall youtube query
            m = re.search(r"search.*for (.+?)(?:,| and |$)", low)
            if m:
                q = m.group(1).split(" and ")[0].strip().rstrip(" .")
                steps.append(TaskStep(id=sid, action="youtube_search", parameters={"query": q}))
                sid += 1

        if not steps:
            return None
        return TaskPlan(goal=goal, steps=steps)
