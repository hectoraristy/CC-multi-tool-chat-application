from __future__ import annotations

import logging
import uuid

from agent.state import AgentState
from config import get_settings
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from storage.dynamo import DynamoDBStore
from storage.models import ToolResult
from storage.protocols import Store

logger = logging.getLogger(__name__)

_store: Store | None = None


def _get_store() -> Store:
    global _store
    if _store is None:
        _store = DynamoDBStore()
    return _store


def set_store(store: Store) -> None:
    global _store
    _store = store


SUMMARIZE_SYSTEM_PROMPT = (
    "You are a summarization assistant. Condense the following tool output "
    "into a concise summary that preserves the key information. "
    "Keep it under 1000 tokens."
)


def should_summarize(state: AgentState) -> str:
    messages = state["messages"]
    if not messages:
        return "agent"

    last = messages[-1]
    if not isinstance(last, ToolMessage):
        return "agent"

    threshold = get_settings().summarize_token_threshold
    approx_tokens = len(last.content) // 4
    if approx_tokens > threshold:
        logger.info(
            "Tool result ~%d tokens exceeds threshold %d, routing to summarizer",
            approx_tokens,
            threshold,
        )
        return "summarize"

    return "agent"


def summarize_node(state: AgentState) -> dict[str, list[BaseMessage]]:
    from agent.llm_factory import create_llm

    messages = state["messages"]
    last_tool_msg = messages[-1]
    assert isinstance(last_tool_msg, ToolMessage)

    session_id = state.get("session_id", "unknown")
    result_id = str(uuid.uuid4())

    store = _get_store()
    store.store_tool_result(
        ToolResult(
            session_id=session_id,
            result_id=result_id,
            tool_name=last_tool_msg.name or "unknown",
            summary=last_tool_msg.content[:500],
            full_result=last_tool_msg.content,
            metadata={"auto_stored": True, "source": "summarize_node"},
        )
    )
    logger.info("Auto-stored large tool result %s before summarization", result_id)

    llm = create_llm()
    from langchain_core.messages import HumanMessage, SystemMessage

    summary_resp = llm.invoke(
        [
            SystemMessage(content=SUMMARIZE_SYSTEM_PROMPT),
            HumanMessage(content=last_tool_msg.content),
        ]
    )

    summarized = ToolMessage(
        content=(f"[Summarized — full result stored as {result_id}] " f"{summary_resp.content}"),
        tool_call_id=last_tool_msg.tool_call_id,
        name=last_tool_msg.name,
    )

    return {"messages": [summarized]}
