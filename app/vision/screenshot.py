"""On-demand screenshot capture for Nova (Phase 7) — MSS + Pillow.

Privacy: not saved permanently, only in-memory PIL Image, resized if configured,
preserves aspect ratio, corrects coordinates for vision scaling, multi-monitor.

Only called when visual command triggers; normal commands do NOT capture.
"""

import logging
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import mss  # type: ignore
except ImportError:
    mss = None  # type: ignore

try:
    from PIL import Image, ImageGrab  # type: ignore
except ImportError:
    Image = None  # type: ignore
    ImageGrab = None  # type: ignore


class ScreenCapture:
    """Capture screen on demand, with monitor selection and resize."""

    def __init__(
        self,
        monitor: str = "primary",  # primary, all, 1, 2, etc.
        max_width: int = 1600,
        max_height: int = 1000,
    ):
        self.monitor = monitor.strip().lower() if monitor else "primary"
        self.max_width = max(320, min(3840, int(max_width)))
        self.max_height = max(240, min(2160, int(max_height)))
        logger.info("ScreenCapture init: monitor=%s max=%dx%d", self.monitor, self.max_width, self.max_height)

    # ------------------------------------------------------------
    # Monitor detection
    # ------------------------------------------------------------
    def list_monitors(self) -> List[Dict[str, Any]]:
        """Return list of monitors with index, width, height, left, top, is_primary."""
        if mss is not None:
            try:
                with mss.mss() as sct:
                    mons = sct.monitors  # index 0 = All, 1 = primary
                    result = []
                    for idx, m in enumerate(mons):
                        result.append({
                            "index": idx,
                            "left": m.get("left", 0),
                            "top": m.get("top", 0),
                            "width": m.get("width", 0),
                            "height": m.get("height", 0),
                            "is_primary": idx == 1,
                        })
                    return result
            except Exception as exc:
                logger.warning("mss list monitors failed: %s", exc)
        # Fallback via PIL / win32
        try:
            if Image is not None:
                # Try to get size via ImageGrab
                # PIL ImageGrab.grab() gives primary monitor size
                img = ImageGrab.grab() if ImageGrab else None
                if img is not None:
                    w, h = img.size
                    return [{"index": 1, "left": 0, "top": 0, "width": w, "height": h, "is_primary": True}]
        except Exception as exc:
            logger.debug("PIL monitor fallback failed: %s", exc)
        return []

    def _resolve_monitor_index(self) -> int:
        """Map config monitor string to mss index."""
        mons = self.list_monitors()
        if not mons:
            return 1
        cfg = self.monitor
        if cfg == "primary":
            return 1
        if cfg == "all":
            return 0
        try:
            idx = int(cfg)
            # mss indices are 1..n, 0 = all
            if 0 <= idx < len(mons):
                return idx
            if 1 <= idx <= len(mons) - 1:
                return idx
        except Exception:
            pass
        return 1

    # ------------------------------------------------------------
    # Capture
    # ------------------------------------------------------------
    def capture_screen(self) -> Tuple[Any, Dict[str, Any]]:
        """Capture screen and return (PIL Image, metadata).

        Metadata: {"monitor":..., "original_size":(w,h), "resized_size":(w,h), "scale":...}
        Image is in-memory, not saved.
        """
        if Image is None:
            raise RuntimeError("Pillow not installed. Run: pip install Pillow")
        # Prefer MSS (faster, multi-monitor)
        img = None
        orig_w = orig_h = 0
        mon_idx = self._resolve_monitor_index()
        mon_info = None

        if mss is not None:
            try:
                with mss.mss() as sct:
                    mons = sct.monitors
                    target = mons[mon_idx] if 0 <= mon_idx < len(mons) else mons[1]
                    mon_info = target
                    shot = sct.grab(target)
                    img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                    orig_w, orig_h = img.size
                    logger.info("Screenshot captured via mss: monitor=%s size=%dx%d", mon_idx, orig_w, orig_h)
            except Exception as exc:
                logger.warning("mss capture failed (falling back to PIL): %s", exc)
                img = None

        if img is None:
            # Fallback PIL
            if ImageGrab is None:
                raise RuntimeError("No screenshot backend available (install mss or Pillow)")
            try:
                # ImageGrab.grab() captures primary; for 'all' use all_screens
                if self.monitor == "all" and hasattr(ImageGrab, "grab"):
                    img = ImageGrab.grab(all_screens=True)  # type: ignore
                else:
                    img = ImageGrab.grab()
                orig_w, orig_h = img.size
                # Ensure RGB
                if img.mode != "RGB":
                    img = img.convert("RGB")
                logger.info("Screenshot captured via PIL: size=%dx%d", orig_w, orig_h)
            except Exception as exc:
                logger.exception("PIL capture failed: %s", exc)
                raise RuntimeError(f"Screenshot capture failed: {exc}") from exc

        # Resize if needed, preserve aspect
        scale = 1.0
        w, h = orig_w, orig_h
        if w > self.max_width or h > self.max_height:
            # Compute scale to fit within max
            scale_w = self.max_width / w
            scale_h = self.max_height / h
            scale = min(scale_w, scale_h)
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            try:
                # Pillow 10+ uses Resampling
                resample = getattr(Image, "Resampling", Image).LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS  # type: ignore
                img = img.resize((new_w, new_h), resample)
                logger.info("Screenshot resized: %dx%d -> %dx%d scale=%.3f", orig_w, orig_h, new_w, new_h, scale)
                w, h = new_w, new_h
            except Exception as exc:
                logger.warning("Resize failed: %s", exc)
                scale = 1.0

        meta = {
            "monitor": self.monitor,
            "monitor_index": mon_idx,
            "monitor_info": mon_info,
            "original_size": (orig_w, orig_h),
            "resized_size": (w, h),
            "scale": scale,
        }
        # Do NOT save to disk
        return img, meta

    def capture_and_encode(self) -> Tuple[str, Dict[str, Any]]:
        """Capture and return base64-encoded PNG for vision API (plus meta). Caller should not log the base64."""
        import base64, io

        img, meta = self.capture_screen()
        buf = io.BytesIO()
        # Save as PNG in memory; use optimize to reduce size
        img.save(buf, format="PNG", optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        logger.debug("Screenshot encoded: %d bytes base64, original=%s resized=%s", len(b64), meta["original_size"], meta["resized_size"])
        return b64, meta

    # ------------------------------------------------------------
    # Coordinate conversion
    # ------------------------------------------------------------
    @staticmethod
    def vision_to_screen(x: int, y: int, w: int, h: int, meta: Dict[str, Any]) -> tuple[int, int, int, int]:
        """Convert vision coordinates (resized image space) back to original screen coordinates.

        Handles scaling + monitor offset.
        """
        scale = meta.get("scale", 1.0)
        mon_info = meta.get("monitor_info")
        left = mon_info.get("left", 0) if isinstance(mon_info, dict) else 0
        top = mon_info.get("top", 0) if isinstance(mon_info, dict) else 0
        # Resized coords -> original
        if scale != 1.0 and scale != 0:
            x_orig = int(x / scale) + left
            y_orig = int(y / scale) + top
            w_orig = int(w / scale)
            h_orig = int(h / scale)
        else:
            x_orig, y_orig, w_orig, h_orig = x + left, y + top, w, h
        return x_orig, y_orig, w_orig, h_orig
