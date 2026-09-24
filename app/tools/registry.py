"""Central safe tool registry for Nova Phase 13.

Each tool has: name, description, permission level, confirmation requirement, executor.
No shell/eval — all dispatch via validated controllers.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any

logger = logging.getLogger(__name__)

PERMISSION_SAFE = "SAFE"
PERMISSION_CONFIRM = "CONFIRMATION_REQUIRED"
PERMISSION_UNSUPPORTED = "NOT_SUPPORTED"


@dataclass
class ToolDefinition:
    name: str
    description: str
    permission: str = PERMISSION_SAFE
    requires_confirmation: bool = False
    category: str = "general"
    aliases: List[str] = field(default_factory=list)
    parameters: Dict[str, str] = field(default_factory=dict)


# Central registry — single source of truth for help & validation
TOOL_DEFINITIONS: List[ToolDefinition] = [
    # Applications
    ToolDefinition("open_application", "Open a Windows application by alias", PERMISSION_SAFE, False, "applications", ["launch", "start", "bring up"], {"application": "str alias"}),
    ToolDefinition("close_application", "Close application/window gracefully", PERMISSION_SAFE, False, "applications", ["close app", "exit app"], {"application": "str optional"}),
    ToolDefinition("find_app", "Check if application is installed", PERMISSION_SAFE, False, "applications", ["is installed", "find app"], {"application": "str"}),
    ToolDefinition("list_apps", "List installed applications (cached)", PERMISSION_SAFE, False, "applications", ["what apps", "installed apps"], {}),

    # Window management
    ToolDefinition("minimize_window", "Minimize active window", PERMISSION_SAFE, False, "windows", ["minimize"], {}),
    ToolDefinition("maximize_window", "Maximize active window", PERMISSION_SAFE, False, "windows", ["maximize"], {}),
    ToolDefinition("restore_window", "Restore active window", PERMISSION_SAFE, False, "windows", ["restore"], {}),
    ToolDefinition("close_window", "Close active window", PERMISSION_SAFE, False, "windows", ["close window", "close this"], {}),
    ToolDefinition("switch_window", "Switch to window by name or previous", PERMISSION_SAFE, False, "windows", ["switch to", "alt tab"], {"target": "str"}),
    ToolDefinition("show_desktop", "Show desktop (Win+D)", PERMISSION_SAFE, False, "windows", ["show desktop"], {}),
    ToolDefinition("move_window", "Move/snap window", PERMISSION_SAFE, False, "windows", ["snap", "move window"], {"direction": "str left/right/top/bottom"}),

    # Keyboard / mouse
    ToolDefinition("type_text", "Type text into focused window", PERMISSION_SAFE, False, "keyboard", ["type", "write"], {"text": "str"}),
    ToolDefinition("press_key", "Press a single key", PERMISSION_SAFE, False, "keyboard", ["press", "hit"], {"key": "str"}),
    ToolDefinition("hotkey", "Press key combination", PERMISSION_SAFE, False, "keyboard", ["hotkey", "shortcut"], {"keys": "list"}),
    ToolDefinition("copy", "Copy (Ctrl+C)", PERMISSION_SAFE, False, "editing", ["copy"], {}),
    ToolDefinition("paste", "Paste (Ctrl+V)", PERMISSION_SAFE, False, "editing", ["paste"], {}),
    ToolDefinition("cut", "Cut (Ctrl+X)", PERMISSION_SAFE, False, "editing", ["cut"], {}),
    ToolDefinition("select_all", "Select all (Ctrl+A)", PERMISSION_SAFE, False, "editing", ["select all"], {}),
    ToolDefinition("undo", "Undo (Ctrl+Z)", PERMISSION_SAFE, False, "editing", ["undo"], {}),
    ToolDefinition("redo", "Redo (Ctrl+Y)", PERMISSION_SAFE, False, "editing", ["redo"], {}),
    ToolDefinition("click", "Left click", PERMISSION_SAFE, False, "mouse", ["click"], {}),
    ToolDefinition("double_click", "Double click", PERMISSION_SAFE, False, "mouse", ["double click"], {}),
    ToolDefinition("right_click", "Right click", PERMISSION_SAFE, False, "mouse", ["right click"], {}),
    ToolDefinition("move_mouse", "Move mouse to coordinates", PERMISSION_SAFE, False, "mouse", ["move mouse"], {"x": "int", "y": "int"}),
    ToolDefinition("scroll", "Scroll up/down", PERMISSION_SAFE, False, "mouse", ["scroll"], {"amount": "int"}),

    # Files
    ToolDefinition("open_folder", "Open known Windows folder", PERMISSION_SAFE, False, "files", ["open folder", "downloads"], {"folder": "str"}),
    ToolDefinition("open_file", "Open a file", PERMISSION_SAFE, False, "files", ["open file"], {"path": "str"}),
    ToolDefinition("search_files", "Search files by pattern", PERMISSION_SAFE, False, "files", ["find file", "search files"], {"query": "str", "directory": "str optional"}),
    ToolDefinition("create_folder", "Create a new folder", PERMISSION_SAFE, False, "files", ["create folder"], {"path": "str"}),
    ToolDefinition("rename_file", "Rename file/folder", PERMISSION_CONFIRM, True, "files", ["rename"], {"old": "str", "new": "str"}),
    ToolDefinition("copy_file", "Copy file/folder", PERMISSION_CONFIRM, False, "files", ["copy file"], {"src": "str", "dst": "str"}),
    ToolDefinition("move_file", "Move file/folder", PERMISSION_CONFIRM, True, "files", ["move"], {"src": "str", "dst": "str"}),
    ToolDefinition("delete_file", "Delete file/folder to recycle bin", PERMISSION_CONFIRM, True, "files", ["delete"], {"path": "str"}),

    # Browser
    ToolDefinition("open_url", "Open website URL", PERMISSION_SAFE, False, "browser", ["open website", "go to"], {"website": "str alias"}),
    ToolDefinition("search_web", "Google search", PERMISSION_SAFE, False, "browser", ["google search", "search web"], {"query": "str"}),
    ToolDefinition("youtube_search", "YouTube search", PERMISSION_SAFE, False, "browser", ["youtube search", "play"], {"query": "str"}),
    ToolDefinition("browser_back", "Browser back", PERMISSION_SAFE, False, "browser", ["go back", "back"], {}),
    ToolDefinition("browser_forward", "Browser forward", PERMISSION_SAFE, False, "browser", ["go forward", "forward"], {}),
    ToolDefinition("browser_refresh", "Browser refresh", PERMISSION_SAFE, False, "browser", ["refresh", "reload"], {}),
    ToolDefinition("browser_scroll", "Browser scroll", PERMISSION_SAFE, False, "browser", ["scroll"], {"amount": "int"}),

    # Media / Volume
    ToolDefinition("volume_up", "Increase system volume", PERMISSION_SAFE, False, "media", ["volume up", "increase volume"], {}),
    ToolDefinition("volume_down", "Decrease system volume", PERMISSION_SAFE, False, "media", ["volume down", "decrease volume"], {}),
    ToolDefinition("set_volume", "Set volume 0-100", PERMISSION_SAFE, False, "media", ["set volume"], {"level": "int 0-100"}),
    ToolDefinition("mute", "Mute audio", PERMISSION_SAFE, False, "media", ["mute"], {}),
    ToolDefinition("unmute", "Unmute audio", PERMISSION_SAFE, False, "media", ["unmute"], {}),
    ToolDefinition("media_play_pause", "Play/pause media", PERMISSION_SAFE, False, "media", ["pause", "play", "resume"], {}),
    ToolDefinition("media_next", "Next track", PERMISSION_SAFE, False, "media", ["next song", "skip"], {}),
    ToolDefinition("media_previous", "Previous track", PERMISSION_SAFE, False, "media", ["previous song"], {}),

    # System
    ToolDefinition("system_info", "Show system information", PERMISSION_SAFE, False, "system", ["system info", "computer info"], {}),
    ToolDefinition("cpu_info", "Show CPU usage", PERMISSION_SAFE, False, "system", ["cpu usage"], {}),
    ToolDefinition("memory_info", "Show RAM usage", PERMISSION_SAFE, False, "system", ["ram usage", "memory"], {}),
    ToolDefinition("storage_info", "Show disk/storage", PERMISSION_SAFE, False, "system", ["storage", "disk space"], {}),
    ToolDefinition("battery_info", "Show battery status", PERMISSION_SAFE, False, "system", ["battery"], {}),
    ToolDefinition("network_info", "Show network status", PERMISSION_SAFE, False, "system", ["network", "wifi", "ip"], {}),
    ToolDefinition("process_info", "Show process info", PERMISSION_SAFE, False, "system", ["process", "cpu hungry"], {"query": "str optional"}),
    ToolDefinition("open_settings", "Open Windows settings page", PERMISSION_SAFE, False, "system", ["open settings", "wifi settings"], {"page": "str"}),
    ToolDefinition("lock_pc", "Lock workstation", PERMISSION_SAFE, False, "system", ["lock"], {}),
    ToolDefinition("shutdown_pc", "Shutdown PC", PERMISSION_CONFIRM, True, "system", ["shutdown"], {}),
    ToolDefinition("restart_pc", "Restart PC", PERMISSION_CONFIRM, True, "system", ["restart"], {}),
    ToolDefinition("sleep_pc", "Sleep PC", PERMISSION_CONFIRM, True, "system", ["sleep", "hibernate"], {}),

    # Utilities
    ToolDefinition("take_screenshot", "Take screenshot", PERMISSION_SAFE, False, "utilities", ["screenshot"], {}),
    ToolDefinition("clipboard_read", "Read clipboard", PERMISSION_SAFE, False, "utilities", ["clipboard"], {}),
    ToolDefinition("clipboard_clear", "Clear clipboard", PERMISSION_SAFE, False, "utilities", ["clear clipboard"], {}),
    ToolDefinition("calculate", "Safe calculation", PERMISSION_SAFE, False, "utilities", ["calculate", "what is"], {"expression": "str"}),
    ToolDefinition("get_time", "Current time/date", PERMISSION_SAFE, False, "utilities", ["what time", "date"], {}),

    # Vision
    ToolDefinition("analyze_screen", "Describe screen", PERMISSION_SAFE, False, "vision", ["what's on screen"], {"question": "str"}),
    ToolDefinition("find_screen_element", "Find element on screen", PERMISSION_SAFE, False, "vision", ["find", "where is"], {"target": "str"}),
    ToolDefinition("click_screen_element", "Click found element", PERMISSION_SAFE, False, "vision", ["click"], {"target": "str"}),
    ToolDefinition("get_active_window", "Get active window title", PERMISSION_SAFE, False, "vision", ["active window"], {}),
]


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {t.name: t for t in TOOL_DEFINITIONS}

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name.lower().strip())

    def all(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def by_category(self, category: str) -> List[ToolDefinition]:
        return [t for t in self._tools.values() if t.category == category]

    def requires_confirmation(self, name: str) -> bool:
        t = self.get(name)
        return bool(t and t.requires_confirmation)

    def permission(self, name: str) -> str:
        t = self.get(name)
        return t.permission if t else PERMISSION_SAFE

    def help_text(self) -> str:
        cats = {}
        for t in self._tools.values():
            cats.setdefault(t.category, []).append(t.name)
        lines = ["I can help with:"]
        for cat, names in cats.items():
            lines.append(f"- {cat}: {', '.join(names[:6])}")
        return "\n".join(lines)

    def detailed_help(self, category: Optional[str] = None) -> str:
        if category:
            tools = self.by_category(category)
        else:
            tools = self.all()
        return "\n".join(f"{t.name}: {t.description} ({t.permission})" for t in tools)


_registry: Optional[ToolRegistry] = None

def get_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
