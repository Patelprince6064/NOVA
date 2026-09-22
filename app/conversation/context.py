"""Short-term conversation context for Nova Phase 9.

In-memory only. No passwords, tokens, or permanent logs.
Expires on timeout, stop/cancel/goodbye, shutdown, or max turns.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import logging
import time

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    """Temporary context for current conversation."""

    conversation_active: bool = False
    last_application: Optional[str] = None
    current_url: Optional[str] = None
    current_site: Optional[str] = None
    last_action: Optional[str] = None
    last_search: Optional[str] = None
    last_task_status: Optional[str] = None
    turn_count: int = 0
    # Extra bookkeeping — not sensitive
    last_user_text: Optional[str] = None
    last_assistant_response: Optional[str] = None
    history: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_active": self.conversation_active,
            "last_application": self.last_application,
            "current_url": self.current_url,
            "current_site": self.current_site,
            "last_action": self.last_action,
            "last_search": self.last_search,
            "last_task_status": self.last_task_status,
            "turn_count": self.turn_count,
        }

    def update(self, **kwargs) -> None:
        """Update allowed fields only — never store sensitive data."""
        blocked = {"password", "token", "api_key", "credit", "bank", "credential"}
        for k, v in kwargs.items():
            lk = k.lower()
            if any(b in lk for b in blocked):
                logger.warning("Blocked sensitive context key: %s", k)
                continue
            if hasattr(self, k):
                setattr(self, k, v)
                logger.debug("[CONTEXT] %s=%r", k, v)

    def clear(self) -> None:
        logger.info("[RESET] Clearing conversation context")
        self.conversation_active = False
        self.last_application = None
        self.current_url = None
        self.current_site = None
        self.last_action = None
        self.last_search = None
        self.last_task_status = None
        self.turn_count = 0
        self.last_user_text = None
        self.last_assistant_response = None
        self.history.clear()

    def add_turn(self, user_text: str, assistant_response: str) -> None:
        # Truncate to avoid memory bloat
        ut = user_text.strip()[:300] if user_text else ""
        ar = assistant_response.strip()[:300] if assistant_response else ""
        self.last_user_text = ut
        self.last_assistant_response = ar
        self.history.append({"user": ut, "assistant": ar, "ts": str(time.time())})
        # Keep only last 10 turns
        if len(self.history) > 10:
            self.history = self.history[-10:]
