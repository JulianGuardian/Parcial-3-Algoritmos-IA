"""In-memory conversations for the agent API (task 4.1, design D6).

A conversation pairs an ADK session (which holds the booking id and the
turn-by-turn state the tools read) with the `ToolDeps` write tools, so
idempotency and call history are shared across turns of the same
conversation. Nothing is persisted: restarting the process drops every
conversation, which matches the exam's "no persistent sessions" non-goal.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field

from google.adk.sessions import InMemorySessionService

from app.disruption.actions.write_tools import MockWriteTools
from app.disruption.agents.contracts import STATE_BOOKING_ID
from app.disruption.agents.disruption_tools import ToolDeps

APP_NAME = "nubara-disruption-agent"


@dataclass
class Conversation:
    conversation_id: str
    booking_id: str
    deps: ToolDeps = field(default_factory=lambda: ToolDeps(write_tools=MockWriteTools()))


class ConversationStore:
    """Process-wide, in-memory. One `InMemorySessionService` for every
    conversation; `conversation_id` doubles as both the ADK user id and
    session id, since each conversation has exactly one participant."""

    def __init__(self) -> None:
        self.session_service = InMemorySessionService()
        self._conversations: dict[str, Conversation] = {}

    def create(self, booking_id: str) -> Conversation:
        conversation_id = uuid.uuid4().hex
        asyncio.run(
            self.session_service.create_session(
                app_name=APP_NAME,
                user_id=conversation_id,
                session_id=conversation_id,
                state={STATE_BOOKING_ID: booking_id},
            )
        )
        conversation = Conversation(conversation_id=conversation_id, booking_id=booking_id)
        self._conversations[conversation_id] = conversation
        return conversation

    def get(self, conversation_id: str) -> Conversation | None:
        return self._conversations.get(conversation_id)


_store: ConversationStore | None = None


def get_conversation_store() -> ConversationStore:
    """Process-wide singleton, overridable in tests via `set_conversation_store`."""
    global _store
    if _store is None:
        _store = ConversationStore()
    return _store


def set_conversation_store(store: ConversationStore | None) -> None:
    global _store
    _store = store
