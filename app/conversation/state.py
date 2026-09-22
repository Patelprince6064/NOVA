"""Conversation states for Nova Phase 9.

Lightweight state machine: IDLE -> WAKE_DETECTED -> LISTENING -> PROCESSING -> EXECUTING -> SPEAKING -> CONVERSATION_ACTIVE -> LISTENING -> ... -> timeout -> IDLE
"""

from enum import Enum, auto


class ConversationState(Enum):
    IDLE = auto()
    WAKE_DETECTED = auto()
    LISTENING = auto()
    PROCESSING = auto()
    EXECUTING = auto()
    SPEAKING = auto()
    CONVERSATION_ACTIVE = auto()

    def __str__(self) -> str:
        return self.name
