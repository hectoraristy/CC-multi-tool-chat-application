from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from typing import Any, Literal

from api.dependencies import get_s3_store, get_store
from config import get_settings
from constants import RESULT_ID_RE, S3_OFFLOAD_THRESHOLD
from langchain_core.tools import tool
from storage.models import ToolResult
from storage.protocols import Store
from storage.s3 import S3ResultStore

logger = logging.getLogger(__name__)


def _handle_store(
    store: Store,
    session_id: str,
    result_id: str,
    tool_name: str,
    content: str,
    summary: str,
    **_: Any,
) -> str:
    for text in (content, summary):
        match = RESULT_ID_RE.search(text)
        if match:
            existing_rid = match.group(1)
            existing = store.get_tool_result(session_id, existing_rid)
            if existing:
                logger.info(
                    "Skipping duplicate store — full result already saved as %s (%d bytes)",
                    existing_rid,
                    existing.size_bytes,
                )
                return (
                    f"[Result ID: {existing_rid}] Full result is already stored "
                    f"({existing.size_bytes} bytes). No need to store again."
                )

    rid = result_id or str(uuid.uuid4())
    truncated_summary = summary or content[:500]

    s3_key: str | None = None
    stored_content = content

    s3 = get_s3_store()
    if s3 is not None and len(content.encode("utf-8")) > S3_OFFLOAD_THRESHOLD:
        s3_key = S3ResultStore.make_key(session_id, rid)
        s3.upload_result(s3_key, content)
        stored_content = ""
        logger.info("Offloaded large result %s to S3 key %s", rid, s3_key)

    result = ToolResult(
        session_id=session_id,
        result_id=rid,
        tool_name=tool_name,
        summary=truncated_summary,
        full_result=stored_content,
        s3_key=s3_key,
        size_bytes=len(content.encode("utf-8")),
        metadata={"source_tool": tool_name},
    )
    store.store_tool_result(result)
    return (
        f"[Result ID: {rid}] Stored from tool '{tool_name}' "
        f"({result.size_bytes} bytes). Summary: {truncated_summary[:200]}"
    )


def _handle_retrieve(
    store: Store,
    session_id: str,
    result_id: str,
    **_: Any,
) -> str:
    if not result_id:
        return "Error: result_id is required for retrieve action."
    result = store.get_tool_result(session_id, result_id)
    if result is None:
        return f"No result found with id '{result_id}' in session '{session_id}'."

    if result.full_result:
        return result.full_result

    if result.s3_key:
        s3 = get_s3_store()
        if s3 is not None:
            return s3.download_result(result.s3_key)

    return f"No content available for result '{result_id}'."


def _handle_list(
    store: Store,
    session_id: str,
    **_: Any,
) -> str:
    items = store.list_tool_results(session_id)
    if not items:
        return "No stored results in this session."
    lines = [
        f"- [{item.result_id}] {item.tool_name} | " f"{item.size_bytes}B | {item.summary[:120]}"
        for item in items
    ]
    return "\n".join(lines)


def _handle_download_url(
    store: Store,
    session_id: str,
    result_id: str,
    **_: Any,
) -> str:
    if not result_id:
        return "Error: result_id is required for get_download_url action."
    result = store.get_tool_result(session_id, result_id)
    if result is None:
        return f"No result found with id '{result_id}' in session '{session_id}'."

    settings = get_settings()
    s3 = get_s3_store()

    if result.s3_key and s3 is not None:
        url = s3.generate_presigned_url(result.s3_key)
        return f"Download URL (expires in {settings.s3_presigned_url_expiry}s): {url}"

    if result.full_result and s3 is not None:
        s3_key = S3ResultStore.make_key(session_id, result_id)
        s3.upload_result(s3_key, result.full_result)
        result.s3_key = s3_key
        store.store_tool_result(result)
        url = s3.generate_presigned_url(s3_key)
        return f"Download URL (expires in {settings.s3_presigned_url_expiry}s): {url}"

    return (
        "Cannot generate a download URL — S3 storage is not configured. "
        "The user can download the result using the download button in the UI."
    )


def _handle_get_chunk(
    store: Store,
    session_id: str,
    result_id: str,
    chunk_index: int = 0,
    **_: Any,
) -> str:
    """Retrieve a specific chunk of a previously stored (and chunked) result."""
    if not result_id:
        return "Error: result_id is required for get_chunk action."

    result = store.get_tool_result(session_id, result_id)
    if result is None:
        return f"No result found with id '{result_id}' in session '{session_id}'."

    if result.total_chunks == 0:
        return (
            f"Result '{result_id}' was not chunked. "
            "Use action='retrieve' to get the full content."
        )

    if chunk_index < 0 or chunk_index >= result.total_chunks:
        return (
            f"Invalid chunk_index {chunk_index}. "
            f"Valid range: 0 to {result.total_chunks - 1}."
        )

    if result.full_result:
        full_content = result.full_result
    elif result.s3_key:
        s3 = get_s3_store()
        if s3 is not None:
            full_content = s3.download_result(result.s3_key)
        else:
            return f"Cannot retrieve content — S3 storage is not available."
    else:
        return f"No content available for result '{result_id}'."

    from services.chunking import get_content_chunk

    chunk = get_content_chunk(full_content, chunk_index, result.chunk_size_chars)
    return (
        f"[Chunk {chunk_index + 1}/{result.total_chunks} of result {result_id}]\n\n"
        f"{chunk}"
    )


_ACTION_HANDLERS: dict[str, Callable[..., str]] = {
    "store": _handle_store,
    "retrieve": _handle_retrieve,
    "list": _handle_list,
    "get_download_url": _handle_download_url,
    "get_chunk": _handle_get_chunk,
}


@tool
def session_manager(
    action: Literal["store", "retrieve", "list", "get_download_url", "get_chunk"],
    session_id: str,
    result_id: str = "",
    tool_name: str = "",
    content: str = "",
    summary: str = "",
    chunk_index: int = 0,
) -> str:
    """Manage stored tool results for the current chat session.

    Actions:
      - store: Persist a tool result. Provide tool_name, content, and optionally summary.
        Returns the result_id and metadata (the full content is NOT echoed back).
      - retrieve: Fetch the full content of a previously stored result by result_id.
      - list: List metadata (id, tool_name, summary, size) of all stored results.
      - get_download_url: Generate a temporary download URL for a stored result by result_id.
        Returns a pre-signed URL the user can open in their browser.
      - get_chunk: Retrieve a specific chunk of a large, auto-chunked result.
        Provide result_id and chunk_index (0-based). Returns the chunk content
        with a header indicating the chunk number and total.
    """
    handler = _ACTION_HANDLERS.get(action)
    if handler is None:
        return f"Unknown action: {action}"

    return handler(
        store=get_store(),
        session_id=session_id,
        result_id=result_id,
        tool_name=tool_name,
        content=content,
        summary=summary,
        chunk_index=chunk_index,
    )
