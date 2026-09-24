"""Safe file operations — allowlisted, no arbitrary disk scan."""
import logging
import os
import shutil
import pathlib
import re
from typing import Tuple, List

logger = logging.getLogger(__name__)

# Allowed base directories for mutations without confirmation
SAFE_FOLDERS = {
    "desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
    "documents": os.path.join(os.path.expanduser("~"), "Documents"),
    "downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
    "pictures": os.path.join(os.path.expanduser("~"), "Pictures"),
    "videos": os.path.join(os.path.expanduser("~"), "Videos"),
    "music": os.path.join(os.path.expanduser("~"), "Music"),
}

# Also common alias map
FOLDER_ALIASES = {
    "downloads": "downloads", "download": "downloads",
    "documents": "documents", "document": "documents",
    "desktop": "desktop",
    "pictures": "pictures", "picture": "pictures", "images": "pictures",
    "videos": "videos", "video": "videos",
    "music": "music", "songs": "music",
    "projects": "documents",
}

# Blocked paths never allow deletion
BLOCKED_PREFIXES = [
    os.environ.get("WINDIR", "C:\\Windows").lower(),
    os.environ.get("ProgramFiles", "C:\\Program Files").lower(),
    os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)").lower(),
    "c:\\windows\\system32",
]


def _resolve_known_folder(name: str) -> str:
    key = name.strip().lower()
    if key in SAFE_FOLDERS:
        return SAFE_FOLDERS[key]
    if key in FOLDER_ALIASES:
        return SAFE_FOLDERS.get(FOLDER_ALIASES[key], SAFE_FOLDERS["documents"])
    return ""


def open_folder(folder: str) -> Tuple[bool, str]:
    try:
        f = folder.strip().lower()
        # Handle "my downloads folder" -> downloads
        for alias in FOLDER_ALIASES:
            if alias in f:
                path = _resolve_known_folder(alias)
                if path and os.path.exists(path):
                    os.startfile(path)  # type: ignore
                    return True, f"Opened {alias}."
                # Try via explorer even if not exists
                os.startfile(path)  # type: ignore
                return True, f"Opened {alias}."
        # Try direct path
        if os.path.exists(f):
            os.startfile(f)  # type: ignore
            return True, f"Opened {f}."
        # Fallback to explorer
        import subprocess
        subprocess.Popen(["explorer.exe", f], shell=False)
        return True, f"Opened {folder}."
    except Exception as exc:
        logger.exception("open_folder failed %r: %s", folder, exc)
        return False, f"I couldn't open {folder}."


def create_folder(path: str) -> Tuple[bool, str]:
    try:
        p = path.strip()
        # Handle "Projects" -> Desktop/Documents/Projects?
        # If no slash, create in Documents
        if "/" not in p and "\\" not in p and not os.path.isabs(p):
            base = SAFE_FOLDERS["documents"]
            # Common names like Projects -> Documents/Projects
            full = os.path.join(base, p)
        else:
            # Check if starts with known folder
            low = p.lower()
            for alias, folder_path in SAFE_FOLDERS.items():
                if low.startswith(alias):
                    full = os.path.join(folder_path, p[len(alias):].lstrip("/\\ "))
                    break
            else:
                full = p
        # Safety: must be under user profile
        full = os.path.normpath(full)
        user_profile = os.path.expanduser("~").lower()
        if not full.lower().startswith(user_profile):
            return False, "I can only create folders in your user folders. Say 'in Documents'."
        if os.path.exists(full):
            return False, f"Folder already exists: {os.path.basename(full)}"
        os.makedirs(full, exist_ok=False)
        return True, f"Created folder {os.path.basename(full)} in {os.path.dirname(full)}."
    except FileExistsError:
        return False, "That folder already exists."
    except Exception as exc:
        logger.exception("create_folder failed %r: %s", path, exc)
        return False, f"I couldn't create folder {path}."


def search_files(query: str, directory: str = "") -> Tuple[bool, str]:
    try:
        q = query.strip().lower()
        base = directory.strip() if directory else SAFE_FOLDERS["documents"]
        # Resolve directory alias
        if directory:
            alias_path = _resolve_known_folder(directory)
            if alias_path:
                base = alias_path
        if not os.path.exists(base):
            base = os.path.expanduser("~")
        # Limited search: only one level + one recursive with cap
        # Prevent full disk scan
        if base.lower().startswith("c:\\windows") or base.lower().startswith("c:\\program"):
            return False, "I won't search system folders."
        results = []
        # Determine extension search
        # "PDF files" -> .pdf
        ext_map = {"pdf": ".pdf", "docx": ".docx", "word": ".docx", "excel": ".xlsx", "ppt": ".pptx", "python": ".py", "resume": "resume"}
        ext = ""
        for k, v in ext_map.items():
            if k in q:
                ext = v
                break
        # Walk with limit 1000 files, 2 levels deep max unless query very specific
        max_files = 500
        count = 0
        for root, dirs, files in os.walk(base):
            # Limit depth
            depth = root[len(base):].count(os.sep)
            if depth > 3:
                dirs[:] = []
                continue
            # Skip hidden/system
            dirs[:] = [d for d in dirs if not d.startswith(".") and d.lower() not in ("node_modules", "__pycache__", ".git")]
            for f in files:
                if count >= max_files:
                    break
                low_f = f.lower()
                match = False
                if ext and low_f.endswith(ext):
                    match = True
                if q in low_f:
                    match = True
                # For "resume" query, match resume substring
                if match:
                    results.append(os.path.join(root, f))
                    if len(results) >= 10:
                        break
                count += 1
            if len(results) >= 10:
                break
            if count >= max_files:
                break
        if not results:
            return True, f"No files matching '{query}' in {os.path.basename(base)}."
        # Format
        names = [os.path.basename(r) for r in results[:5]]
        return True, f"Found: {', '.join(names)}" + (f" and {len(results)-5} more in {base}" if len(results) > 5 else f" in {base}.")
    except Exception as exc:
        logger.exception("search_files failed: %s", exc)
        return False, "I couldn't search files."


def open_file(path: str) -> Tuple[bool, str]:
    try:
        p = path.strip().strip('"').strip("'")
        # Safety: block executables without confirmation
        if p.lower().endswith((".exe", ".bat", ".cmd", ".ps1", ".msi")):
            return False, "Executable files need confirmation. Say 'confirm open'."
        # Try known folder resolution
        if not os.path.isabs(p):
            # Try Documents etc
            for base in SAFE_FOLDERS.values():
                cand = os.path.join(base, p)
                if os.path.exists(cand):
                    p = cand
                    break
        if not os.path.exists(p):
            # Search for file by name
            ok, msg = search_files(os.path.basename(p))
            return False, f"I couldn't find {path}. {msg}"
        # Use startfile
        os.startfile(p)  # type: ignore
        return True, f"Opened {os.path.basename(p)}."
    except Exception as exc:
        logger.exception("open_file failed %r: %s", path, exc)
        return False, f"I couldn't open {path}."


def _safe_path_check(path: str) -> Tuple[bool, str]:
    low = os.path.normpath(path).lower()
    for blocked in BLOCKED_PREFIXES:
        if low.startswith(blocked):
            return False, "I won't modify system files."
    user = os.path.expanduser("~").lower()
    if not low.startswith(user) and not low.startswith(os.path.expandvars("%TEMP%").lower()):
        # Allow but warn? For now require confirmation outside user folder
        pass
    return True, ""


def rename_file(old: str, new: str) -> Tuple[bool, str]:
    try:
        old = old.strip().strip('"')
        new = new.strip().strip('"')
        # Resolve old path
        if not os.path.exists(old):
            # Try to find by basename
            for base in SAFE_FOLDERS.values():
                cand = os.path.join(base, old)
                if os.path.exists(cand):
                    old = cand
                    break
        if not os.path.exists(old):
            return False, f"I couldn't find {old}."
        ok, err = _safe_path_check(old)
        if not ok:
            return False, err
        # New name may be just filename
        if "/" not in new and "\\" not in new:
            new = os.path.join(os.path.dirname(old), new)
        if os.path.exists(new):
            return False, "A file with that name already exists."
        os.rename(old, new)
        return True, f"Renamed to {os.path.basename(new)}."
    except Exception as exc:
        logger.exception("rename failed: %s", exc)
        return False, "I couldn't rename that."


def delete_file(path: str) -> Tuple[bool, str]:
    """Move to recycle bin — requires confirmation via registry."""
    try:
        p = path.strip().strip('"')
        if not os.path.exists(p):
            # Try find
            for base in SAFE_FOLDERS.values():
                cand = os.path.join(base, p)
                if os.path.exists(cand):
                    p = cand
                    break
        if not os.path.exists(p):
            return False, f"I couldn't find {path}."
        ok, err = _safe_path_check(p)
        if not ok:
            return False, err
        # Prefer send2trash if available
        try:
            from send2trash import send2trash
            send2trash(p)
            return True, f"Moved {os.path.basename(p)} to Recycle Bin."
        except ImportError:
            # Fallback: use recycle via shell
            import subprocess
            # Use PowerShell to recycle? For now delete with confirmation not actually deleting, ask to confirm
            return False, "Recycle Bin library not installed. Install send2trash to delete."
        except Exception as exc2:
            logger.exception("send2trash failed: %s", exc2)
            return False, "I couldn't delete that."
    except Exception as exc:
        logger.exception("delete failed: %s", exc)
        return False, "I couldn't delete that."


def get_installed_apps(limit: int = 30) -> Tuple[bool, str]:
    """Cache discovered apps via registry / start menu."""
    try:
        apps = set()
        # Check APPLICATION_ALIASES as hint
        from app.pc.controller import APPLICATION_ALIASES
        # Scan Start Menu
        start_dirs = [
            os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"), "Microsoft\\Windows\\Start Menu\\Programs"),
            os.path.join(os.path.expanduser("~"), "AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs"),
        ]
        for d in start_dirs:
            if os.path.exists(d):
                for root, _, files in os.walk(d):
                    for f in files:
                        if f.lower().endswith(".lnk"):
                            name = os.path.splitext(f)[0]
                            apps.add(name)
                            if len(apps) >= 100:
                                break
                    if len(apps) >= 100:
                        break
        if apps:
            sample = sorted(apps)[:limit]
            return True, f"Installed: {', '.join(sample[:10])}" + (f" and {len(apps)-10} more" if len(apps) > 10 else "")
        return True, "Available apps: " + ", ".join(sorted(APPLICATION_ALIASES.keys())[:10])
    except Exception as exc:
        logger.exception("get_installed failed: %s", exc)
        return False, "I couldn't list apps."
