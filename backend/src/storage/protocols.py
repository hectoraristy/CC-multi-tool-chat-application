from __future__ import annotations

from typing import Protocol

from storage.models import (
    ChatMessage,
    PaginatedResult,
    Session,
    ToolResult,
    ToolResultMetadata,
    UserFact,
)


class SessionRepository(Protocol):
    def create_session(self, title: str = "New Chat") -> Session:
        ...

    def get_session(self, session_id: str) -> Session | None:
        ...

    def list_sessions(
        self,
        limit: int = 20,
        cursor: str | None = None,
    ) -> PaginatedResult[Session]:
        ...

    def update_session_title(self, session_id: str, title: str) -> Session | None:
        ...

    def update_session_timestamp(self, session_id: str) -> None:
        ...

    def delete_session(self, session_id: str) -> bool:
        ...


class MessageRepository(Protocol):
    def store_message(self, message: ChatMessage) -> None:
        ...

    def get_messages(self, session_id: str) -> list[ChatMessage]:
        ...


class ToolResultRepository(Protocol):
    def store_tool_result(self, result: ToolResult) -> None:
        ...

    def get_tool_result(self, session_id: str, result_id: str) -> ToolResult | None:
        ...

    def list_tool_results(self, session_id: str) -> list[ToolResultMetadata]:
        ...


class UserFactRepository(Protocol):
    def store_user_fact(self, fact: UserFact) -> None:
        ...

    def get_user_facts(self, user_id: str) -> list[UserFact]:
        ...


class Store(
    SessionRepository,
    MessageRepository,
    ToolResultRepository,
    UserFactRepository,
    Protocol,
):
    """Combined protocol for implementations that satisfy all repositories."""

    ...
