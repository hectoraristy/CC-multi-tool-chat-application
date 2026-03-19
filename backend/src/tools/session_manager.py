"""Session Manager Tool — the core tool for persisting and retrieving tool results.

The agent uses this to:
  1. **store** a tool result in DynamoDB (returns metadata only, keeping context lean).
  2. **retrieve** a previously stored result by ID (brings full content into context).
  3. **list** metadata for all stored results in the current session.
"""

from __future__ import annotations

import uuid
from typing import Literal

from langchain_core.tools import tool

from storage.dynamo import DynamoDBStore
from storage.models import ToolResult

_store = None


def _get_store() -> DynamoDBStore:
    global _store
    if _store is None:
        _store = DynamoDBStore()
    return _store


def set_store(store: DynamoDBStore) -> None:
    global _store
    _store = store


@tool
def session_manager(
    action: Literal["store", "retrieve", "list"],
    session_id: str,
    result_id: str = "",
    tool_name: str = "",
    content: str = "",
    summary: str = "",
) -> str:
    """Manage stored tool results for the current chat session.

    Actions:
      - store: Persist a tool result. Provide tool_name, content, and optionally summary.
        Returns the result_id and metadata (the full content is NOT echoed back).
      - retrieve: Fetch the full content of a previously stored result by result_id.
      - list: List metadata (id, tool_name, summary, size) of all stored results.
    """
    store = _get_store()

    if action == "store":
        rid = result_id or str(uuid.uuid4())
        truncated_summary = summary or content[:500]
        result = ToolResult(
            session_id=session_id,
            result_id=rid,
            tool_name=tool_name,
            summary=truncated_summary,
            full_result=content,
            metadata={"source_tool": tool_name},
        )
        store.store_tool_result(result)
        return (
            f"Stored result {rid} from tool '{tool_name}' "
            f"({result.size_bytes} bytes). Summary: {truncated_summary[:200]}"
        )

    if action == "retrieve":
        if not result_id:
            return "Error: result_id is required for retrieve action."
        result = store.get_tool_result(session_id, result_id)
        if result is None:
            return f"No result found with id '{result_id}' in session '{session_id}'."
        return result.full_result

    if action == "list":
        items = store.list_tool_results(session_id)
        if not items:
            return "No stored results in this session."
        lines = []
        for item in items:
            lines.append(
                f"- [{item.result_id}] {item.tool_name} | "
                f"{item.size_bytes}B | {item.summary[:120]}"
            )
        return "\n".join(lines)

    return f"Unknown action: {action}"
