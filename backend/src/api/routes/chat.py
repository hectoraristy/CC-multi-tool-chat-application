from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, HTTPException
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from sse_starlette.sse import EventSourceResponse

from agent.graph import build_graph
from api.models import ChatRequest
from storage.dynamo import DynamoDBStore
from storage.models import ChatMessage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

_store: DynamoDBStore | None = None
_graph = None


def _get_store() -> DynamoDBStore:
    global _store
    if _store is None:
        _store = DynamoDBStore()
        _store.create_table_if_not_exists()
    return _store


def _get_graph():  # noqa: ANN202
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


@router.post("/chat")
async def chat(body: ChatRequest) -> EventSourceResponse:
    store = _get_store()
    session = store.get_session(body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    store.store_message(
        ChatMessage(
            session_id=body.session_id,
            message_id=str(uuid.uuid4()),
            role="user",
            content=body.message,
        )
    )

    stored_messages = store.get_messages(body.session_id)
    lc_messages = []
    for m in stored_messages:
        if m.role == "tool_call":
            continue
        elif m.role == "user":
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

    async def event_generator():  # noqa: ANN202
        graph = _get_graph()
        state = {"messages": lc_messages, "session_id": body.session_id}

        full_response = ""
        try:
            for event in graph.stream(state, stream_mode="updates"):
                for node_name, node_output in event.items():
                    msgs = node_output.get("messages", [])
                    for msg in msgs:
                        if isinstance(msg, AIMessage):
                            if msg.tool_calls:
                                for tc in msg.tool_calls:
                                    store.store_message(
                                        ChatMessage(
                                            session_id=body.session_id,
                                            message_id=str(uuid.uuid4()),
                                            role="tool_call",
                                            content=json.dumps(tc["args"]),
                                            tool_name=tc["name"],
                                            tool_call_id=tc["id"],
                                        )
                                    )
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
                                yield {
                                    "event": "token",
                                    "data": msg.content,
                                }
                        elif isinstance(msg, ToolMessage):
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
            store.store_message(
                ChatMessage(
                    session_id=body.session_id,
                    message_id=str(uuid.uuid4()),
                    role="assistant",
                    content=full_response,
                )
            )
            store.update_session_timestamp(body.session_id)

        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())
