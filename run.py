#!/usr/bin/env python3
"""Nova — single entry point.  `python run.py`  (or `python -m app.main`)
Handles config load, startup validation, logging setup, health screen, and safe shutdown.
"""

import sys
import os
import logging
from pathlib import Path

# Ensure nova root on path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def _setup_logging(config):
    """Configure file + console logging with rotation."""
    try:
        from app.logging_setup import setup_logging
        setup_logging(config)
    except Exception as exc:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        logging.warning("Logging setup failed, fallback to basic: %s", exc)

def _validate_startup(config) -> bool:
    """Startup validation — friendly messages, no huge traceback."""
    from app.health.checker import run_health_check, print_health

    health = run_health_check(config)
    # Show first-run screen
    print("\n=================================")
    print(f"        {config.nova_name.upper()} ASSISTANT")
    print("=================================\n")
    print_health(health, verbose=False)

    # Critical failures
    if not health.get("microphone"):
        print(f"\n{config.nova_name} could not start because the microphone is unavailable.")
        print("Check: Windows Settings → Privacy & security → Microphone → Allow access")
        print("Basic commands will still be tried, but voice input will fail.\n")
        # Don't exit — allow degraded mode but warn
    if health.get("speech") is False:
        print("Speech model not ready. On first run, Whisper will download (see logs/nova.log).")
    if config.llm_enabled and not health.get("ai"):
        print("AI features are disabled because the API configuration is missing.")
        print("Basic PC commands will still work. Set LLM_API_KEY in .env to enable AI.\n")
    if config.browser_enabled and not health.get("browser"):
        print("Browser control unavailable (Playwright not installed). Run: setup_browser.bat\n")
    if config.vision_enabled and not health.get("vision"):
        print("Screen vision is disabled or unavailable.\n")

    # Create required directories
    try:
        (ROOT / "logs").mkdir(exist_ok=True)
        (ROOT / "models").mkdir(exist_ok=True)
    except Exception as exc:
        logging.warning("Could not create dirs: %s", exc)

    return True

def main():
    # Load config first for logging level
    try:
        from app.config import Config
        config = Config.load()
    except Exception as exc:
        print(f"Failed to load configuration: {exc}")
        sys.exit(1)

    _setup_logging(config)
    log = logging.getLogger(__name__)
    log.info("Starting %s...", config.nova_name)

    # Minimal startup banner
    print(f"\nStarting {config.nova_name}...")

    if not _validate_startup(config):
        sys.exit(1)

    # Show ready checks
    print("\nStarting components...")
    try:
        from app.main import main as nova_main
    except Exception as exc:
        log.exception("Failed to import Nova main: %s", exc)
        print(f"Nova failed to start: {exc}")
        print("See logs/errors.log for details.")
        sys.exit(1)

    try:
        nova_main()
    except KeyboardInterrupt:
        print(f"\n{config.nova_name} stopped by user.")
    except SystemExit:
        raise
    except Exception as exc:
        log.exception("Unhandled exception in Nova: %s", exc)
        print(f"\n{config.nova_name} encountered an error: {exc}")
        print("See logs/errors.log. Nova will exit.")
        sys.exit(1)
    finally:
        log.info("%s stopped.", config.nova_name)
        print(f"\n{config.nova_name} stopped.")

if __name__ == "__main__":
    main()
