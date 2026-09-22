"""Structured schemas for Nova vision (Phase 7).

No screenshots stored, no code execution. Coordinates are approximate screen
positions in original monitor space (after resize correction).
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Literal, Dict, Any
import logging

logger = logging.getLogger(__name__)

ElementType = Literal["button", "text", "input", "link", "image", "icon", "menu", "window", "unknown"]


@dataclass
class ScreenElement:
    type: str  # ElementType
    label: str
    x: int
    y: int
    width: int
    height: int
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    def is_valid(self) -> bool:
        return bool(self.label) and self.width > 0 and self.height > 0 and 0.0 <= self.confidence <= 1.0


@dataclass
class ScreenAnalysis:
    description: str
    elements: List[ScreenElement]
    active_window: Optional[str] = None
    monitor: Optional[str] = None
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "elements": [e.to_dict() for e in self.elements],
            "active_window": self.active_window,
            "monitor": self.monitor,
            "confidence": self.confidence,
        }


@dataclass
class FindResult:
    found: bool
    label: str
    x: Optional[int] = None
    y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    confidence: float = 0.0
    type: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"found": self.found, "label": self.label}
        if self.found:
            d.update({"x": self.x, "y": self.y, "width": self.width, "height": self.height, "confidence": self.confidence, "type": self.type})
        return d


def validate_element(data: Dict[str, Any], min_confidence: float = 0.0) -> tuple[bool, str]:
    """Check element dict; used to gate future click."""
    required = ("type", "label", "x", "y", "width", "height")
    for k in required:
        if k not in data:
            return False, f"Missing {k}"
    try:
        conf = float(data.get("confidence", 0.0))
    except Exception:
        return False, "Invalid confidence"
    if conf < min_confidence:
        return False, f"Confidence {conf:.2f} below threshold {min_confidence:.2f}"
    # Basic bounds check (assume 8k max)
    for coord in ("x", "y", "width", "height"):
        try:
            v = int(data[coord])
            if not 0 <= v <= 8000:
                return False, f"Invalid {coord}={v}"
        except Exception:
            return False, f"Invalid {coord}"
    return True, ""
