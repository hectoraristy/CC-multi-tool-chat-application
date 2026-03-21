from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from exceptions import NotFoundError
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from storage.models import ChatMessage
from storage.protocols import MessageRepository, SessionRepository, Store

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

logger = logging.getLogger(__name__)


def build_langchain_messages(
    stored_messages: list[ChatMessage],
) -> list[BaseMessage]:
    """Convert persisted ``ChatMessage`` rows into LangChain message objects.

    Consecutive ``tool_call`` rows are merged into a single ``AIMessage``
    with ``tool_calls``, matching the structure LangGraph expects.
    """
    lc_messages: list[BaseMessage] = []
    pending_tool_calls: list[dict[str, Any]] = []

    def _flush_tool_calls() -> None:
        if not pending_tool_calls:
            return
        lc_messages.append(
            AIMessage(content="", tool_calls=list(pending_tool_calls))
        )
        pending_tool_calls.clear()

    for m in stored_messages:
        if m.role == "tool_call":
            pending_tool_calls.append(
                {
                    "name": m.tool_name or "unknown",
                    "args": json.loads(m.content) if m.content else {},
                    "id": m.tool_call_id or "",
                }
            )
        else:
            _flush_tool_calls()
            if m.role == "user":
                lc_messages.append(HumanMessage(content=m.content))
            elif m.role == "assistant":
                lc_messages.append(AIMessage(content=m.content))
            elif m.role == "tool":
                lc_messages.append(
                    ToolMessage(
                        content=m.content,
                        tool_call_id=m.tool_call_id or "",
                        name=m.tool_name or "unknown",
                    )
                )

    _flush_tool_calls()
    return lc_messages


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


def validate_session_exists(
    store: SessionRepository,
    session_id: str,
) -> None:
    """Raise ``NotFoundError`` if the session does not exist."""
    if store.get_session(session_id) is None:
        raise NotFoundError("Session", session_id)


async def stream_agent_events(
    graph: CompiledStateGraph,
    store: Store,
    session_id: str,
    lc_messages: list[BaseMessage],
) -> AsyncIterator[dict[str, str]]:
    """Run the agent graph and yield SSE-ready dicts."""
    state = {"messages": lc_messages, "session_id": session_id}
    full_response = ""

    try:
        for event in graph.stream(state, stream_mode="updates"):
            for _node_name, node_output in event.items():
                msgs = node_output.get("messages", [])
                for msg in msgs:
                    if isinstance(msg, AIMessage):
                        if msg.tool_calls:
                            for tc in msg.tool_calls:
                                persist_tool_call(store, session_id, tc)
                                yield {
                                    "event": "tool_call",
                                    "data": json.dumps(
                                        {
                                            "tool": tc["name"],
                                            "args": tc["args"],
                                            "id": tc["id"],
                                        }
                                    ),
                                }
                        elif msg.content:
                            full_response += msg.content
                            yield {"event": "token", "data": msg.content}

                    elif isinstance(msg, ToolMessage):
                        persist_tool_message(store, session_id, msg)
                        summary = msg.content[:500] if msg.content else ""
                        yield {
                            "event": "tool_result",
                            "data": json.dumps(
                                {
                                    "tool": msg.name or "unknown",
                                    "result_preview": summary,
                                }
                            ),
                        }
    except Exception as exc:
        logger.exception("Agent error")
        yield {"event": "error", "data": str(exc)}
        return

    if full_response:
        persist_assistant_message(store, session_id, full_response)

    yield {"event": "done", "data": ""}
