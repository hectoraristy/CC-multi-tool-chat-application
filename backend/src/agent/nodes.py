from __future__ import annotations

import logging
import uuid

from agent.state import AgentState
from api.dependencies import get_s3_store, get_store
from config import get_settings
from langchain_core.messages import BaseMessage, ToolMessage
from storage.models import ToolResult
from storage.s3 import S3ResultStore

logger = logging.getLogger(__name__)


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
    full_content = last_tool_msg.content

    s3_key: str | None = None
    stored_full_result = full_content

    s3 = get_s3_store()
    if s3 is not None:
        s3_key = S3ResultStore.make_key(session_id, result_id)
        s3.upload_result(s3_key, full_content)
        stored_full_result = ""
        logger.info("Uploaded large tool result %s to S3 key %s", result_id, s3_key)

    store = get_store()
    store.store_tool_result(
        ToolResult(
            session_id=session_id,
            result_id=result_id,
            tool_name=last_tool_msg.name or "unknown",
            summary=full_content[:500],
            full_result=stored_full_result,
            s3_key=s3_key,
            size_bytes=len(full_content.encode("utf-8")),
            metadata={"auto_stored": True, "source": "summarize_node"},
        )
    )
    logger.info("Auto-stored large tool result %s before summarization", result_id)

    llm = create_llm()
    from langchain_core.messages import HumanMessage, SystemMessage

    summary_resp = llm.invoke(
        [
            SystemMessage(content=SUMMARIZE_SYSTEM_PROMPT),
            HumanMessage(content=full_content),
        ]
    )

    summarized = ToolMessage(
        content=(f"[Summarized — full result stored as {result_id}] " f"{summary_resp.content}"),
        tool_call_id=last_tool_msg.tool_call_id,
        name=last_tool_msg.name,
        id=last_tool_msg.id,
    )

    return {"messages": [summarized]}
