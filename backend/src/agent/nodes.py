from __future__ import annotations

import logging

from agent.state import AgentState
from config import get_settings
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

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

    llm = create_llm()
    from langchain_core.messages import HumanMessage, SystemMessage

    summary_resp = llm.invoke(
        [
            SystemMessage(content=SUMMARIZE_SYSTEM_PROMPT),
            HumanMessage(content=last_tool_msg.content),
        ]
    )

    summarized = ToolMessage(
        content=f"[Summarized] {summary_resp.content}",
        tool_call_id=last_tool_msg.tool_call_id,
        name=last_tool_msg.name,
    )

    return {"messages": [summarized]}
