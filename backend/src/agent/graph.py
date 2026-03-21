from __future__ import annotations

from agent.llm_factory import create_llm
from agent.nodes import should_summarize, summarize_node
from agent.state import AgentState
from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from tools import ALL_TOOLS

SYSTEM_PROMPT_TEMPLATE = (
    "You are a helpful multi-tool AI assistant. "
    "The current session ID is: {session_id}\n\n"
    "You have access to several tools:\n"
    "- session_manager: Store, retrieve, list, or get download URLs for tool results "
    "persisted in the session.\n"
    "- database_query: Run read-only SQL queries.\n"
    "- web_download: Fetch web page content.\n"
    "- external_api: Call external HTTP APIs.\n"
    "- file_source: Read CSV/JSON files.\n\n"
    "IMPORTANT — automatic storage of large results:\n"
    "When a tool result is large, it is automatically stored and you will see a "
    "message like '[Summarized — full result stored as <result_id>]' followed by "
    "a summary. The FULL content is already saved under that result_id. "
    "Do NOT call session_manager(action='store') again for these results — "
    "doing so would only save the summary, not the full content.\n\n"
    "Only use session_manager(action='store') for results that were NOT "
    "automatically stored (i.e. results that do not contain the "
    "'[Summarized — full result stored as ...]' marker).\n\n"
    "When the user asks to download or get a link to a stored result, use "
    "session_manager with action='get_download_url' and the result_id to generate "
    "a temporary download URL. Share that URL directly with the user.\n\n"
    "At the start of a conversation, if prior messages reference stored results or "
    "you suspect relevant data was previously stored, use session_manager with "
    "action='list' to check what is available before re-fetching.\n\n"
    "Always pass the session ID shown above when calling session_manager.\n\n"
    "Always be concise and helpful."
)


def _agent_node(state: AgentState) -> dict[str, list[BaseMessage]]:
    llm = create_llm()
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    messages = state["messages"]
    from langchain_core.messages import SystemMessage

    session_id = state.get("session_id", "unknown")
    prompt = SYSTEM_PROMPT_TEMPLATE.format(session_id=session_id)

    has_system = any(isinstance(m, SystemMessage) for m in messages)
    if not has_system:
        messages = [SystemMessage(content=prompt)] + list(messages)

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
