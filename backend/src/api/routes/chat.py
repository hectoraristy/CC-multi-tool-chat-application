from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import boto3
from api.dependencies import get_graph, get_store
from api.models import ChatRequest, FileUploadResponse
from config import get_settings
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from langchain_core.messages import HumanMessage
from services.chat_service import stream_agent_events
from services.message_converter import build_langchain_messages
from services.persistence import persist_user_message, validate_session_exists
from sse_starlette.sse import EventSourceResponse
from storage.protocols import Store

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

router = APIRouter(prefix="/api/chat", tags=["chat"])

_ALLOWED_EXTENSIONS = {".csv", ".pdf"}
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    session_id: str = Form(...),
    file: UploadFile = ...,
    store: Store = Depends(get_store),
) -> FileUploadResponse:
    """Upload a CSV or PDF file for processing in the chat session."""
    validate_session_exists(store, session_id)

    settings = get_settings()
    if not settings.s3_results_bucket:
        raise HTTPException(status_code=501, detail="File uploads require S3 to be configured")

    filename = file.filename or "upload"
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}",
        )

    contents = await file.read()
    if len(contents) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit")

    file_id = uuid.uuid4().hex[:12]
    s3_key = f"uploads/{session_id}/{file_id}_{filename}"
    s3_uri = f"s3://{settings.s3_results_bucket}/{s3_key}"

    s3 = boto3.client("s3", region_name=settings.aws_region)
    s3.put_object(Bucket=settings.s3_results_bucket, Key=s3_key, Body=contents)

    return FileUploadResponse(
        s3_uri=s3_uri,
        filename=filename,
        file_type=ext.lstrip("."),
        size_bytes=len(contents),
    )


def _build_attachment_context(body: ChatRequest) -> str | None:
    if not body.attachments:
        return None
    lines: list[str] = []
    for att in body.attachments:
        lines.append(
            f"[Uploaded file: {att.filename} ({att.file_type}) at {att.s3_uri}]"
        )
    lines.append("Use the file_source tool with the S3 URI above to read and process the file.")
    return "\n".join(lines)


@router.post("")
async def chat(
    body: ChatRequest,
    store: Store = Depends(get_store),
    graph: CompiledStateGraph = Depends(get_graph),
) -> EventSourceResponse:
    validate_session_exists(store, body.session_id)
    persist_user_message(store, body.session_id, body.message)

    stored_messages = store.get_messages(body.session_id)
    lc_messages = build_langchain_messages(stored_messages)

    attachment_ctx = _build_attachment_context(body)
    if attachment_ctx and lc_messages and isinstance(lc_messages[-1], HumanMessage):
        original = lc_messages[-1].content
        lc_messages[-1] = HumanMessage(content=f"{original}\n\n{attachment_ctx}")

    tools_used = list({
        m.tool_name for m in stored_messages
        if m.role in ("tool_call", "tool") and m.tool_name
    })

    return EventSourceResponse(
        stream_agent_events(
            graph,
            store,
            body.session_id,
            lc_messages,
            tools_used_this_session=tools_used,
            turn_count=len(stored_messages),
        )
    )
