from __future__ import annotations

import json

import httpx
from langchain_core.tools import tool


@tool
def external_api(
    url: str,
    method: str = "GET",
    headers: str = "{}",
    body: str = "",
) -> str:
    """Call an external API and return the response.

    Args:
        url: The full URL to call.
        method: HTTP method (GET, POST, PUT, DELETE).
        headers: JSON string of HTTP headers.
        body: Request body (for POST/PUT).
    """
    method = method.upper()
    if method not in ("GET", "POST", "PUT", "DELETE"):
        return f"Unsupported HTTP method: {method}"

    try:
        parsed_headers = json.loads(headers) if headers else {}
    except json.JSONDecodeError:
        return "Error: headers must be a valid JSON string."

    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            resp = client.request(
                method,
                url,
                headers=parsed_headers,
                content=body if body else None,
            )
    except httpx.HTTPError as exc:
        return f"HTTP error: {exc}"

    try:
        data = resp.json()
        formatted = json.dumps(data, indent=2)
    except (json.JSONDecodeError, ValueError):
        formatted = resp.text

    status_line = f"HTTP {resp.status_code}"
    if len(formatted) > 50_000:
        formatted = formatted[:50_000] + "\n\n[Response truncated]"

    return f"{status_line}\n\n{formatted}"
