from __future__ import annotations

import json
from dataclasses import dataclass

from api.models import (
    MessageResponse,
    PaginatedSessionsResponse,
    SessionResponse,
    ToolResultResponse,
)
from constants import HIDDEN_TOOLS, RESULT_ID_RE
from exceptions import NotFoundError
from storage.models import ChatMessage, Session, ToolResult, ToolResultMetadata
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


def list_sessions(
    store: SessionRepository,
    limit: int = 20,
    cursor: str | None = None,
) -> PaginatedSessionsResponse:
    result = store.list_sessions(limit=limit, cursor=cursor)
    return PaginatedSessionsResponse(
        items=[_to_session_response(s) for s in result.items],
        next_cursor=result.next_cursor,
    )


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

    # Build a map of tool_call_id -> result_id from tool result messages
    tool_call_result_ids: dict[str, str] = {}
    for m in messages:
        if m.role == "tool" and m.tool_call_id and m.content:
            match = RESULT_ID_RE.search(m.content)
            if match:
                tool_call_result_ids[m.tool_call_id] = match.group(1)

    results: list[MessageResponse] = []
    for m in messages:
        if m.role == "tool":
            continue
        if m.role == "tool_call" and m.tool_name in HIDDEN_TOOLS:
            continue

        tool_args = None
        result_id = None
        if m.role == "tool_call":
            try:
                tool_args = json.loads(m.content)
            except (json.JSONDecodeError, TypeError):
                pass
            result_id = tool_call_result_ids.get(m.tool_call_id or "")

        results.append(
            MessageResponse(
                message_id=m.message_id,
                role=m.role,
                content=m.content,
                tool_name=m.tool_name,
                tool_call_id=m.tool_call_id,
                tool_args=tool_args,
                result_id=result_id,
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
            has_full_result=bool(r.s3_key),
            created_at=r.created_at,
        )
        for r in results
    ]


@dataclass(frozen=True)
class DownloadContent:
    url: str | None = None
    content: str | None = None


def get_download_result(
    store: Store,
    session_id: str,
    result_id: str,
) -> DownloadContent:
    result: ToolResult | None = store.get_tool_result(session_id, result_id)
    if result is None:
        raise NotFoundError("ToolResult", result_id)

    if result.s3_key:
        from api.dependencies import get_s3_store

        s3 = get_s3_store()
        if s3 is not None:
            return DownloadContent(url=s3.generate_presigned_url(result.s3_key))

    if result.full_result:
        return DownloadContent(content=result.full_result)

    raise NotFoundError("ToolResult content", result_id)
