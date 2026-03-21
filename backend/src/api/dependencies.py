from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from config import get_settings
from storage.dynamo import DynamoDBStore
from storage.protocols import Store

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph
    from storage.s3 import S3ResultStore


@lru_cache
def get_store() -> Store:
    store = DynamoDBStore()
    store.create_table_if_not_exists()
    return store


@lru_cache
def get_s3_store() -> S3ResultStore | None:
    """Return a shared S3ResultStore instance, or ``None`` if S3 is not configured."""
    settings = get_settings()
    if not settings.s3_results_bucket:
        return None
    from storage.s3 import S3ResultStore

    return S3ResultStore()


@lru_cache
def get_graph() -> CompiledStateGraph:
    from agent.graph import build_graph

    return build_graph()
