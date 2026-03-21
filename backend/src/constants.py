from __future__ import annotations

import re

RESULT_ID_RE = re.compile(
    r"\[(?:Summarized — full result stored as|Result ID:)\s*([0-9a-f-]{36})\]"
)

HIDDEN_TOOLS = frozenset({"session_manager"})

S3_OFFLOAD_THRESHOLD = 100_000
