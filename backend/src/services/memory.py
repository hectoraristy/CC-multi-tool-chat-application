from __future__ import annotations

import hashlib
import json
import logging
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage
from storage.models import UserFact

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel
    from storage.protocols import Store

logger = logging.getLogger(__name__)

FACT_EXTRACTION_PROMPT = (
    "You are a fact-extraction assistant. Given the latest conversation turn, "
    "extract any durable facts about the user that would be useful in future "
    "sessions. Examples: database type, preferred output format, team/role, "
    "common workflows, data schemas.\n\n"
    "Return a JSON array of objects with keys: "
    '"content" (the fact) and "category" (one of: preference, environment, '
    "workflow, schema, general).\n\n"
    "If there are no new durable facts, return an empty array: []\n"
    "Return ONLY valid JSON, no markdown fences or explanation."
)


def _fact_hash(content: str) -> str:
    return hashlib.sha256(content.strip().lower().encode()).hexdigest()[:16]


def extract_and_store_facts(
    llm: BaseChatModel,
    store: Store,
    user_id: str,
    session_id: str,
    user_message: str,
    assistant_message: str,
) -> list[UserFact]:
    """Extract durable user facts from the latest turn and persist new ones."""
    turn_text = f"User: {user_message}\nAssistant: {assistant_message}"

    try:
        resp = llm.invoke(
            [
                SystemMessage(content=FACT_EXTRACTION_PROMPT),
                HumanMessage(content=turn_text),
            ]
        )
        raw = resp.content if isinstance(resp.content, str) else str(resp.content)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        facts_data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        logger.debug("No facts extracted (parse error or empty)")
        return []

    if not isinstance(facts_data, list):
        return []

    existing = store.get_user_facts(user_id)
    existing_hashes = {_fact_hash(f.content) for f in existing}

    new_facts: list[UserFact] = []
    for item in facts_data:
        if not isinstance(item, dict) or "content" not in item:
            continue
        content = str(item["content"]).strip()
        if not content:
            continue
        fh = _fact_hash(content)
        if fh in existing_hashes:
            continue
        existing_hashes.add(fh)

        fact = UserFact(
            user_id=user_id,
            fact_id=fh,
            content=content,
            category=str(item.get("category", "general")),
            source_session=session_id,
        )
        store.store_user_fact(fact)
        new_facts.append(fact)

    if new_facts:
        logger.info("Extracted %d new user facts for user %s", len(new_facts), user_id)
    return new_facts
