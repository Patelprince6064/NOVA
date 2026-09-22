"""Windows startup via Startup folder — no admin required."""

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

def _startup_folder() -> Path | None:
    try:
        appdata = os.getenv("APPDATA")
        if not appdata:
            # fallback
            appdata = str(Path.home() / "AppData" / "Roaming")
        folder = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        return folder
    except Exception as exc:
        logger.warning("Could not resolve Startup folder: %s", exc)
        return None

def _target_bat_path() -> Path | None:
    folder = _startup_folder()
    if not folder:
        return None
    return folder / "Nova.bat"

def enable_startup():
    """Create Nova.bat in Startup folder to launch run.py with pythonw."""
    folder = _startup_folder()
    bat = _target_bat_path()
    if not folder or not bat:
        logger.warning("Startup not supported on this system")
        return False
    try:
        folder.mkdir(parents=True, exist_ok=True)
        # Determine python executable and project root
        python_exe = sys.executable
        # Prefer pythonw for no console
        pythonw = python_exe.replace("python.exe", "pythonw.exe")
        if not Path(pythonw).exists():
            pythonw = python_exe
        project_root = Path(__file__).resolve().parents[2]
        run_py = project_root / "run.py"
        # Batch content — cd to project and launch
        content = f'@echo off\r\ncd /d "{project_root}"\r\nstart "" "{pythonw}" "{run_py}"\r\n'
        bat.write_text(content, encoding="utf-8")
        logger.info("Enabled startup: %s", bat)
        print(f"Startup enabled: {bat}")
        return True
    except Exception as exc:
        logger.warning("Enable startup failed: %s", exc)
        return False

def disable_startup():
    bat = _target_bat_path()
    if not bat:
        return False
    try:
        if bat.exists():
            bat.unlink()
            logger.info("Disabled startup: %s", bat)
            print(f"Startup disabled: {bat}")
        return True
    except Exception as exc:
        logger.warning("Disable startup failed: %s", exc)
        return False

def is_startup_enabled() -> bool:
    bat = _target_bat_path()
    return bool(bat and bat.exists())

def sync_startup_setting(config):
    """Called at startup to sync START_WITH_WINDOWS setting (opt-in only)."""
    if not config:
        return
    wanted = bool(getattr(config, "start_with_windows", False))
    enabled = is_startup_enabled()
    if wanted and not enabled:
        enable_startup()
    elif not wanted and enabled:
        # Do not auto-disable if user manually enabled? But respect config false
        # Only disable if explicitly false and we manage it
        disable_startup()
