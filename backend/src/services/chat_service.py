from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from config import get_settings
from constants import RESULT_ID_RE
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
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
    *,
    stored_result_ids: list[str] | None = None,
    tools_used_this_session: list[str] | None = None,
    turn_count: int = 0,
    user_facts: list[str] | None = None,
) -> AsyncIterator[dict[str, str]]:
    """Run the agent graph and yield SSE-ready dicts."""
    state: dict[str, object] = {
        "messages": lc_messages,
        "session_id": session_id,
        "stored_result_ids": stored_result_ids or [],
        "tools_used_this_session": tools_used_this_session or [],
        "turn_count": turn_count,
        "user_facts": user_facts or [],
    }
    full_response = ""
    pending_tool_msgs: dict[str, ToolMessage] = {}

    try:
        for event in graph.stream(state, stream_mode="updates"):
            for _node_name, node_output in event.items():
                if not node_output:
                    continue
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

        # Extract durable user facts from this turn (fire-and-forget)
        try:
            last_user_content = ""
            for msg in reversed(lc_messages):
                if isinstance(msg, HumanMessage):
                    last_user_content = msg.content if isinstance(msg.content, str) else str(msg.content)
                    break

            if last_user_content:
                from agent.llm_factory import create_llm
                from services.memory import extract_and_store_facts

                settings = get_settings()
                extract_and_store_facts(
                    llm=create_llm(),
                    store=store,
                    user_id=settings.user_id,
                    session_id=session_id,
                    user_message=last_user_content,
                    assistant_message=full_response,
                )
        except Exception:
            logger.debug("Fact extraction failed (non-critical)", exc_info=True)

    yield {"event": "done", "data": ""}
