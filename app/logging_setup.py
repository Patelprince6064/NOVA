"""Logging setup for Nova — file rotation, logs/nova.log + logs/errors.log"""

import logging
import logging.handlers
from pathlib import Path

def setup_logging(config):
    level_name = getattr(config, "log_level", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    max_mb = getattr(config, "log_max_mb", 5)
    backup = getattr(config, "log_backup_count", 3)

    logs_dir = Path(__file__).resolve().parent.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Root logger
    root = logging.getLogger()
    root.setLevel(level)

    # Clear existing handlers to avoid duplicate
    for h in list(root.handlers):
        root.removeHandler(h)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # Console handler (quiet normal mode, only INFO+)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # File handler — nova.log (rotation)
    try:
        fh = logging.handlers.RotatingFileHandler(
            logs_dir / "nova.log",
            maxBytes=max_mb * 1024 * 1024,
            backupCount=backup,
            encoding="utf-8",
        )
        fh.setLevel(level)
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except Exception as exc:
        logging.warning("Could not create nova.log handler: %s", exc)

    # Errors only
    try:
        eh = logging.handlers.RotatingFileHandler(
            logs_dir / "errors.log",
            maxBytes=max_mb * 1024 * 1024,
            backupCount=backup,
            encoding="utf-8",
        )
        eh.setLevel(logging.WARNING)
        eh.setFormatter(fmt)
        root.addHandler(eh)
    except Exception as exc:
        logging.warning("Could not create errors.log handler: %s", exc)

    logging.info("Logging initialized: level=%s dir=%s max=%dMB backups=%d", level_name, logs_dir, max_mb, backup)
    # Silence noisy libraries unless DEBUG
    if level_name != "DEBUG":
        for noisy in ("urllib3", "openai", "httpcore", "httpx"):
            logging.getLogger(noisy).setLevel(logging.WARNING)
