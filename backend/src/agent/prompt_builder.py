from __future__ import annotations

from storage.models import ToolResultMetadata

_BASE_IDENTITY = "You are a helpful multi-tool AI assistant."

_CHUNKING_INSTRUCTIONS = (
    "IMPORTANT — automatic chunking of large results:\n"
    "When a tool result is too large for the context window, it is automatically "
    "stored and chunked. You will receive chunk 1 with a marker like:\n"
    "  [Chunked: result_id=<id>, chunk 1/N, ...]\n"
    "followed by the first chunk of data.\n\n"
    "When you see a chunked result:\n"
    "1. ALWAYS tell the user the data was too large and has been split into N chunks.\n"
    "2. Present the first chunk to the user.\n"
    "3. Let the user know they can ask for subsequent chunks.\n"
    "4. When the user asks for the next chunk, call:\n"
    "   session_manager(action='get_chunk', session_id=<session_id>, "
    "result_id=<id>, chunk_index=<N>)\n"
    "   where chunk_index is 0-based (chunk 1 = index 0, chunk 2 = index 1, etc.).\n\n"
    "Do NOT call session_manager(action='store') for auto-chunked results — "
    "the full content is already persisted.\n\n"
    "CRITICAL — re-fetching compacted data:\n"
    "Older tool results may be summarized in the conversation history to save context "
    "space. When you see '[Summarized tool result]' or '[Chunk data removed from "
    "history]' for a result, you MUST call session_manager(action='get_chunk') with "
    "the result_id to re-retrieve the full data before answering questions about it. "
    "Never paraphrase, abbreviate, or work from memory when full data is available "
    "for retrieval.\n"
    "When the user asks about content from a file that was previously read, always "
    "re-fetch the relevant chunk(s) rather than relying on what may be an incomplete "
    "context window.\n\n"
    "IMPORTANT — analytical follow-up queries on large files:\n"
    "When the user asks analytical questions about a previously read or chunked file "
    "(e.g. sums, averages, filtering, searching, counting), use the data_analysis tool "
    "with the ORIGINAL file path (the s3:// URI or local path from the earlier file_source call). "
    "data_analysis runs computations server-side and returns only the result, "
    "avoiding context window overflow. Do NOT re-read the file with file_source."
)

_TOOL_DESCRIPTIONS: dict[str, tuple[str, str]] = {
    "session_manager": (
        "Store, retrieve, list, get download URLs, or get chunks for tool results in the session.",
        "session_manager: Manage stored tool results (store/retrieve/list/download URLs/get_chunk). "
        "Use action='get_chunk' with result_id and chunk_index to retrieve subsequent chunks "
        "of auto-chunked results. Always pass the session ID when calling.",
    ),
    "database_query": (
        "Run read-only SQL queries.",
        "database_query: Run read-only SQL queries against connected databases.",
    ),
    "web_download": (
        "Fetch web page content.",
        "web_download: Fetch and extract content from web pages.",
    ),
    "external_api": (
        "Call external HTTP APIs.",
        "external_api: Make HTTP requests to external APIs (GET, POST, etc.).",
    ),
    "file_source": (
        "Read CSV, JSON, or PDF files (initial preview).",
        "file_source: Read and parse CSV, JSON, or PDF files from local paths or S3 URIs. "
        "Best for an initial preview of file contents. For analytical follow-up queries "
        "(sums, averages, filtering, searching) use data_analysis instead.",
    ),
    "data_analysis": (
        "Run server-side computations on CSV/JSON files (sum, filter, describe, etc.).",
        "data_analysis: Analyze CSV or JSON files server-side using pandas. "
        "Operations: describe, head, tail, aggregate (sum/mean/count/min/max/std/median/nunique), "
        "query (filter rows), value_counts, search. "
        "Accepts a file path (local or s3:// URI). Use this for analytical questions about "
        "files instead of re-reading the full file with file_source.",
    ),
}


def _format_results_inventory(stored_results: list[ToolResultMetadata]) -> str:
    if not stored_results:
        return ""
    lines = ["Previously stored results in this session:"]
    for r in stored_results[:20]:
        size_label = (
            f"{r.size_bytes / 1024:.1f}KB" if r.size_bytes >= 1024
            else f"{r.size_bytes}B"
        )
        summary_preview = r.summary[:80].replace("\n", " ") if r.summary else ""
        lines.append(f"  - {r.result_id} ({r.tool_name}, {size_label}): {summary_preview}")
    lines.append(
        "Use session_manager with action='get_download_url' and the result_id "
        "to generate a temporary download URL when the user requests one."
    )
    return "\n".join(lines)


def _format_tool_instructions(tools_used: list[str]) -> str:
    """Full descriptions for tools already used; one-liners for the rest."""
    lines = ["Available tools:"]
    for name, (short_desc, full_desc) in _TOOL_DESCRIPTIONS.items():
        if name in tools_used:
            lines.append(f"- {full_desc}")
        else:
            lines.append(f"- {name}: {short_desc}")
    return "\n".join(lines)


def build_system_prompt(
    session_id: str,
    stored_results: list[ToolResultMetadata] | None = None,
    tools_used: list[str] | None = None,
    user_facts: list[str] | None = None,
) -> str:
    """Assemble a dynamic system prompt from contextual sections."""
    sections: list[str] = [_BASE_IDENTITY]

    sections.append(f"The current session ID is: {session_id}")

    if user_facts:
        facts_block = "\n".join(f"- {f}" for f in user_facts)
        sections.append(f"Known user context:\n{facts_block}")

    inventory = _format_results_inventory(stored_results or [])
    if inventory:
        sections.append(inventory)

    sections.append(_format_tool_instructions(tools_used or []))
    sections.append(_CHUNKING_INSTRUCTIONS)
    sections.append(
        "Provide thorough, detailed responses. Reproduce information from tool "
        "results verbatim when relevant. Do not summarize or abbreviate unless "
        "the user explicitly asks for a summary."
    )

    return "\n\n".join(sections)
