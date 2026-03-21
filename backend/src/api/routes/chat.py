from __future__ import annotations

from typing import TYPE_CHECKING

from api.dependencies import get_graph, get_store
from api.models import ChatRequest
from fastapi import APIRouter, Depends
from services import chat_service
from sse_starlette.sse import EventSourceResponse
from storage.protocols import Store

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
async def chat(
    body: ChatRequest,
    store: Store = Depends(get_store),
    graph: CompiledStateGraph = Depends(get_graph),
) -> EventSourceResponse:
    chat_service.validate_session_exists(store, body.session_id)
    chat_service.persist_user_message(store, body.session_id, body.message)

    stored_messages = store.get_messages(body.session_id)
    lc_messages = chat_service.build_langchain_messages(stored_messages)

    return EventSourceResponse(
        chat_service.stream_agent_events(graph, store, body.session_id, lc_messages)
    )
