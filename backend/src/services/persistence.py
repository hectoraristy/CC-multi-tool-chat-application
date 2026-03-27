from __future__ import annotations

import json
import uuid
from typing import Any

from exceptions import NotFoundError
from langchain_core.messages import ToolMessage
from storage.models import ChatMessage
from storage.protocols import MessageRepository, SessionRepository, Store


def persist_user_message(
    store: MessageRepository,
    session_id: str,
    content: str,
) -> None:
    store.store_message(
        ChatMessage(
            session_id=session_id,
            message_id=str(uuid.uuid4()),
            role="user",
            content=content,
        )
    )


def persist_assistant_message(
    store: Store,
    session_id: str,
    content: str,
) -> None:
    store.store_message(
        ChatMessage(
            session_id=session_id,
            message_id=str(uuid.uuid4()),
            role="assistant",
            content=content,
        )
    )
    store.update_session_timestamp(session_id)


def persist_tool_call(
    store: MessageRepository,
    session_id: str,
    tool_call: dict[str, Any],
) -> None:
    store.store_message(
        ChatMessage(
            session_id=session_id,
            message_id=str(uuid.uuid4()),
            role="tool_call",
            content=json.dumps(tool_call["args"]),
            tool_name=tool_call["name"],
            tool_call_id=tool_call["id"],
        )
    )


def persist_tool_message(
    store: MessageRepository,
    session_id: str,
    msg: ToolMessage,
) -> None:
    store.store_message(
        ChatMessage(
            session_id=session_id,
            message_id=str(uuid.uuid4()),
            role="tool",
            content=msg.content or "",
            tool_name=msg.name or "unknown",
            tool_call_id=getattr(msg, "tool_call_id", "") or "",
        )
    )


def flush_pending_tool_msgs(
    store: MessageRepository,
    session_id: str,
    pending: dict[str, ToolMessage],
) -> None:
    for tm in pending.values():
        persist_tool_message(store, session_id, tm)
    pending.clear()


def validate_session_exists(
    store: SessionRepository,
    session_id: str,
) -> None:
    if store.get_session(session_id) is None:
        raise NotFoundError("Session", session_id)
