"""Business logic for session management.

Wraps storage operations and raises domain exceptions, keeping
route handlers free of persistence details.
"""

from __future__ import annotations

import json

from api.models import (
    MessageResponse,
    SessionResponse,
    ToolResultResponse,
)
from exceptions import NotFoundError
from storage.models import ChatMessage, Session, ToolResultMetadata
from storage.protocols import SessionRepository, Store


def _to_session_response(session: Session) -> SessionResponse:
    return SessionResponse(
        session_id=session.session_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def create_session(
    store: SessionRepository,
    title: str = "New Chat",
) -> SessionResponse:
    session = store.create_session(title=title)
    return _to_session_response(session)


def list_sessions(store: SessionRepository) -> list[SessionResponse]:
    return [_to_session_response(s) for s in store.list_sessions()]


def update_session(
    store: SessionRepository,
    session_id: str,
    title: str,
) -> SessionResponse:
    session = store.update_session_title(session_id, title)
    if session is None:
        raise NotFoundError("Session", session_id)
    return _to_session_response(session)


def delete_session(store: SessionRepository, session_id: str) -> None:
    if not store.delete_session(session_id):
        raise NotFoundError("Session", session_id)


def get_messages(
    store: Store,
    session_id: str,
) -> list[MessageResponse]:
    if store.get_session(session_id) is None:
        raise NotFoundError("Session", session_id)

    messages: list[ChatMessage] = store.get_messages(session_id)
    results: list[MessageResponse] = []
    for m in messages:
        tool_args = None
        if m.role == "tool_call":
            try:
                tool_args = json.loads(m.content)
            except (json.JSONDecodeError, TypeError):
                pass
        results.append(
            MessageResponse(
                message_id=m.message_id,
                role=m.role,
                content=m.content,
                tool_name=m.tool_name,
                tool_call_id=m.tool_call_id,
                tool_args=tool_args,
                created_at=m.created_at,
            )
        )
    return results


def get_tool_results(
    store: Store,
    session_id: str,
) -> list[ToolResultResponse]:
    if store.get_session(session_id) is None:
        raise NotFoundError("Session", session_id)

    results: list[ToolResultMetadata] = store.list_tool_results(session_id)
    return [
        ToolResultResponse(
            result_id=r.result_id,
            tool_name=r.tool_name,
            summary=r.summary,
            metadata=r.metadata,
            size_bytes=r.size_bytes,
            created_at=r.created_at,
        )
        for r in results
    ]
