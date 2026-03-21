from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from storage.models import ChatMessage


def build_langchain_messages(
    stored_messages: list[ChatMessage],
) -> list[BaseMessage]:
    """Convert persisted ``ChatMessage`` rows into LangChain message objects.

    Consecutive ``tool_call`` rows are merged into a single ``AIMessage``
    with ``tool_calls``, matching the structure LangGraph expects.

    When multiple ``tool`` rows share the same ``tool_call_id`` (e.g. a raw
    result followed by a summarized replacement), only the last one is kept
    so the resulting sequence satisfies the OpenAI constraint of one
    ``ToolMessage`` per ``tool_call``.
    """
    deduped: list[ChatMessage] = []
    seen_tool_ids: dict[str, int] = {}

    for m in stored_messages:
        if m.role == "tool" and m.tool_call_id:
            prev_idx = seen_tool_ids.get(m.tool_call_id)
            if prev_idx is not None:
                deduped[prev_idx] = m
                continue
            seen_tool_ids[m.tool_call_id] = len(deduped)
        deduped.append(m)

    lc_messages: list[BaseMessage] = []
    pending_tool_calls: list[dict[str, Any]] = []

    def _flush_tool_calls() -> None:
        if not pending_tool_calls:
            return
        lc_messages.append(AIMessage(content="", tool_calls=list(pending_tool_calls)))
        pending_tool_calls.clear()

    for m in deduped:
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
