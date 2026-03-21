from __future__ import annotations

from api.dependencies import get_store
from api.models import (
    DownloadUrlResponse,
    MessageResponse,
    PaginatedSessionsResponse,
    SessionCreate,
    SessionResponse,
    SessionUpdate,
    ToolResultResponse,
)
from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from services import session_service
from storage.protocols import Store

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse)
def create_session(
    body: SessionCreate,
    store: Store = Depends(get_store),
) -> SessionResponse:
    return session_service.create_session(store, title=body.title)


@router.get("", response_model=PaginatedSessionsResponse)
def list_sessions(
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
    store: Store = Depends(get_store),
) -> PaginatedSessionsResponse:
    return session_service.list_sessions(store, limit=limit, cursor=cursor)


@router.patch("/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: str,
    body: SessionUpdate,
    store: Store = Depends(get_store),
) -> SessionResponse:
    return session_service.update_session(store, session_id, body.title)


@router.delete("/{session_id}", status_code=204)
def delete_session(
    session_id: str,
    store: Store = Depends(get_store),
) -> None:
    session_service.delete_session(store, session_id)


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
def get_messages(
    session_id: str,
    store: Store = Depends(get_store),
) -> list[MessageResponse]:
    return session_service.get_messages(store, session_id)


@router.get("/{session_id}/tool-results", response_model=list[ToolResultResponse])
def get_tool_results(
    session_id: str,
    store: Store = Depends(get_store),
) -> list[ToolResultResponse]:
    return session_service.get_tool_results(store, session_id)


@router.get("/{session_id}/tool-results/{result_id}/download", response_model=None)
def download_tool_result(
    session_id: str,
    result_id: str,
    store: Store = Depends(get_store),
) -> DownloadUrlResponse | PlainTextResponse:
    download = session_service.get_download_result(store, session_id, result_id)
    if download.url:
        return DownloadUrlResponse(download_url=download.url)
    return PlainTextResponse(content=download.content or "")
