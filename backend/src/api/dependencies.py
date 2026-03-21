from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from storage.dynamo import DynamoDBStore
from storage.protocols import Store

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph


@lru_cache
def get_store() -> Store:
    store = DynamoDBStore()
    store.create_table_if_not_exists()
    return store


@lru_cache
def get_graph() -> CompiledStateGraph:
    from agent.graph import build_graph

    return build_graph()
