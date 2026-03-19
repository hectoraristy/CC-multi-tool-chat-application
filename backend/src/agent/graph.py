from __future__ import annotations

from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from agent.llm_factory import create_llm
from agent.nodes import should_summarize, summarize_node
from agent.state import AgentState
from tools import ALL_TOOLS

SYSTEM_PROMPT = (
    "You are a helpful multi-tool AI assistant. You have access to several tools:\n"
    "- session_manager: Store, retrieve, or list tool results persisted in the session.\n"
    "- database_query: Run read-only SQL queries.\n"
    "- web_download: Fetch web page content.\n"
    "- external_api: Call external HTTP APIs.\n"
    "- file_source: Read CSV/JSON files.\n\n"
    "When a tool returns a large result, use the session_manager to store it and "
    "refer to the stored result by ID in future turns. Only retrieve the full content "
    "when the user specifically needs it.\n\n"
    "Always be concise and helpful."
)


def _agent_node(state: AgentState) -> dict[str, list[BaseMessage]]:
    llm = create_llm()
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    messages = state["messages"]
    from langchain_core.messages import SystemMessage

    has_system = any(isinstance(m, SystemMessage) for m in messages)
    if not has_system:
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)

    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def _route_after_agent(state: AgentState) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


def build_graph() -> StateGraph:
    tool_node = ToolNode(ALL_TOOLS)

    graph = StateGraph(AgentState)
    graph.add_node("agent", _agent_node)
    graph.add_node("tools", tool_node)
    graph.add_node("summarize", summarize_node)

    graph.set_entry_point("agent")

    graph.add_conditional_edges("agent", _route_after_agent, {"tools": "tools", END: END})
    graph.add_conditional_edges(
        "tools",
        should_summarize,
        {"summarize": "summarize", "agent": "agent"},
    )
    graph.add_edge("summarize", "agent")

    return graph.compile()
