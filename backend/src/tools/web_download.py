from __future__ import annotations

import httpx
from bs4 import BeautifulSoup
from langchain_core.tools import tool


@tool
def web_download(url: str) -> str:
    """Download a web page and return its text content.

    Fetches the URL, strips HTML tags, and returns clean text.
    """
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": "MultiToolChatBot/1.0"})
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        return f"HTTP error fetching {url}: {exc}"

    content_type = resp.headers.get("content-type", "")
    if "text/html" in content_type:
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
    else:
        text = resp.text
    return text
