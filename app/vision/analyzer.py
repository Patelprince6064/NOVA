"""Screen analyzer for Nova Phase 7 — provider-abstracted vision.

Receives screenshot (PIL) + question/target, returns structured result.
Does NOT click. Optional safe visual click behind VISION_CLICK_TEST_ENABLED.

Provider abstraction: currently OpenAI vision (gpt-4o / gpt-4o-mini).
Only sends screenshot when visual command triggered, not continuously.
Handles timeout, low confidence, invalid response gracefully.
"""

import base64
import io
import json
import logging
import re
import time
from typing import Optional, List, Dict, Any

from app.vision.schemas import ScreenElement, ScreenAnalysis, FindResult
from app.vision.screenshot import ScreenCapture

logger = logging.getLogger(__name__)


class ScreenAnalyzer:
    def __init__(
        self,
        enabled: bool = True,
        provider: str = "openai",
        model: str = "",
        api_key: str = "",
        timeout_seconds: int = 15,
        min_confidence: float = 0.70,
        click_test_enabled: bool = False,
        screen_monitor: str = "primary",
        max_width: int = 1600,
        max_height: int = 1000,
    ):
        self.enabled = enabled
        self.provider = (provider or "openai").lower().strip()
        self.model = model.strip() if model else ("gpt-4o-mini" if provider == "openai" else "")
        self.api_key = api_key.strip() if api_key else ""
        self.timeout_seconds = max(1, min(60, int(timeout_seconds)))
        self.min_confidence = max(0.0, min(1.0, float(min_confidence)))
        self.click_test_enabled = bool(click_test_enabled)
        self.capture = ScreenCapture(monitor=screen_monitor, max_width=max_width, max_height=max_height)

        key_hint = (self.api_key[:4] + "…") if self.api_key else "none"
        logger.info("ScreenAnalyzer init: enabled=%s provider=%s model=%s timeout=%d conf=%.2f click_test=%s",
                    enabled, self.provider, self.model or "default", self.timeout_seconds, self.min_confidence, self.click_test_enabled)

    def is_available(self) -> bool:
        # Available even without vision API for fallback local description
        return bool(self.enabled)

    def is_vision_api_available(self) -> bool:
        return bool(self.enabled and self.api_key and self.provider == "openai")

    # ------------------------------------------------------------
    # Public API — analyze / find
    # ------------------------------------------------------------
    def analyze(self, question: str, active_window: Optional[str] = None) -> ScreenAnalysis:
        """Answer visual question about current screen. Captures on demand."""
        if not self.enabled:
            raise RuntimeError("Vision is disabled (VISION_ENABLED=false)")

        question = question.strip() if question else "What is on my screen?"
        logger.info("Vision analyze requested: %r", question[:120])

        # Capture screenshot on demand
        try:
            b64, meta = self.capture.capture_and_encode()
            # Do not log b64
        except Exception as exc:
            logger.exception("Screenshot capture failed: %s", exc)
            raise RuntimeError(f"Could not capture screen: {exc}") from exc

        # If no API key, fallback local: return active window info + monitor size
        if not self.is_vision_api_available():
            logger.info("Vision API not configured — returning fallback local analysis")
            desc = self._fallback_description(active_window, meta)
            return ScreenAnalysis(
                description=desc,
                elements=[],
                active_window=active_window,
                monitor=str(meta.get("monitor")),
                confidence=0.65,
            )

        # Call vision model
        try:
            raw = self._call_vision(b64, question, meta, active_window)
            # raw is string JSON or description
            analysis = self._parse_analysis(raw, active_window, meta)
            # Filter by confidence if needed
            if analysis.confidence < self.min_confidence and analysis.confidence != 0:
                logger.info("Analysis confidence %.2f below threshold %.2f", analysis.confidence, self.min_confidence)
            return analysis
        except TimeoutError as exc:
            logger.warning("Vision timeout: %s", exc)
            raise TimeoutError(f"Screen analysis timed out after {self.timeout_seconds}s") from exc
        except Exception as exc:
            logger.warning("Vision analyze failed: %s", exc)
            raise RuntimeError(f"Vision analysis failed: {exc}") from exc

    def find_element(self, target: str, active_window: Optional[str] = None) -> FindResult:
        """Find element by label. Returns FindResult with screen coordinates."""
        if not self.enabled:
            raise RuntimeError("Vision is disabled")
        target = target.strip() if target else ""
        if not target:
            return FindResult(found=False, label=target)

        logger.info("Vision find_element: %r", target)

        try:
            b64, meta = self.capture.capture_and_encode()
        except Exception as exc:
            logger.exception("Screenshot failed for find: %s", exc)
            raise RuntimeError(f"Could not capture screen: {exc}") from exc

        if not self.is_vision_api_available():
            logger.info("Vision API not configured — find_element fallback not found")
            return FindResult(found=False, label=target)

        try:
            raw = self._call_vision_find(b64, target, meta, active_window)
            result = self._parse_find(raw, target, meta)
            if result.found and result.confidence < self.min_confidence:
                logger.info("Find confidence %.2f below threshold %.2f -> treating as not found", result.confidence, self.min_confidence)
                return FindResult(found=False, label=target)
            return result
        except TimeoutError as exc:
            logger.warning("Find timeout: %s", exc)
            raise TimeoutError(f"Find element timed out") from exc
        except Exception as exc:
            logger.warning("Find element failed: %s", exc)
            raise RuntimeError(f"Find element failed: {exc}") from exc

    def safe_click(self, element: Dict[str, Any]) -> tuple[bool, str]:
        """Optional safe visual click — only if VISION_CLICK_TEST_ENABLED=true and confidence passes."""
        if not self.click_test_enabled:
            return False, "Visual click test is disabled (VISION_CLICK_TEST_ENABLED=false)"
        # Validate element
        from app.vision.schemas import validate_element

        ok, err = validate_element(element, self.min_confidence)
        if not ok:
            return False, f"Invalid element: {err}"
        try:
            # Check confidence explicitly
            conf = float(element.get("confidence", 0.0))
            if conf < self.min_confidence:
                return False, f"I'm not confident enough to identify that (confidence {conf:.2f} < {self.min_confidence:.2f})"
            # Move and click center
            x = int(element["x"]); y = int(element["y"])
            w = int(element["width"]); h = int(element["height"])
            cx, cy = x + w // 2, y + h // 2
            logger.info("Safe visual click: %r at (%d,%d) conf=%.2f", element.get("label"), cx, cy, conf)
            try:
                from app.pc.controller import PCController  # lazy
                # Use pyautogui via controller? Simple move
                import pyautogui  # type: ignore
                pyautogui.FAILSAFE = False
                pyautogui.moveTo(cx, cy, duration=0.2)
                pyautogui.click()
                return True, f"Clicked {element.get('label')}."
            except Exception as exc:
                logger.exception("Safe click failed: %s", exc)
                return False, "I couldn't click there."
        except Exception as exc:
            logger.exception("Safe click error: %s", exc)
            return False, "I couldn't click there."

    # ------------------------------------------------------------
    # Internal vision calls
    # ------------------------------------------------------------
    def _fallback_description(self, active_window: Optional[str], meta: Dict[str, Any]) -> str:
        orig = meta.get("original_size", (0, 0))
        if active_window:
            return f"{active_window} is open. Screen is {orig[0]}x{orig[1]}."
        return f"Screen is {orig[0]}x{orig[1]}. Vision API not configured — connect LLM vision for detailed description."

    def _call_vision(self, b64_png: str, question: str, meta: Dict[str, Any], active_window: Optional[str]) -> str:
        """Call OpenAI vision model — return raw string response."""
        if self.provider != "openai":
            raise RuntimeError(f"Unsupported vision provider: {self.provider}")
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai not installed. pip install openai")
        if not self.api_key:
            raise RuntimeError("VISION_API_KEY/OpenAI key not configured")

        client = OpenAI(api_key=self.api_key, timeout=self.timeout_seconds)
        resized = meta.get("resized_size", meta.get("original_size"))
        orig = meta.get("original_size")
        active_hint = f" Active window hint: {active_window}." if active_window else ""
        prompt = (
            f"You are Nova's screen analyzer. Answer concisely about the screenshot. "
            f"Screenshot resized to {resized} from {orig} (aspect preserved).{active_hint} "
            f"Question: {question} "
            f"Return JSON with: {{'description': string, 'elements': [{{'type':'button|text|input|link|image|icon|menu|window|unknown','label':string,'x':int,'y':int,'width':int,'height':int,'confidence':float}}], 'confidence':float}}. "
            f"Coordinates must be in resized image space {resized}. Keep description 1-3 sentences. If unsure, say so."
        )
        logger.info("Calling vision API: model=%s question=%r", self.model or "gpt-4o-mini", question[:80])
        t0 = time.time()
        resp = client.chat.completions.create(
            model=self.model or "gpt-4o-mini",
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_png}", "detail": "high"}},
                ]},
            ],
            max_tokens=700,
            timeout=self.timeout_seconds,
            temperature=0.2,
        )
        dt = time.time() - t0
        logger.info("Vision API done in %.2fs", dt)
        if not resp.choices or not resp.choices[0].message or not resp.choices[0].message.content:
            return ""
        return resp.choices[0].message.content.strip()

    def _call_vision_find(self, b64_png: str, target: str, meta: Dict[str, Any], active_window: Optional[str]) -> str:
        if self.provider != "openai":
            raise RuntimeError(f"Unsupported vision provider: {self.provider}")
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai not installed")
        if not self.api_key:
            raise RuntimeError("VISION_API_KEY not configured")

        client = OpenAI(api_key=self.api_key, timeout=self.timeout_seconds)
        resized = meta.get("resized_size", meta.get("original_size"))
        orig = meta.get("original_size")
        prompt = (
            f"Find the UI element labeled '{target}' in the screenshot. Screenshot resized to {resized} from {orig}. "
            f"Return ONLY JSON: {{'found': bool, 'label': string, 'x':int,'y':int,'width':int,'height':int,'confidence':float,'type': string}}. "
            f"Coordinates in resized image space. If not found, return {{'found': false}}. Confidence 0-1."
        )
        logger.info("Calling vision find: target=%r", target)
        resp = client.chat.completions.create(
            model=self.model or "gpt-4o-mini",
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_png}", "detail": "high"}},
                ]},
            ],
            max_tokens=300,
            timeout=self.timeout_seconds,
            temperature=0.1,
        )
        if not resp.choices or not resp.choices[0].message or not resp.choices[0].message.content:
            return ""
        return resp.choices[0].message.content.strip()

    # ------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------
    def _parse_analysis(self, raw: str, active_window: Optional[str], meta: Dict[str, Any]) -> ScreenAnalysis:
        # Try extract JSON
        import json as _json
        import re as _re

        raw_stripped = raw.strip()
        # Try JSON object
        json_str = None
        # Handle code fences
        if "```" in raw_stripped:
            m = _re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_stripped, _re.DOTALL)
            if m:
                json_str = m.group(1)
        if not json_str:
            start = raw_stripped.find("{")
            end = raw_stripped.rfind("}")
            if start != -1 and end != -1 and end > start:
                json_str = raw_stripped[start:end+1]

        if json_str:
            try:
                data = _json.loads(json_str)
                desc = str(data.get("description", raw_stripped[:300])).strip()
                if not desc:
                    desc = raw_stripped[:300]
                elems_raw = data.get("elements", [])
                elems: List[ScreenElement] = []
                for e in elems_raw[:20]:  # limit
                    if not isinstance(e, dict):
                        continue
                    try:
                        # Vision coords are in resized space; convert to screen
                        x = int(e.get("x", 0)); y = int(e.get("y", 0))
                        w = int(e.get("width", 0)); h = int(e.get("height", 0))
                        if w == 0 or h == 0:
                            continue
                        x_s, y_s, w_s, h_s = ScreenCapture.vision_to_screen(x, y, w, h, meta)
                        elems.append(ScreenElement(
                            type=str(e.get("type", "unknown")).lower(),
                            label=str(e.get("label", ""))[:100],
                            x=x_s, y=y_s, width=w_s, height=h_s,
                            confidence=float(e.get("confidence", 0.7)),
                        ))
                    except Exception:
                        continue
                conf = float(data.get("confidence", 0.7)) if isinstance(data.get("confidence"), (int, float)) else 0.7
                return ScreenAnalysis(description=desc[:500], elements=elems, active_window=active_window, monitor=str(meta.get("monitor")), confidence=conf)
            except Exception as exc:
                logger.warning("Failed to parse analysis JSON: %s", exc)
        # Fallback: treat raw as description
        desc = raw_stripped[:500].replace("\n", " ").strip()
        return ScreenAnalysis(description=desc or "I see a computer screen.", elements=[], active_window=active_window, monitor=str(meta.get("monitor")), confidence=0.6)

    def _parse_find(self, raw: str, target: str, meta: Dict[str, Any]) -> FindResult:
        import json as _json
        import re as _re
        s = raw.strip()
        json_str = None
        if "```" in s:
            m = _re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, _re.DOTALL)
            if m:
                json_str = m.group(1)
        if not json_str:
            start = s.find("{")
            end = s.rfind("}")
            if start != -1 and end != -1:
                json_str = s[start:end+1]
        if json_str:
            try:
                data = _json.loads(json_str)
                found = bool(data.get("found", False))
                if not found:
                    return FindResult(found=False, label=target)
                x = int(data.get("x", 0)); y = int(data.get("y", 0))
                w = int(data.get("width", 50)); h = int(data.get("height", 20))
                conf = float(data.get("confidence", 0.7))
                typ = str(data.get("type", "unknown")).lower()
                label = str(data.get("label", target))
                x_s, y_s, w_s, h_s = ScreenCapture.vision_to_screen(x, y, w, h, meta)
                return FindResult(found=True, label=label, x=x_s, y=y_s, width=w_s, height=h_s, confidence=conf, type=typ)
            except Exception as exc:
                logger.warning("Find parse failed: %s", exc)
        # If raw contains false, return not found
        if '"found": false' in s.lower() or '"found":false' in s.lower():
            return FindResult(found=False, label=target)
        return FindResult(found=False, label=target)
