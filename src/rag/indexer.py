#!/usr/bin/env python3
"""
RAG Indexer using ChromaDB

Uses ChromaDB for vector storage and semantic search.
Embeddings generated with transformers (all-MiniLM-L6-v2) via mean pooling.
Persists to local files in data/chroma/.
"""

import chromadb
import torch
from transformers import AutoTokenizer, AutoModel
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from pathlib import Path


class TransformersEmbeddingFunction:
    """
    ChromaDB-compatible embedding function using transformers directly.
    Applies mean pooling over token embeddings (same as sentence-transformers).
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._model = AutoModel.from_pretrained(model_name)
        self._model.eval()

    def name(self) -> str:
        """
        Return "default" so ChromaDB skips the persisted-EF conflict check.
        This allows swapping embedding implementations without deleting the collection.
        """
        return "default"

    def _encode(self, texts: list[str]) -> list[list[float]]:
        """Shared encoding logic for both documents and queries."""
        encoded = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )
        with torch.no_grad():
            output = self._model(**encoded)

        # Mean pool over token dimension, respecting attention mask
        mask = encoded["attention_mask"].unsqueeze(-1).float()
        embeddings = (output.last_hidden_state * mask).sum(dim=1) / mask.sum(dim=1)

        # L2-normalise so cosine similarity == dot product
        embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
        return embeddings.tolist()

    def __call__(self, input: list[str]) -> list[list[float]]:
        """Embed documents. Called by ChromaDB on upsert."""
        return self._encode(input)

    def embed_query(self, input: list[str]) -> list[list[float]]:
        """Embed query texts. Called by ChromaDB on query."""
        return self._encode(input)


@dataclass
class IncidentDocument:
    """Represents a past incident"""
    incident_id: str
    title: str
    description: str
    client_id: str
    incident_type: str
    value_date: str
    resolution_steps: list[str]
    outcome: str
    metadata: dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)

    def to_text(self) -> str:
        """Create searchable text for embedding"""
        return "\n".join([
            f"Title: {self.title}",
            f"Type: {self.incident_type}",
            f"Description: {self.description}",
            f"Resolution: {' '.join(self.resolution_steps)}",
            f"Outcome: {self.outcome}"
        ])

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "description": self.description,
            "client_id": self.client_id,
            "incident_type": self.incident_type,
            "value_date": self.value_date,
            "resolution_steps": self.resolution_steps,
            "outcome": self.outcome,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class IncidentMatch:
    """Represents a matched incident from RAG search"""
    incident: IncidentDocument
    similarity_score: float
    rank: int


class RAGIndexer:
    """
    RAG system backed by ChromaDB with local file persistence.

    Files stored in persist_dir (default: data/chroma/).
    Uses all-MiniLM-L6-v2 embeddings via transformers with mean pooling.
    """

    COLLECTION_NAME = "incidents"

    def __init__(self, persist_dir: str = "data/chroma") -> None:
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(path=persist_dir)
        self._ef = TransformersEmbeddingFunction()
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"}
        )

        # Local cache of IncidentDocument objects keyed by incident_id
        self._docs: dict[str, IncidentDocument] = {}

        # Populate cache from any already-persisted docs
        self._reload_cache()

    def _reload_cache(self) -> None:
        """Rebuild in-memory doc cache from ChromaDB metadata."""
        import json
        existing = self._collection.get(include=["metadatas"])
        for doc_id, meta in zip(existing["ids"], existing["metadatas"]):
            if doc_id not in self._docs and meta:
                try:
                    self._docs[doc_id] = IncidentDocument(
                        incident_id=meta["incident_id"],
                        title=meta["title"],
                        description=meta["description"],
                        client_id=meta["client_id"],
                        incident_type=meta["incident_type"],
                        value_date=meta["value_date"],
                        resolution_steps=json.loads(meta["resolution_steps"]),
                        outcome=meta["outcome"],
                        metadata=json.loads(meta["extra_metadata"]),
                    )
                except (KeyError, json.JSONDecodeError):
                    pass

    def add_incident(self, incident: IncidentDocument) -> None:
        """Add a single incident to the index."""
        self._add_batch([incident])

    def add_incidents_batch(self, incidents: list[IncidentDocument]) -> None:
        """Add multiple incidents efficiently."""
        self._add_batch(incidents)

    def _add_batch(self, incidents: list[IncidentDocument]) -> None:
        import json
        ids, documents, metadatas = [], [], []
        for inc in incidents:
            ids.append(inc.incident_id)
            documents.append(inc.to_text())
            metadatas.append({
                "incident_id": inc.incident_id,
                "title": inc.title,
                "description": inc.description,
                "client_id": inc.client_id,
                "incident_type": inc.incident_type,
                "value_date": inc.value_date,
                "resolution_steps": json.dumps(inc.resolution_steps),
                "outcome": inc.outcome,
                "extra_metadata": json.dumps(inc.metadata),
            })
            self._docs[inc.incident_id] = inc

        self._collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.0
    ) -> list[IncidentMatch]:
        """
        Semantic search for similar incidents.

        Args:
            query: Natural language search query
            top_k: Number of results to return
            min_similarity: Minimum cosine similarity threshold (0-1)

        Returns:
            List of IncidentMatch sorted by similarity descending
        """
        n = min(top_k, self._collection.count())
        if n == 0:
            return []

        results = self._collection.query(
            query_texts=[query],
            n_results=n,
            include=["metadatas", "distances"]
        )

        matches = []
        for rank, (doc_id, distance) in enumerate(
            zip(results["ids"][0], results["distances"][0])
        ):
            # ChromaDB cosine space returns distance (0=identical, 2=opposite)
            similarity = 1.0 - (distance / 2.0)
            if similarity < min_similarity:
                continue
            incident = self._docs.get(doc_id)
            if incident:
                matches.append(IncidentMatch(
                    incident=incident,
                    similarity_score=round(similarity, 4),
                    rank=rank + 1
                ))

        return matches

    def search_by_type(
        self,
        query: str,
        incident_type: str,
        top_k: int = 5
    ) -> list[IncidentMatch]:
        """Search filtered by incident_type using ChromaDB metadata filtering."""
        n = min(top_k, self._collection.count())
        if n == 0:
            return []

        results = self._collection.query(
            query_texts=[query],
            n_results=n,
            where={"incident_type": incident_type},
            include=["metadatas", "distances"]
        )

        matches = []
        for rank, (doc_id, distance) in enumerate(
            zip(results["ids"][0], results["distances"][0])
        ):
            similarity = 1.0 - (distance / 2.0)
            incident = self._docs.get(doc_id)
            if incident:
                matches.append(IncidentMatch(
                    incident=incident,
                    similarity_score=round(similarity, 4),
                    rank=rank + 1
                ))

        return matches

    def get_incident_by_id(self, incident_id: str) -> Optional[IncidentDocument]:
        """Get incident by ID."""
        return self._docs.get(incident_id)

    def get_stats(self) -> dict[str, Any]:
        """Get indexer statistics."""
        return {
            "total_documents": self._collection.count(),
            "incident_types": list({d.incident_type for d in self._docs.values()}),
            "backend": "chromadb",
        }


# Global singleton
_global_indexer: Optional[RAGIndexer] = None


def get_rag_indexer() -> RAGIndexer:
    """Get global RAGIndexer singleton (auto-loads from persistent storage)."""
    global _global_indexer
    if _global_indexer is None:
        _global_indexer = RAGIndexer()
        print(f"[RAG] Loaded {_global_indexer.get_stats()['total_documents']} incidents from persistent storage")
    return _global_indexer
