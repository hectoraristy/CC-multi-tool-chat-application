from __future__ import annotations

import logging
import re

import tiktoken
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

logger = logging.getLogger(__name__)

_CHUNK_ANNOTATION_RE = re.compile(
    r"(\[Chunked: result_id=[0-9a-f-]+, chunk \d+/\d+.*?retrieve more chunks\.\])\n*",
    re.DOTALL,
)

_RESULT_ID_RE = re.compile(
    r"\[(?:Summarized — full result stored as|Result ID:|Chunked: result_id=)\s*([0-9a-f-]{36})"
)


def count_message_tokens(messages: list[BaseMessage], model: str = "") -> int:
    """Return an approximate token count for a list of LangChain messages.

    Uses tiktoken when the model is an OpenAI model, otherwise falls back to
    a character-based heuristic (len / 4).
    """
    try:
        enc = tiktoken.encoding_for_model(model or "gpt-4o")
        total = 0
        for msg in messages:
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            total += len(enc.encode(content)) + 4  # per-message overhead
        return total
    except Exception:
        total = 0
        for msg in messages:
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            total += len(content) // 4 + 4
        return total


def compact_chunked_messages(
    messages: list[BaseMessage],
    max_tokens: int,
    recent_to_preserve: int = 5,
    model: str = "",
) -> list[BaseMessage]:
    """Strip chunk data from old ToolMessages to fit within *max_tokens*.

    Chunked ToolMessages contain an annotation header followed by raw chunk data.
    For messages outside the most recent *recent_to_preserve* messages, the chunk
    data is removed and only the annotation is kept, dramatically reducing tokens
    while preserving the tool_call_id pairing that OpenAI requires.

    If the messages are already within budget, they are returned unchanged.
    """
    total = count_message_tokens(messages, model)
    if total <= max_tokens:
        return messages

    preserve_boundary = max(0, len(messages) - recent_to_preserve)

    compacted: list[BaseMessage] = []
    for i, msg in enumerate(messages):
        if (
            i < preserve_boundary
            and isinstance(msg, ToolMessage)
            and isinstance(msg.content, str)
        ):
            match = _CHUNK_ANNOTATION_RE.match(msg.content)
            if match and len(msg.content) > len(match.group(0)) + 100:
                compacted.append(
                    ToolMessage(
                        content=match.group(1) + "\n[Chunk data removed from history to save context. "
                        "Use data_analysis with the original file path for computations, "
                        "or session_manager(action='get_chunk') to retrieve raw chunks.]",
                        tool_call_id=getattr(msg, "tool_call_id", ""),
                        name=msg.name,
                        id=msg.id,
                    )
                )
                continue
        compacted.append(msg)

    new_total = count_message_tokens(compacted, model)
    if new_total <= max_tokens:
        logger.info("Context compaction reduced tokens from %d to %d", total, new_total)
        return compacted

    # Still over budget — summarize old messages instead of dropping them so
    # the model retains awareness of what was discussed and which result_ids
    # are available for re-fetching.
    summarized: list[BaseMessage] = []
    for i, msg in enumerate(compacted):
        if isinstance(msg, SystemMessage) or i >= preserve_boundary:
            summarized.append(msg)
            continue

        summarized.append(_summarize_message(msg))

    final_total = count_message_tokens(summarized, model)
    logger.info(
        "Context compaction + summarization reduced tokens from %d to %d (%d messages)",
        total, final_total, len(summarized),
    )
    return summarized


def _extract_result_ids(text: str) -> list[str]:
    """Pull all result_id UUIDs from a message's content."""
    return _RESULT_ID_RE.findall(text)


_SUMMARY_CHAR_LIMIT = 200


def _summarize_message(msg: BaseMessage) -> BaseMessage:
    """Return a compact version of *msg* that preserves result_id references."""
    content = msg.content if isinstance(msg.content, str) else str(msg.content)

    if isinstance(msg, HumanMessage):
        return msg

    if isinstance(msg, ToolMessage):
        result_ids = _extract_result_ids(content)
        ref_note = (
            " | Stored result_ids: " + ", ".join(result_ids)
            if result_ids
            else ""
        )
        preview = content[:_SUMMARY_CHAR_LIMIT].replace("\n", " ")
        compact = (
            f"[Summarized tool result]{ref_note}\n{preview}..."
            "\n[Use session_manager(action='get_chunk') with the result_id to "
            "retrieve full data.]"
        )
        return ToolMessage(
            content=compact,
            tool_call_id=getattr(msg, "tool_call_id", ""),
            name=msg.name,
            id=msg.id,
        )

    if isinstance(msg, AIMessage):
        if getattr(msg, "tool_calls", None):
            return AIMessage(
                content="",
                tool_calls=msg.tool_calls,
                id=msg.id,
            )
        preview = content[:_SUMMARY_CHAR_LIMIT].replace("\n", " ")
        return AIMessage(content=f"[Earlier response summarized] {preview}...", id=msg.id)

    return msg
