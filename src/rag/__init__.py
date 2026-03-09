"""
RAG (Retrieval-Augmented Generation) Module

Provides in-memory vector search for historical incident retrieval.
"""

from src.rag.indexer import (
    InMemoryRAGIndexer,
    IncidentDocument,
    IncidentMatch,
    get_rag_indexer
)
from src.rag.sample_incidents import (
    get_sample_incidents,
    load_incidents_to_rag
)

__all__ = [
    "InMemoryRAGIndexer",
    "IncidentDocument",
    "IncidentMatch",
    "get_rag_indexer",
    "get_sample_incidents",
    "load_incidents_to_rag",
]
