from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from constants import RESULT_ID_RE
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from services.persistence import (
    flush_pending_tool_msgs,
    persist_assistant_message,
    persist_tool_call,
)
from storage.protocols import Store

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

logger = logging.getLogger(__name__)


def _extract_result_id(content: str) -> str | None:
    """Return the result_id embedded in a ToolMessage, or None."""
    m = RESULT_ID_RE.search(content)
    return m.group(1) if m else None


async def stream_agent_events(
    graph: CompiledStateGraph,
    store: Store,
    session_id: str,
    lc_messages: list[BaseMessage],
) -> AsyncIterator[dict[str, str]]:
    """Run the agent graph and yield SSE-ready dicts."""
    state = {"messages": lc_messages, "session_id": session_id}
    full_response = ""
    pending_tool_msgs: dict[str, ToolMessage] = {}

    try:
        for event in graph.stream(state, stream_mode="updates"):
            for _node_name, node_output in event.items():
                msgs = node_output.get("messages", [])
                for msg in msgs:
                    if isinstance(msg, AIMessage):
                        flush_pending_tool_msgs(store, session_id, pending_tool_msgs)
                        if msg.tool_calls:
                            for tc in msg.tool_calls:
                                persist_tool_call(store, session_id, tc)
                                if tc["name"] == "session_manager":
                                    continue
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
                        tc_id = getattr(msg, "tool_call_id", "") or ""
                        pending_tool_msgs[tc_id] = msg
                        tool_name = msg.name or "unknown"
                        if tool_name == "session_manager":
                            continue
                        summary = msg.content[:500] if msg.content else ""
                        event_data: dict[str, str] = {
                            "tool": tool_name,
                            "result_preview": summary,
                        }
                        rid = _extract_result_id(msg.content)
                        if rid:
                            event_data["result_id"] = rid
                        yield {
                            "event": "tool_result",
                            "data": json.dumps(event_data),
                        }
    except Exception as exc:
        logger.exception("Agent error")
        flush_pending_tool_msgs(store, session_id, pending_tool_msgs)
        yield {"event": "error", "data": str(exc)}
        return

    flush_pending_tool_msgs(store, session_id, pending_tool_msgs)

    if full_response:
        persist_assistant_message(store, session_id, full_response)

    yield {"event": "done", "data": ""}
