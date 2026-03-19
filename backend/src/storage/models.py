from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ToolResult(BaseModel):
    session_id: str
    result_id: str
    tool_name: str
    summary: str
    full_result: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utc_now)
    size_bytes: int = 0

    def model_post_init(self, __context: Any) -> None:
        if self.size_bytes == 0:
            self.size_bytes = len(self.full_result.encode("utf-8"))


class ToolResultMetadata(BaseModel):
    """Lightweight view returned when listing stored results (no full_result)."""

    session_id: str
    result_id: str
    tool_name: str
    summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    size_bytes: int


class Session(BaseModel):
    session_id: str
    title: str = "New Chat"
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class ChatMessage(BaseModel):
    session_id: str
    message_id: str
    role: str  # "user" | "assistant" | "tool"
    content: str
    tool_name: str | None = None
    tool_call_id: str | None = None
    created_at: datetime = Field(default_factory=_utc_now)
