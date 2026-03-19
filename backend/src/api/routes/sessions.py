from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.models import (
    MessageResponse,
    SessionCreate,
    SessionResponse,
    SessionUpdate,
    ToolResultResponse,
)
from storage.dynamo import DynamoDBStore

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

_store: DynamoDBStore | None = None


def _get_store() -> DynamoDBStore:
    global _store
    if _store is None:
        _store = DynamoDBStore()
        _store.create_table_if_not_exists()
    return _store


@router.post("", response_model=SessionResponse)
def create_session(body: SessionCreate) -> SessionResponse:
    session = _get_store().create_session(title=body.title)
    return SessionResponse(
        session_id=session.session_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("", response_model=list[SessionResponse])
def list_sessions() -> list[SessionResponse]:
    sessions = _get_store().list_sessions()
    return [
        SessionResponse(
            session_id=s.session_id,
            title=s.title,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sessions
    ]


@router.patch("/{session_id}", response_model=SessionResponse)
def update_session(session_id: str, body: SessionUpdate) -> SessionResponse:
    session = _get_store().update_session_title(session_id, body.title)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(
        session_id=session.session_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
def get_messages(session_id: str) -> list[MessageResponse]:
    session = _get_store().get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = _get_store().get_messages(session_id)
    return [
        MessageResponse(
            message_id=m.message_id,
            role=m.role,
            content=m.content,
            tool_name=m.tool_name,
            tool_call_id=m.tool_call_id,
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.get("/{session_id}/tool-results", response_model=list[ToolResultResponse])
def get_tool_results(session_id: str) -> list[ToolResultResponse]:
    session = _get_store().get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    results = _get_store().list_tool_results(session_id)
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
