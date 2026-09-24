"""Strict action schema for Nova Phase 5.

LLM output is untrusted. All actions validated against allowlists before
execution. Only these actions are allowed in Phase 5.
"""

import re
import logging
from typing import Dict, Any, Tuple, Optional, List

from app.pc.controller import APPLICATION_ALIASES, WEBSITE_ALIASES, KEY_ALIASES, ALLOWED_HOTKEYS

logger = logging.getLogger(__name__)

AllowedActions = [
    "open_application",
    "close_application",
    "open_url",
    "type_text",
    "press_key",
    "hotkey",
    "scroll",
    "click",
    "double_click",
    "right_click",
    "move_mouse",
    # Editing
    "copy",
    "paste",
    "cut",
    "select_all",
    "undo",
    "redo",
    # Window management Phase 13
    "minimize_window",
    "maximize_window",
    "restore_window",
    "close_window",
    "switch_window",
    "show_desktop",
    "move_window",
    # Files Phase 13
    "open_folder",
    "open_file",
    "search_files",
    "create_folder",
    "rename_file",
    "rename_folder",
    "copy_file",
    "move_file",
    "delete_file",
    "list_apps",
    "find_app",
    # Media Phase 13
    "volume_up",
    "volume_down",
    "set_volume",
    "mute",
    "unmute",
    "media_play_pause",
    "media_next",
    "media_previous",
    # Screenshot/clipboard
    "take_screenshot",
    "clipboard_read",
    "clipboard_clear",
    # System Phase 13
    "system_info",
    "cpu_info",
    "memory_info",
    "storage_info",
    "battery_info",
    "network_info",
    "process_info",
    "open_settings",
    "lock_pc",
    "shutdown_pc",
    "restart_pc",
    "sleep_pc",
    # Utilities
    "calculate",
    "get_time",
    # Browser actions Phase 6
    "search_web",
    "youtube_search",
    "browser_back",
    "browser_forward",
    "browser_refresh",
    "browser_scroll",
    "close_browser",
    # Vision actions Phase 7
    "analyze_screen",
    "find_screen_element",
    "get_active_window",
    "click_screen_element",
    # Meta actions (not PC, just responses)
    "unsupported",
    "clarification",
]


def _normalize_app(name: str) -> Optional[str]:
    """Resolve app name to canonical alias key, or None if unknown."""
    if not name:
        return None
    key = name.strip().lower()
    if key in APPLICATION_ALIASES:
        return key
    # word-aware substring
    for alias in APPLICATION_ALIASES:
        if alias == key or key == alias:
            return alias
        if f" {alias} " in f" {key} " or key.startswith(alias + " ") or key.endswith(" " + alias):
            return alias
    return None


def _normalize_website(name: str) -> Optional[str]:
    if not name:
        return None
    key = name.strip().lower()
    if key in WEBSITE_ALIASES:
        return key
    for alias in WEBSITE_ALIASES:
        if alias == key or f" {alias} " in f" {key} " or key.startswith(alias + " ") or key.endswith(" " + alias):
            return alias
    return None


def _is_valid_url(url: str) -> bool:
    if not url or " " in url:
        return False
    if url.startswith("http://") or url.startswith("https://"):
        return bool(re.match(r"https?://[^\s/$.?#].[^\s]*$", url))
    # bare domain like youtube.com
    if "." in url and re.match(r"^[a-z0-9.-]+\.[a-z]{2,}(/.*)?$", url.lower()):
        return True
    return False


def validate_action(data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Validate LLM structured output.

    Returns (is_valid, error_message, normalized_data).
    Normalized data has canonical keys (lowercase application, etc.).
    For unsupported/clarification, returns valid with that action (no PC exec).
    """
    if not isinstance(data, dict):
        return False, "Action must be a JSON object", None
    action = data.get("action")
    if not isinstance(action, str):
        return False, "Missing 'action' string", None
    action = action.strip().lower()
    if action not in AllowedActions:
        return False, f"Unsupported action '{action}'", None

    # Meta actions
    if action == "unsupported":
        reason = data.get("reason", "")
        if not isinstance(reason, str):
            reason = str(reason)
        return True, "", {"action": "unsupported", "reason": reason[:200]}
    if action == "clarification":
        msg = data.get("message", "")
        if not isinstance(msg, str):
            msg = str(msg)
        return True, "", {"action": "clarification", "message": msg[:300]}

    # PC actions validation
    if action == "open_application":
        app = data.get("application") or data.get("app") or data.get("name")
        if not isinstance(app, str) or not app.strip():
            return False, "open_application requires 'application' string", None
        norm = _normalize_app(app)
        if norm is None:
            # Check if LLM invented path with slashes
            if "/" in app or "\\" in app or "." in app:
                return False, "Application must be alias, not path", None
            return False, f"Unknown application '{app}'", None
        return True, "", {"action": "open_application", "application": norm}

    if action == "open_url":
        website = data.get("website") or data.get("site")
        url = data.get("url") or data.get("link")
        # Prefer website alias
        if isinstance(website, str) and website.strip():
            norm = _normalize_website(website)
            if norm is None:
                return False, f"Unknown website '{website}'", None
            return True, "", {"action": "open_url", "website": norm}
        if isinstance(url, str) and url.strip():
            url = url.strip()
            if not _is_valid_url(url):
                return False, f"Invalid URL '{url}'", None
            # Normalize bare domains to https
            if not url.startswith("http"):
                url = "https://" + url
            return True, "", {"action": "open_url", "url": url}
        return False, "open_url requires 'website' or 'url'", None

    if action == "type_text":
        text = data.get("text")
        if text is None:
            text = data.get("content", "")
        if not isinstance(text, str):
            return False, "type_text requires 'text' string", None
        if len(text) > 500:
            return False, "type_text too long (max 500)", None
        # Don't allow empty type that could be confused with command
        return True, "", {"action": "type_text", "text": text}

    if action == "press_key":
        key = data.get("key")
        if not isinstance(key, str) or not key.strip():
            return False, "press_key requires 'key'", None
        norm_key = key.strip().lower()
        if norm_key not in KEY_ALIASES:
            return False, f"Unsupported key '{key}'", None
        return True, "", {"action": "press_key", "key": norm_key}

    if action == "hotkey":
        keys = data.get("keys") or data.get("key") or data.get("hotkey")
        if isinstance(keys, str):
            # e.g., "ctrl+c" or "ctrl c"
            # Split by + or space
            delim = "+" if "+" in keys else " "
            raw = [k.strip().lower() for k in keys.split(delim) if k.strip()]
            # Map control->ctrl
            mapped = []
            for k in raw:
                if k in ("control", "ctrl"):
                    mapped.append("ctrl")
                elif k in ("windows", "win"):
                    mapped.append("win")
                elif k in ("alternate", "alt"):
                    mapped.append("alt")
                elif k == "shift":
                    mapped.append("shift")
                else:
                    mapped.append(k)
            keys = mapped
        if not isinstance(keys, list) or not keys:
            return False, "hotkey requires 'keys' list", None
        # Normalize
        normed = []
        for k in keys:
            if not isinstance(k, str):
                return False, "hotkey keys must be strings", None
            kk = k.strip().lower()
            if kk in ("control", "ctrl"):
                normed.append("ctrl")
            elif kk in ("windows", "win"):
                normed.append("win")
            elif kk in ("alternate", "alt"):
                normed.append("alt")
            else:
                normed.append(kk)
        combo = tuple(normed)
        # Allowlist check
        if combo not in ALLOWED_HOTKEYS:
            # Also allow single ctrl+char a-z
            if not (len(combo) == 2 and combo[0] == "ctrl" and len(combo[1]) == 1 and combo[1].isalpha()):
                return False, f"Hotkey not allowlisted: {keys}", None
        return True, "", {"action": "hotkey", "keys": normed}

    if action == "scroll":
        # Support direction/amount
        direction = data.get("direction")
        amount = data.get("amount")
        if isinstance(direction, str):
            d = direction.strip().lower()
            if d in ("up", "down"):
                # Use default if amount missing
                if amount is None:
                    amount = 5 if d == "up" else -5
        if amount is not None:
            try:
                amount = int(amount)
            except Exception:
                return False, "scroll amount must be int", None
            if not -20 <= amount <= 20:
                return False, "scroll amount out of range (-20..20)", None
            return True, "", {"action": "scroll", "amount": amount}
        # No amount/direction -> use default scroll up? But require explicit
        return False, "scroll requires 'amount' or 'direction'", None

    if action in ("click", "double_click", "right_click", "copy", "paste", "cut", "select_all", "undo", "redo"):
        return True, "", {"action": action}
    if action == "move_mouse":
        x = data.get("x"); y = data.get("y")
        try:
            xi = int(x) if x is not None else 0
            yi = int(y) if y is not None else 0
        except Exception:
            return False, "move_mouse requires int x,y", None
        if not 0 <= xi <= 8000 or not 0 <= yi <= 8000:
            return False, "coordinates out of range", None
        return True, "", {"action": "move_mouse", "x": xi, "y": yi}
    # Window management
    if action in ("minimize_window", "maximize_window", "restore_window", "close_window", "show_desktop"):
        return True, "", {"action": action}
    if action == "switch_window":
        target = data.get("target") or data.get("application") or data.get("name") or ""
        if not isinstance(target, str):
            return False, "switch_window requires target string", None
        return True, "", {"action": "switch_window", "target": target.strip()[:100]}
    if action == "move_window":
        direction = data.get("direction") or data.get("target") or "left"
        if not isinstance(direction, str) or direction.strip().lower() not in ("left", "right", "top", "bottom", "up", "down"):
            direction = "left"
        return True, "", {"action": "move_window", "direction": direction.strip().lower()}
    if action == "close_application":
        app = data.get("application") or data.get("target") or data.get("name") or ""
        if not isinstance(app, str):
            return False, "close_application requires application", None
        return True, "", {"action": "close_application", "application": app.strip()[:100]}
    # Files
    if action == "open_folder":
        folder = data.get("folder") or data.get("path") or data.get("target") or ""
        if not isinstance(folder, str) or not folder.strip():
            return False, "open_folder requires folder", None
        if len(folder) > 200:
            return False, "folder name too long", None
        return True, "", {"action": "open_folder", "folder": folder.strip()}
    if action == "open_file":
        path = data.get("path") or data.get("file") or ""
        if not isinstance(path, str) or not path.strip():
            return False, "open_file requires path", None
        if len(path) > 300:
            return False, "path too long", None
        return True, "", {"action": "open_file", "path": path.strip()}
    if action == "search_files":
        query = data.get("query") or data.get("text") or data.get("q") or ""
        if not isinstance(query, str) or not query.strip():
            return False, "search_files requires query", None
        if len(query) > 100:
            return False, "query too long", None
        directory = data.get("directory") or ""
        if directory and not isinstance(directory, str):
            directory = ""
        return True, "", {"action": "search_files", "query": query.strip(), "directory": directory.strip()[:100] if directory else ""}
    if action == "create_folder":
        path = data.get("path") or data.get("folder") or data.get("name") or ""
        if not isinstance(path, str) or not path.strip():
            return False, "create_folder requires path", None
        if len(path) > 200:
            return False, "path too long", None
        if "/" in path or "\\" in path or ".." in path:
            return False, "Invalid folder name", None
        return True, "", {"action": "create_folder", "path": path.strip()}
    if action in ("rename_file", "rename_folder"):
        old = data.get("old") or data.get("src") or data.get("path") or ""
        new = data.get("new") or data.get("dst") or data.get("target") or ""
        if not isinstance(old, str) or not old.strip() or not isinstance(new, str) or not new.strip():
            return False, f"{action} requires old and new", None
        return True, "", {"action": action, "old": old.strip()[:200], "new": new.strip()[:200]}
    if action in ("copy_file", "move_file"):
        src = data.get("src") or data.get("old") or data.get("path") or ""
        dst = data.get("dst") or data.get("new") or data.get("target") or ""
        if not isinstance(src, str) or not src.strip() or not isinstance(dst, str) or not dst.strip():
            return False, f"{action} requires src and dst", None
        return True, "", {"action": action, "src": src.strip()[:300], "dst": dst.strip()[:300]}
    if action == "delete_file":
        path = data.get("path") or data.get("file") or ""
        if not isinstance(path, str) or not path.strip():
            return False, "delete_file requires path", None
        return True, "", {"action": "delete_file", "path": path.strip()[:300]}
    if action in ("list_apps", "find_app"):
        if action == "find_app":
            app = data.get("application") or data.get("target") or ""
            if not isinstance(app, str) or not app.strip():
                return False, "find_app requires application", None
            return True, "", {"action": "find_app", "application": app.strip()[:100]}
        return True, "", {"action": action}
    # Media
    if action in ("volume_up", "volume_down", "mute", "unmute", "media_play_pause", "media_next", "media_previous"):
        return True, "", {"action": action}
    if action == "set_volume":
        lvl = data.get("level") or data.get("volume") or data.get("amount")
        try:
            lvl = int(lvl)
        except Exception:
            return False, "set_volume requires int level 0-100", None
        if not 0 <= lvl <= 100:
            return False, "volume out of range 0-100", None
        return True, "", {"action": "set_volume", "level": lvl}
    # Screenshot/clipboard
    if action in ("take_screenshot", "clipboard_read", "clipboard_clear"):
        return True, "", {"action": action}
    # System
    if action in ("system_info", "cpu_info", "memory_info", "storage_info", "battery_info", "network_info"):
        return True, "", {"action": action}
    if action == "process_info":
        q = data.get("query") or data.get("target") or ""
        if q and not isinstance(q, str):
            return False, "process_info query must be string", None
        return True, "", {"action": "process_info", "query": (q or "").strip()[:100]}
    if action == "open_settings":
        page = data.get("page") or data.get("target") or ""
        if page and not isinstance(page, str):
            return False, "open_settings page must be string", None
        return True, "", {"action": "open_settings", "page": (page or "").strip()[:50]}
    if action in ("lock_pc", "shutdown_pc", "restart_pc", "sleep_pc"):
        confirm = data.get("confirm", False)
        if action != "lock_pc" and not confirm:
            # Require explicit confirm param, but allow without and will ask
            return True, "", {"action": action, "confirm": bool(confirm)}
        return True, "", {"action": action, "confirm": bool(confirm)}
    if action == "calculate":
        expr = data.get("expression") or data.get("text") or data.get("query") or ""
        if not isinstance(expr, str) or not expr.strip():
            return False, "calculate requires expression", None
        if len(expr) > 100:
            return False, "expression too long", None
        return True, "", {"action": "calculate", "expression": expr.strip()}
    if action == "get_time":
        return True, "", {"action": "get_time"}

    # Browser actions Phase 6
    if action == "search_web":
        query = data.get("query") or data.get("q") or data.get("text")
        if not isinstance(query, str) or not query.strip():
            return False, "search_web requires 'query' string", None
        if len(query) > 300:
            return False, "search_web query too long (max 300)", None
        return True, "", {"action": "search_web", "query": query.strip()}
    if action == "youtube_search":
        query = data.get("query") or data.get("q") or data.get("text")
        if not isinstance(query, str) or not query.strip():
            return False, "youtube_search requires 'query' string", None
        if len(query) > 200:
            return False, "youtube_search query too long (max 200)", None
        return True, "", {"action": "youtube_search", "query": query.strip()}
    if action in ("browser_back", "browser_forward", "browser_refresh", "close_browser"):
        return True, "", {"action": action}
    if action == "browser_scroll":
        direction = data.get("direction")
        amount = data.get("amount")
        if isinstance(direction, str):
            d = direction.strip().lower()
            if d == "up":
                amount = 500 if amount is None else amount
            elif d == "down":
                amount = -500 if amount is None else amount
        if amount is not None:
            try:
                amount = int(amount)
            except Exception:
                return False, "browser_scroll amount must be int", None
            if not -2000 <= amount <= 2000:
                return False, "browser_scroll amount out of range", None
            return True, "", {"action": "browser_scroll", "amount": amount}
        return True, "", {"action": "browser_scroll", "amount": -500}

    # Vision actions Phase 7
    if action == "analyze_screen":
        q = data.get("question") or data.get("q") or data.get("prompt")
        if q is not None and not isinstance(q, str):
            return False, "analyze_screen question must be string", None
        # question optional, defaults to generic
        question = q.strip() if isinstance(q, str) and q.strip() else "What is on my screen?"
        if len(question) > 300:
            return False, "analyze_screen question too long", None
        return True, "", {"action": "analyze_screen", "question": question}
    if action == "find_screen_element":
        target = data.get("target") or data.get("label") or data.get("query")
        if not isinstance(target, str) or not target.strip():
            return False, "find_screen_element requires 'target' string", None
        if len(target) > 100:
            return False, "find_screen_element target too long", None
        return True, "", {"action": "find_screen_element", "target": target.strip()}
    if action == "get_active_window":
        return True, "", {"action": "get_active_window"}

    return False, f"Unhandled action '{action}'", None
