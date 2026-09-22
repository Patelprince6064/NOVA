"""Conversation Manager for Nova Phase 9 — lightweight state + timeout + context.

API:
  start()
  is_active()
  add_turn(user_text, assistant_response)
  get_context()
  update_context(...)
  reset()
  should_timeout()
  increment_turn()

In-memory only. No sensitive data.
"""

import time
import logging
import threading
from typing import Dict, Any, Optional

from app.conversation.state import ConversationState
from app.conversation.context import ConversationContext

logger = logging.getLogger(__name__)


class ConversationManager:
    def __init__(
        self,
        enabled: bool = True,
        conversation_timeout: int = 8,
        follow_up_timeout: int = 6,
        max_turns: int = 10,
        context_enabled: bool = True,
        post_tts_cooldown_ms: int = 300,
    ):
        self.enabled = enabled
        self.conversation_timeout = max(1, int(conversation_timeout))
        self.follow_up_timeout = max(1, int(follow_up_timeout))
        self.max_turns = max(1, int(max_turns))
        self.context_enabled = context_enabled
        self.post_tts_cooldown_ms = max(0, int(post_tts_cooldown_ms))

        self.state: ConversationState = ConversationState.IDLE
        self.context = ConversationContext()
        self._start_time: Optional[float] = None
        self._last_activity: Optional[float] = None
        self._turn_count: int = 0
        self._lock = threading.Lock()

        logger.info(
            "[CONTEXT] ConversationManager init enabled=%s timeout=%ds follow_up=%ds max_turns=%d context=%s cooldown=%dms",
            enabled, self.conversation_timeout, self.follow_up_timeout, self.max_turns, context_enabled, self.post_tts_cooldown_ms,
        )

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Begin a new conversation (after wake word)."""
        if not self.enabled:
            logger.debug("[CONTEXT] start() called but conversation disabled")
            return
        with self._lock:
            self.context.conversation_active = True
            self.context.turn_count = 0
            self._turn_count = 0
            self._start_time = time.time()
            self._last_activity = time.time()
            self.state = ConversationState.CONVERSATION_ACTIVE
            logger.info("[CONTEXT] Conversation active")

    def is_active(self) -> bool:
        if not self.enabled or not self.context_enabled:
            return False
        with self._lock:
            if not self.context.conversation_active:
                return False
            if self.should_timeout_locked():
                return False
            if self._turn_count >= self.max_turns:
                return False
            return True

    def add_turn(self, user_text: str, assistant_response: str) -> None:
        with self._lock:
            self.context.add_turn(user_text, assistant_response)
            self._last_activity = time.time()
            logger.debug("[CONTEXT] Turn added: %r -> %r", user_text[:60], assistant_response[:60])

    def get_context(self) -> Dict[str, Any]:
        with self._lock:
            d = self.context.to_dict()
            # Also include turn count from manager
            d["turn_count"] = self._turn_count
            return dict(d)

    def update_context(self, **kwargs) -> None:
        if not self.context_enabled:
            return
        with self._lock:
            self.context.update(**kwargs)
            self._last_activity = time.time()

    def reset(self) -> None:
        with self._lock:
            logger.info("[RESET] Conversation reset (turns=%d state=%s)", self._turn_count, self.state)
            self.context.clear()
            self._turn_count = 0
            self._start_time = None
            self._last_activity = None
            self.state = ConversationState.IDLE

    def should_timeout(self) -> bool:
        with self._lock:
            return self.should_timeout_locked()

    def should_timeout_locked(self) -> bool:
        if not self.context.conversation_active:
            return False
        if self._last_activity is None:
            return False
        elapsed = time.time() - self._last_activity
        # Use conversation_timeout as primary; follow_up also considered
        timeout = self.conversation_timeout
        if elapsed > timeout:
            logger.info("[TIMEOUT] Conversation timeout after %.1fs > %ds", elapsed, timeout)
            return True
        return False

    def increment_turn(self) -> int:
        with self._lock:
            self._turn_count += 1
            self.context.turn_count = self._turn_count
            self._last_activity = time.time()
            logger.debug("[CONTEXT] Turn %d/%d", self._turn_count, self.max_turns)
            return self._turn_count

    def check_turn_limit(self) -> bool:
        """Return True if turn limit reached."""
        with self._lock:
            return self._turn_count >= self.max_turns

    def touch(self) -> None:
        with self._lock:
            self._last_activity = time.time()

    def set_state(self, state: ConversationState) -> None:
        with self._lock:
            self.state = state
            logger.debug("[CONTEXT] State -> %s", state)

    def get_state(self) -> ConversationState:
        with self._lock:
            return self.state

    def handle_timeout_if_needed(self) -> bool:
        """Check timeout and reset if needed. Returns True if reset occurred."""
        if self.should_timeout():
            logger.info("[TIMEOUT] Resetting conversation due to timeout")
            self.reset()
            return True
        return False
