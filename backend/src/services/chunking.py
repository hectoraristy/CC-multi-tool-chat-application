from __future__ import annotations

import logging
import uuid
from typing import Any

from config import get_settings
from constants import S3_OFFLOAD_THRESHOLD
from langchain_core.messages import BaseMessage, ToolMessage
from services.context_manager import count_message_tokens
from storage.models import ToolResult
from storage.s3 import S3ResultStore

logger = logging.getLogger(__name__)


def _compute_line_chunks(content: str, chunk_size_chars: int) -> list[tuple[int, int]]:
    """Return ``(start, end)`` character offsets for each chunk.

    Boundaries are snapped to newlines when possible, then to spaces as a
    fallback.  If a segment contains neither (e.g. base64 or minified JSON),
    it is split at exactly *chunk_size_chars* characters.
    """
    if not content:
        return [(0, 0)]

    chunks: list[tuple[int, int]] = []
    start = 0
    length = len(content)

    while start < length:
        end = min(start + chunk_size_chars, length)
        if end < length:
            newline_pos = content.rfind("\n", start, end)
            if newline_pos > start:
                end = newline_pos + 1
            else:
                space_pos = content.rfind(" ", start, end)
                if space_pos > start:
                    end = space_pos + 1
        chunks.append((start, end))
        start = end

    return chunks or [(0, length)]


def _estimate_chunk_size_chars(
    content: str,
    token_budget: int,
    model: str = "",
) -> int:
    """Return the target character length per chunk for *token_budget* tokens.

    A 10 % safety margin is applied to account for non-uniform token density
    across different regions of *content*.
    """
    dummy = [ToolMessage(content=content, tool_call_id="calc")]
    total_tokens = count_message_tokens(dummy, model)
    if total_tokens <= 0:
        return len(content)

    chars_per_token = len(content) / total_tokens
    effective_budget = int(token_budget * 0.9)
    return max(1, int(chars_per_token * effective_budget))


def get_content_chunk(content: str, chunk_index: int, chunk_size_chars: int) -> str:
    """Return the slice of *content* for the given zero-based *chunk_index*,
    snapped to line boundaries so rows are never split mid-line."""
    boundaries = _compute_line_chunks(content, chunk_size_chars)
    if chunk_index < 0 or chunk_index >= len(boundaries):
        return ""
    start, end = boundaries[chunk_index]
    return content[start:end]


class ChunkingMiddleware:
    """Wraps a LangGraph ToolNode to auto-chunk large results.

    After the inner tool node executes, every ``ToolMessage`` whose content
    exceeds ``chunk_token_budget`` tokens is:

    1. Persisted in full to DynamoDB (and S3 for large payloads).
    2. Replaced with **chunk 1** plus a metadata annotation so the LLM
       knows how to request subsequent chunks via ``session_manager``.

    Usage::

        from langgraph.prebuilt import ToolNode
        from services.chunking import ChunkingMiddleware

        tool_node = ToolNode(tools)
        chunked = ChunkingMiddleware(tool_node, chunk_token_budget=30_000)
        graph.add_node("tools", chunked)
    """

    def __init__(
        self,
        tool_node: Any,
        chunk_token_budget: int | None = None,
    ) -> None:
        self.tool_node = tool_node
        self.chunk_token_budget = (
            chunk_token_budget
            if chunk_token_budget is not None
            else get_settings().chunk_token_budget
        )

    def __call__(self, state: dict[str, Any]) -> dict[str, list[BaseMessage]]:
        result = self.tool_node.invoke(state)
        return self._process_results(state, result)

    def _process_results(
        self,
        state: dict[str, Any],
        result: dict[str, Any],
    ) -> dict[str, list[BaseMessage]]:
        messages: list[BaseMessage] = result.get("messages", [])
        if not messages:
            return result

        settings = get_settings()
        model = settings.openai_model if settings.llm_provider == "openai" else ""

        processed: list[BaseMessage] = []
        for msg in messages:
            if isinstance(msg, ToolMessage) and msg.content:
                token_count = count_message_tokens([msg], model)
                if token_count > self.chunk_token_budget:
                    msg = self._chunk_message(state, msg, model)
            processed.append(msg)

        return {"messages": processed}

    def _chunk_message(
        self,
        state: dict[str, Any],
        msg: ToolMessage,
        model: str,
    ) -> ToolMessage:
        from api.dependencies import get_s3_store, get_store

        session_id = state.get("session_id", "unknown")
        result_id = str(uuid.uuid4())
        full_content = msg.content if isinstance(msg.content, str) else str(msg.content)
        byte_size = len(full_content.encode("utf-8"))

        chunk_size_chars = _estimate_chunk_size_chars(
            full_content, self.chunk_token_budget, model
        )
        boundaries = _compute_line_chunks(full_content, chunk_size_chars)
        total_chunks = len(boundaries)

        s3_key: str | None = None
        s3_chunk_prefix: str | None = None
        stored_content = full_content
        uploaded_s3_keys: list[str] = []

        try:
            s3 = get_s3_store()
            if s3 is not None and byte_size > S3_OFFLOAD_THRESHOLD:
                s3_key = S3ResultStore.make_key(session_id, result_id)
                s3.upload_result(s3_key, full_content)
                uploaded_s3_keys.append(s3_key)

                s3_chunk_prefix = f"results/{session_id}/{result_id}/chunk_"
                for i, (start, end) in enumerate(boundaries):
                    chunk_key = S3ResultStore.make_chunk_key(
                        session_id, result_id, i
                    )
                    s3.upload_result(chunk_key, full_content[start:end])
                    uploaded_s3_keys.append(chunk_key)

                stored_content = ""
                logger.info(
                    "Offloaded chunked result %s to S3 (%d chunk objects)",
                    result_id,
                    total_chunks,
                )

            store = get_store()
            store.store_tool_result(
                ToolResult(
                    session_id=session_id,
                    result_id=result_id,
                    tool_name=msg.name or "unknown",
                    summary=full_content[:500],
                    full_result=stored_content,
                    s3_key=s3_key,
                    s3_chunk_prefix=s3_chunk_prefix,
                    size_bytes=byte_size,
                    total_chunks=total_chunks,
                    chunk_size_chars=chunk_size_chars,
                    metadata={"auto_chunked": True, "source": "ChunkingMiddleware"},
                )
            )
        except Exception:
            logger.exception(
                "Failed to persist chunked result %s — returning original message",
                result_id,
            )
            self._cleanup_s3(uploaded_s3_keys)
            return msg

        start, end = boundaries[0]
        chunk_1 = full_content[start:end]

        annotation = (
            f"[Chunked: result_id={result_id}, chunk 1/{total_chunks}, "
            f"~{self.chunk_token_budget} tokens per chunk. "
            f"Use session_manager(action='get_chunk', result_id='{result_id}', "
            f"chunk_index=N) to retrieve more chunks.]\n\n"
        )

        logger.info(
            "Auto-chunked tool result %s: %d chunks of ~%d chars each (%d bytes total)",
            result_id,
            total_chunks,
            chunk_size_chars,
            byte_size,
        )

        return ToolMessage(
            content=annotation + chunk_1,
            tool_call_id=msg.tool_call_id,
            name=msg.name,
            id=msg.id,
        )

    @staticmethod
    def _cleanup_s3(keys: list[str]) -> None:
        """Best-effort removal of S3 objects uploaded before a failure."""
        if not keys:
            return
        try:
            from api.dependencies import get_s3_store

            s3 = get_s3_store()
            if s3 is not None:
                for key in keys:
                    try:
                        s3.delete_result(key)
                    except Exception:
                        logger.debug("Failed to clean up S3 key %s", key, exc_info=True)
        except Exception:
            logger.debug("S3 cleanup skipped — store unavailable", exc_info=True)
