from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ToolResult(BaseModel):
    session_id: str
    result_id: str
    tool_name: str
    summary: str
    full_result: str = ""
    s3_key: str | None = None
    s3_chunk_prefix: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utc_now)
    size_bytes: int = 0
    total_chunks: int = 0
    chunk_size_chars: int = 0

    def model_post_init(self, __context: Any) -> None:
        if self.size_bytes == 0 and self.full_result:
            self.size_bytes = len(self.full_result.encode("utf-8"))


class ToolResultMetadata(BaseModel):
    """Lightweight view returned when listing stored results (no full_result)."""

    session_id: str
    result_id: str
    tool_name: str
    summary: str
    s3_key: str | None = None
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


@dataclass
class PaginatedResult(Generic[T]):
    items: list[T] = field(default_factory=list)
    next_cursor: str | None = None
