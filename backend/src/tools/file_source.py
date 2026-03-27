from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import boto3
from langchain_core.tools import tool

MAX_ROWS = 500
MAX_TEXT_CHARS = 50_000


@tool
def file_source(path: str) -> str:
    """Read a CSV, JSON, or PDF file and return its contents as formatted text.

    Supports local file paths and S3 URIs (s3://bucket/key).
    CSV files are returned as a markdown-style table (limited to 500 rows).
    JSON files are returned as pretty-printed JSON.
    PDF files are returned as extracted text (page by page).
    """
    lower = path.lower()

    if lower.endswith(".pdf"):
        try:
            raw_bytes = _read_raw_bytes(path)
        except Exception as exc:
            return f"Error reading file: {exc}"
        return _format_pdf(raw_bytes)

    try:
        raw = _read_raw(path)
    except Exception as exc:
        return f"Error reading file: {exc}"

    if lower.endswith(".csv"):
        return _format_csv(raw)
    if lower.endswith(".json"):
        return _format_json(raw)

    return raw[:MAX_TEXT_CHARS] if len(raw) > MAX_TEXT_CHARS else raw


def _read_raw(path: str) -> str:
    if path.startswith("s3://"):
        return _read_s3_text(path)
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return p.read_text(encoding="utf-8")


def _read_raw_bytes(path: str) -> bytes:
    """Read file as raw bytes — required for binary formats like PDF."""
    if path.startswith("s3://"):
        return _read_s3_bytes(path)
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return p.read_bytes()


def _parse_s3_uri(uri: str) -> tuple[str, str]:
    parts = uri.replace("s3://", "").split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid S3 URI: {uri}")
    return parts[0], parts[1]


def _read_s3_text(uri: str) -> str:
    bucket, key = _parse_s3_uri(uri)
    s3 = boto3.client("s3")
    resp = s3.get_object(Bucket=bucket, Key=key)
    return resp["Body"].read().decode("utf-8")


def _read_s3_bytes(uri: str) -> bytes:
    bucket, key = _parse_s3_uri(uri)
    s3 = boto3.client("s3")
    resp = s3.get_object(Bucket=bucket, Key=key)
    return resp["Body"].read()


def _format_csv(raw: str) -> str:
    reader = csv.reader(io.StringIO(raw))
    rows = list(reader)
    if not rows:
        return "Empty CSV file."

    header = rows[0]
    data = rows[1 : MAX_ROWS + 1]
    truncated = len(rows) - 1 > MAX_ROWS

    col_widths = [len(h) for h in header]
    for row in data:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(cell))

    def _fmt_row(cells: list[str]) -> str:
        padded = [c.ljust(col_widths[i]) if i < len(col_widths) else c for i, c in enumerate(cells)]
        return "| " + " | ".join(padded) + " |"

    lines = [_fmt_row(header)]
    lines.append("|" + "|".join("-" * (w + 2) for w in col_widths) + "|")
    for row in data:
        lines.append(_fmt_row(row))

    if truncated:
        lines.append(f"\n[Showing {MAX_ROWS} of {len(rows) - 1} rows]")

    return "\n".join(lines)


def _format_json(raw: str) -> str:
    try:
        data = json.loads(raw)
        formatted = json.dumps(data, indent=2)
        if len(formatted) > MAX_TEXT_CHARS:
            formatted = formatted[:MAX_TEXT_CHARS] + "\n\n[Truncated]"
        return formatted
    except json.JSONDecodeError as exc:
        return f"Invalid JSON: {exc}"


def _format_pdf(raw_bytes: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(raw_bytes))
    pages: list[str] = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append(f"--- Page {i + 1} ---\n{text}")
    full = "\n\n".join(pages)
    if not full.strip():
        return "PDF file contains no extractable text (may be scanned/image-based)."
    if len(full) > MAX_TEXT_CHARS:
        return full[:MAX_TEXT_CHARS] + "\n\n[Truncated]"
    return full
