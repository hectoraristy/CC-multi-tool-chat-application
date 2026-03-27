from __future__ import annotations

import logging
from typing import Any

from agent.state import AgentState
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


PLAN_SYSTEM_PROMPT = (
    "You are a planning assistant. Given the user's request, produce a brief "
    "internal plan (3-5 bullet points) describing which tools to use and in "
    "what order. Do NOT execute any tools — just outline the approach. "
    "Keep it under 200 tokens."
)


# ── Planning node ──────────────────────────────────────────────────────


def plan_node(state: AgentState) -> dict[str, Any]:
    """Generate a lightweight plan on the first turn of a session."""
    from agent.llm_factory import create_llm

    messages = state.get("messages", [])
    if not messages:
        return {}

    last_user_msg = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_msg = msg
            break
    if last_user_msg is None:
        return {}

    llm = create_llm()
    plan_resp = llm.invoke(
        [
            SystemMessage(content=PLAN_SYSTEM_PROMPT),
            HumanMessage(content=last_user_msg.content),
        ]
    )

    plan_content = plan_resp.content if isinstance(plan_resp.content, str) else str(plan_resp.content)
    logger.info("Generated plan: %s", plan_content[:200])

    plan_msg = SystemMessage(content=f"Internal plan:\n{plan_content}")
    return {"messages": [plan_msg]}
