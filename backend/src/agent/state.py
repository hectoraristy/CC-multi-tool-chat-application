from __future__ import annotations

from typing import Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import NotRequired, TypedDict


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    session_id: str
    tools_used_this_session: NotRequired[list[str]]
    turn_count: NotRequired[int]
    _eval_route: NotRequired[str]
