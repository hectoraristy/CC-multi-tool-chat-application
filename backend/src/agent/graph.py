from __future__ import annotations

from agent.llm_factory import create_llm
from agent.nodes import evaluate_node, plan_node
from agent.prompt_builder import build_system_prompt
from agent.state import AgentState
from config import get_settings
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from services.chunking import ChunkingMiddleware
from services.context_manager import compact_chunked_messages
from tools import ALL_TOOLS


def _agent_node(state: AgentState) -> dict[str, list[BaseMessage]]:
    llm = create_llm()
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    messages = list(state["messages"])
    session_id = state.get("session_id", "unknown")

    has_system = any(isinstance(m, SystemMessage) for m in messages)
    if not has_system:
        prompt = build_system_prompt(
            session_id=session_id,
            tools_used=state.get("tools_used_this_session", []),
            user_facts=state.get("user_facts", []),
        )
        messages = [SystemMessage(content=prompt)] + messages

    settings = get_settings()
    model = settings.openai_model if settings.llm_provider == "openai" else ""
    messages = compact_chunked_messages(
        messages,
        max_tokens=settings.max_context_tokens,
        recent_to_preserve=settings.recent_turns_to_preserve,
        model=model,
    )

    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def _route_after_agent(state: AgentState) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


def _should_plan(state: AgentState) -> str:
    """Route to the plan node on first turn, otherwise skip to agent."""
    turn_count = state.get("turn_count", 0)
    has_assistant = any(
        not isinstance(m, (SystemMessage,)) and hasattr(m, "content")
        and getattr(m, "type", "") == "ai"
        for m in state.get("messages", [])
    )
    if turn_count <= 1 and not has_assistant:
        return "plan"
    return "agent"


def build_graph() -> StateGraph:
    tool_node = ToolNode(ALL_TOOLS)
    chunked_tools = ChunkingMiddleware(tool_node)

    graph = StateGraph(AgentState)
    graph.add_node("plan", plan_node)
    graph.add_node("agent", _agent_node)
    graph.add_node("tools", chunked_tools)
    graph.add_node("evaluate", evaluate_node)

    graph.set_entry_point("router")
    graph.add_node("router", lambda state: {})
    graph.add_conditional_edges(
        "router",
        _should_plan,
        {"plan": "plan", "agent": "agent"},
    )

    graph.add_edge("plan", "agent")
    graph.add_conditional_edges("agent", _route_after_agent, {"tools": "tools", END: END})
    graph.add_edge("tools", "evaluate")
    graph.add_conditional_edges(
        "evaluate",
        lambda state: state.get("_eval_route", "agent"),
        {"agent": "agent", END: END},
    )

    return graph.compile()
