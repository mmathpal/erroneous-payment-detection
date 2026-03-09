#!/usr/bin/env python3
"""
In-Memory RAG Indexer

Uses FAISS for fast similarity search and sentence-transformers for embeddings.
All data stored in memory - suitable for POC/testing.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import pickle


@dataclass
class IncidentDocument:
    """Represents a past incident"""
    incident_id: str
    title: str
    description: str
    client_id: str
    incident_type: str
    value_date: str
    resolution_steps: List[str]
    outcome: str
    metadata: Dict[str, Any]
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
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
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class IncidentMatch:
    """Represents a matched incident from RAG search"""
    incident: IncidentDocument
    similarity_score: float
    rank: int


class InMemoryRAGIndexer:
    """
    In-memory RAG system using FAISS and sentence-transformers

    Features:
    - Fast semantic search with FAISS
    - Local embeddings (no API calls)
    - In-memory storage (no database)
    - Suitable for POC with <10k documents
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", persist_dir: str = "data/rag"):
        """
        Initialize RAG indexer

        Args:
            model_name: sentence-transformers model name
            persist_dir: Directory to store persistent FAISS index files
        """
        self.model_name = model_name
        self.embedding_model = None
        self.index = None
        self.documents: List[IncidentDocument] = []
        self.embeddings: Optional[np.ndarray] = None
        self.embedding_dim = 384  # all-MiniLM-L6-v2 dimension
        self.persist_dir = persist_dir

        # Lazy load to avoid importing if not used
        self._model_loaded = False

        # Create persist directory if needed
        from pathlib import Path
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

    def _load_model(self):
        """Lazy load sentence-transformers model"""
        if not self._model_loaded:
            try:
                from sentence_transformers import SentenceTransformer
                self.embedding_model = SentenceTransformer(self.model_name)
                self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
                self._model_loaded = True
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )

    def _load_faiss(self):
        """Lazy load FAISS"""
        try:
            import faiss
            return faiss
        except ImportError:
            raise ImportError(
                "faiss-cpu not installed. "
                "Install with: pip install faiss-cpu"
            )

    def _create_document_text(self, doc: IncidentDocument) -> str:
        """
        Create searchable text from incident document

        Args:
            doc: Incident document

        Returns:
            Combined text for embedding
        """
        parts = [
            f"Title: {doc.title}",
            f"Type: {doc.incident_type}",
            f"Description: {doc.description}",
            f"Resolution: {' '.join(doc.resolution_steps)}",
            f"Outcome: {doc.outcome}"
        ]
        return "\n".join(parts)

    def add_incident(self, incident: IncidentDocument) -> None:
        """
        Add incident to the index

        Args:
            incident: Incident document to add
        """
        self._load_model()

        # Generate embedding
        text = self._create_document_text(incident)
        embedding = self.embedding_model.encode(text, convert_to_numpy=True)

        # Add to documents
        self.documents.append(incident)

        # Add to embeddings
        if self.embeddings is None:
            self.embeddings = embedding.reshape(1, -1)
        else:
            self.embeddings = np.vstack([self.embeddings, embedding])

        # Rebuild FAISS index
        self._rebuild_index()

    def add_incidents_batch(self, incidents: List[IncidentDocument]) -> None:
        """
        Add multiple incidents efficiently

        Args:
            incidents: List of incident documents
        """
        if not incidents:
            return

        self._load_model()

        # Generate embeddings for all documents
        texts = [self._create_document_text(doc) for doc in incidents]
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)

        # Add to documents
        self.documents.extend(incidents)

        # Add to embeddings
        if self.embeddings is None:
            self.embeddings = embeddings
        else:
            self.embeddings = np.vstack([self.embeddings, embeddings])

        # Rebuild FAISS index
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        """Rebuild FAISS index from current embeddings"""
        if self.embeddings is None or len(self.embeddings) == 0:
            return

        faiss = self._load_faiss()

        # Create FAISS index (L2 distance, can change to inner product for cosine)
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.index.add(self.embeddings.astype('float32'))

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.0
    ) -> List[IncidentMatch]:
        """
        Semantic search for similar incidents

        Args:
            query: Search query
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0-1)

        Returns:
            List of matched incidents with similarity scores
        """
        if not self.documents:
            return []

        self._load_model()

        # Generate query embedding
        query_embedding = self.embedding_model.encode(query, convert_to_numpy=True)
        query_embedding = query_embedding.reshape(1, -1).astype('float32')

        # Search FAISS index
        distances, indices = self.index.search(query_embedding, min(top_k, len(self.documents)))

        # Convert distances to similarity scores (L2 to cosine-like)
        # Normalize: similarity = 1 / (1 + distance)
        similarities = 1.0 / (1.0 + distances[0])

        # Build results
        results = []
        for rank, (idx, sim) in enumerate(zip(indices[0], similarities)):
            if sim >= min_similarity:
                match = IncidentMatch(
                    incident=self.documents[idx],
                    similarity_score=float(sim),
                    rank=rank + 1
                )
                results.append(match)

        return results

    def search_by_type(
        self,
        query: str,
        incident_type: str,
        top_k: int = 5
    ) -> List[IncidentMatch]:
        """
        Search for similar incidents of a specific type

        Args:
            query: Search query
            incident_type: Filter by incident type
            top_k: Number of results

        Returns:
            List of matched incidents
        """
        # Get more results than needed for filtering
        all_results = self.search(query, top_k=top_k * 3)

        # Filter by type
        filtered = [
            match for match in all_results
            if match.incident.incident_type == incident_type
        ]

        # Re-rank
        for rank, match in enumerate(filtered[:top_k]):
            match.rank = rank + 1

        return filtered[:top_k]

    def get_incident_by_id(self, incident_id: str) -> Optional[IncidentDocument]:
        """
        Get incident by ID

        Args:
            incident_id: Incident identifier

        Returns:
            Incident document or None
        """
        for doc in self.documents:
            if doc.incident_id == incident_id:
                return doc
        return None

    def save_to_disk(self) -> None:
        """
        Save index to persistent storage (FAISS index + metadata)

        Creates files in persist_dir:
        - faiss.index: FAISS index file
        - metadata.pkl: Documents and embeddings
        """
        import os
        faiss = self._load_faiss()

        # Save FAISS index
        if self.index is not None:
            index_path = os.path.join(self.persist_dir, "faiss.index")
            faiss.write_index(self.index, index_path)
            print(f"[RAG] Saved FAISS index to {index_path}")

        # Save metadata (documents, embeddings, config)
        metadata = {
            "documents": self.documents,
            "embeddings": self.embeddings,
            "model_name": self.model_name,
            "embedding_dim": self.embedding_dim
        }

        metadata_path = os.path.join(self.persist_dir, "metadata.pkl")
        with open(metadata_path, 'wb') as f:
            pickle.dump(metadata, f)
        print(f"[RAG] Saved metadata to {metadata_path}")

    def load_from_disk(self) -> bool:
        """
        Load index from persistent storage

        Returns:
            True if loaded successfully, False if no index found
        """
        import os
        faiss = self._load_faiss()

        index_path = os.path.join(self.persist_dir, "faiss.index")
        metadata_path = os.path.join(self.persist_dir, "metadata.pkl")

        # Check if files exist
        if not os.path.exists(index_path) or not os.path.exists(metadata_path):
            return False

        try:
            # Load FAISS index
            self.index = faiss.read_index(index_path)
            print(f"[RAG] Loaded FAISS index from {index_path}")

            # Load metadata
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)

            self.documents = metadata["documents"]
            self.embeddings = metadata["embeddings"]
            self.model_name = metadata["model_name"]
            self.embedding_dim = metadata["embedding_dim"]
            print(f"[RAG] Loaded metadata from {metadata_path}")

            return True
        except Exception as e:
            print(f"[RAG] Error loading from disk: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get indexer statistics"""
        return {
            "total_documents": len(self.documents),
            "embedding_dimension": self.embedding_dim,
            "model_name": self.model_name,
            "index_built": self.index is not None,
            "incident_types": list(set(doc.incident_type for doc in self.documents))
        }


# Global singleton instance
_global_indexer: Optional[InMemoryRAGIndexer] = None


def get_rag_indexer() -> InMemoryRAGIndexer:
    """
    Get global RAG indexer instance (singleton)

    Automatically loads from persistent storage if available
    """
    global _global_indexer
    if _global_indexer is None:
        _global_indexer = InMemoryRAGIndexer()
        # Try to load from disk
        loaded = _global_indexer.load_from_disk()
        if loaded:
            print(f"[RAG] Loaded {len(_global_indexer.documents)} incidents from persistent storage")
    return _global_indexer
