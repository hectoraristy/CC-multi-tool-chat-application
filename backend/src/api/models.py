from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FileAttachment(BaseModel):
    s3_uri: str
    filename: str
    file_type: str


class FileUploadResponse(BaseModel):
    s3_uri: str
    filename: str
    file_type: str
    size_bytes: int


class ChatRequest(BaseModel):
    session_id: str = Field(
        ..., pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )
    message: str = Field(..., min_length=1)
    attachments: list[FileAttachment] | None = None


class ChatEvent(BaseModel):
    """Individual SSE event sent during streaming."""

    event: str  # "token" | "tool_call" | "tool_result" | "done" | "error"
    data: str


class SessionCreate(BaseModel):
    title: str = "New Chat"


class SessionUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class SessionResponse(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    message_id: str
    role: str
    content: str
    tool_name: str | None = None
    tool_call_id: str | None = None
    tool_args: dict[str, Any] | None = None
    result_id: str | None = None
    created_at: datetime


class ToolResultResponse(BaseModel):
    result_id: str
    tool_name: str
    summary: str
    metadata: dict[str, Any]
    size_bytes: int
    has_full_result: bool = False
    created_at: datetime


class PaginatedSessionsResponse(BaseModel):
    items: list[SessionResponse]
    next_cursor: str | None = None


class DownloadUrlResponse(BaseModel):
    download_url: str
