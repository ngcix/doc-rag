"""
FAISS Vector Store Module

This module provides a FAISS-based vector store for fast similarity search.
FAISS (Facebook AI Similarity Search) is optimized for efficient similarity search
and clustering of dense vectors.
"""
from typing import Optional
from pathlib import Path
import pickle
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from specrag.config import settings, VectorDBConfig, ensure_directories
from specrag.path_resolver import normalize_metadata_paths


def read_store_summary(config: Optional[VectorDBConfig] = None) -> Optional[dict]:
    """Read lightweight store summary without loading embeddings."""
    config = config or settings.vectordb
    summary_path = config.faiss_index_dir / f"{config.collection_name}_summary.json"
    if not summary_path.exists():
        return None
    try:
        with open(summary_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


class FaissVectorStore:
    """
    FAISS-based vector store for fast similarity search.
    
    Supports multiple index types:
    - Flat: Exact search, best for smaller datasets
    - IVF: Approximate search, better for large datasets
    - HNSW: Graph-based approximate search
    """
    
    def __init__(self, config: Optional[VectorDBConfig] = None):
        """
        Initialize the FaissVectorStore.
        
        Args:
            config: Vector database configuration.
        """
        self.config = config or settings.vectordb
        self._index = None
        self._metadata = {}
        self._documents = {}
        self._embeddings = {}
        self._id_to_idx = {}
        self._idx_to_id = {}
        self._dimension = None
        self._metadata_loaded = False
        self._embeddings_loaded = False
        self._index_needs_rebuild = False
        ensure_directories()
    
    @property
    def index_path(self) -> Path:
        """Path to the FAISS index file."""
        return self.config.faiss_index_dir / f"{self.config.collection_name}.index"
    
    @property
    def metadata_path(self) -> Path:
        """Path to the metadata file."""
        return self.config.faiss_index_dir / f"{self.config.collection_name}_metadata.pkl"
    
    @property
    def embeddings_path(self) -> Path:
        """Path to the embeddings file."""
        return self.config.faiss_index_dir / f"{self.config.collection_name}_embeddings.pkl"
    
    @property
    def summary_path(self) -> Path:
        """Path to the lightweight summary file."""
        return self.config.faiss_index_dir / f"{self.config.collection_name}_summary.json"

    @classmethod
    def read_summary(cls, config: Optional[VectorDBConfig] = None) -> Optional[dict]:
        """Read lightweight stats without loading the full store."""
        return read_store_summary(config)

    def _ensure_metadata_loaded(self) -> None:
        """Load metadata and document text from disk on first access."""
        if self._metadata_loaded:
            return
        self._metadata_loaded = True

        if not self.metadata_path.exists():
            return

        try:
            with open(self.metadata_path, "rb") as f:
                data = pickle.load(f)
            self._metadata = data.get("metadata", {})
            self._documents = data.get("documents", {})
            self._dimension = data.get("dimension")

            # Backward compatibility: legacy single-file format with embeddings.
            legacy_embeddings = data.get("embeddings", {})
            if legacy_embeddings:
                self._embeddings = legacy_embeddings
                self._embeddings_loaded = True
                self._index_needs_rebuild = True
        except Exception as e:
            print(f"Failed to load metadata: {e}")
            import traceback
            traceback.print_exc()

    def _ensure_embeddings_loaded(self) -> None:
        """Load embeddings from disk when search or vector updates need them."""
        if self._embeddings_loaded:
            return

        self._ensure_metadata_loaded()

        if self.embeddings_path.exists():
            try:
                with open(self.embeddings_path, "rb") as f:
                    data = pickle.load(f)
                self._embeddings = data.get("embeddings", {})
            except Exception as e:
                print(f"Failed to load embeddings: {e}")
                import traceback
                traceback.print_exc()

        self._embeddings_loaded = True
        self._index_needs_rebuild = bool(self._embeddings)

    def _ensure_index_ready(self):
        """Ensure FAISS index is built and ready for search."""
        self._ensure_embeddings_loaded()
        if self._index_needs_rebuild and self._embeddings:
            self._rebuild_index()
            self._index_needs_rebuild = False
            print(f"Rebuilt FAISS index with {self._index.ntotal} vectors")
    
    def _create_index(self, dimension: int):
        """Create a new FAISS index instance."""
        try:
            import faiss
        except ImportError:
            raise ImportError("faiss-cpu is required.")
        
        self._dimension = dimension
        index_type = self.config.faiss_index_type
        
        if index_type == "Flat":
            if self.config.distance_metric == "cosine":
                self._index = faiss.IndexFlatIP(dimension)
            else:
                self._index = faiss.IndexFlatL2(dimension)
        elif index_type == "IVF":
            quantizer = faiss.IndexFlatL2(dimension)
            nlist = min(100, max(1, len(self._embeddings) // 10))
            self._index = faiss.IndexIVFFlat(quantizer, dimension, max(nlist, 1))
        elif index_type == "HNSW":
            self._index = faiss.IndexHNSWFlat(dimension, 32)
        else:
            self._index = faiss.IndexFlatIP(dimension)
        
        print(f"Created FAISS index: {index_type}, dimension: {dimension}")

    def _save_summary(self) -> None:
        summary = {
            "backend": "faiss",
            "collection_name": self.config.collection_name,
            "count": len(self._metadata),
            "index_type": self.config.faiss_index_type,
            "dimension": self._dimension,
            "index_directory": str(self.config.faiss_index_dir),
            "distance_metric": self.config.distance_metric,
        }
        with open(self.summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
    
    def _save(self, include_embeddings: bool = True):
        """Save metadata and optionally embeddings to disk."""
        import faiss

        self.config.faiss_index_dir.mkdir(parents=True, exist_ok=True)
        
        if self._index:
            try:
                faiss.write_index(self._index, str(self.index_path))
            except Exception as e:
                print(f"Warning: Could not save FAISS index file: {e}")

        with open(self.metadata_path, "wb") as f:
            pickle.dump(
                {
                    "metadata": self._metadata,
                    "documents": self._documents,
                    "dimension": self._dimension,
                },
                f,
            )

        if include_embeddings and (self._embeddings_loaded or self._embeddings):
            with open(self.embeddings_path, "wb") as f:
                pickle.dump({"embeddings": self._embeddings}, f)

        self._save_summary()
    
    def update_metadata(self, doc_id: str, new_metadata: dict):
        """
        Update metadata for a document.
        
        Args:
            doc_id: Document ID to update.
            new_metadata: Dictionary of metadata to merge.
        """
        self._ensure_metadata_loaded()
        if doc_id in self._metadata:
            self._metadata[doc_id].update(new_metadata)
            self._save(include_embeddings=False)
            print(f"Updated metadata for {doc_id}")
        else:
            print(f"Warning: Document {doc_id} not found, cannot update metadata")
    
    def get_metadata(self, doc_id: str) -> dict:
        """Get metadata for a document."""
        self._ensure_metadata_loaded()
        return self._metadata.get(doc_id, {})
    
    def get_content(self, doc_id: str) -> Optional[str]:
        """Get the text content of a document."""
        self._ensure_metadata_loaded()
        return self._documents.get(doc_id)
    
    def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: Optional[list[str]] = None,
        metadatas: Optional[list[dict]] = None
    ):
        """
        Add or update vectors.
        
        Args:
            ids: Unique identifiers for each vector.
            embeddings: List of embedding vectors.
            documents: Optional list of original documents.
            metadatas: Optional list of metadata dicts.
        """
        if not embeddings:
            return

        self._ensure_metadata_loaded()
        self._ensure_embeddings_loaded()
            
        dim = len(embeddings[0])
        self._dimension = dim
        
        for i, doc_id in enumerate(ids):
            self._embeddings[doc_id] = embeddings[i]
            if documents:
                self._documents[doc_id] = documents[i]
            if metadatas:
                self._metadata[doc_id] = metadatas[i]
        
        self._rebuild_index()
        self._save()
        print(f"Added/Updated {len(ids)} vectors to FAISS index")
    
    def add_chunks(self, vectorized_chunks: list[dict]):
        """
        Add vectorized chunks to the store.
        
        Args:
            vectorized_chunks: List of dicts from TextVectorizer.vectorize_chunks()
        """
        if not vectorized_chunks:
            return
        
        ids = [chunk["chunk_id"] for chunk in vectorized_chunks]
        embeddings = [chunk["embedding"] for chunk in vectorized_chunks]
        documents = [chunk["content"] for chunk in vectorized_chunks]
        metadatas = [
            {
                "source_file": chunk.get("source_file", ""),
                **chunk.get("metadata", {}),
            }
            for chunk in vectorized_chunks
        ]
        
        metadatas = [
            {
                k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                for k, v in m.items()
            }
            for m in metadatas
        ]
        
        self.add(ids, embeddings, documents, metadatas)
    
    def search_similar(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        threshold: Optional[float] = None
    ) -> list[dict]:
        """
        Search for similar documents.
        
        Args:
            query_embedding: The query embedding vector.
            top_k: Number of top results to return.
            threshold: Optional similarity threshold.
            
        Returns:
            List of search results with documents and scores.
        """
        self._ensure_index_ready()
        
        if self._index is None or self._index.ntotal == 0:
            return []
        
        import faiss
        import numpy as np
        
        query_np = np.array([query_embedding], dtype=np.float32)
        
        if self.config.distance_metric == "cosine":
            faiss.normalize_L2(query_np)
        
        search_k = min(top_k * 4, self._index.ntotal)
        distances, indices = self._index.search(query_np, search_k)
        
        results = []
        for rank, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx == -1:
                continue
            
            doc_id = self._idx_to_id.get(idx)
            if not doc_id:
                continue
            
            if len(results) >= top_k:
                break
            
            if self.config.distance_metric == "cosine":
                similarity = float(dist)
            else:
                similarity = 1 / (1 + float(dist))
            
            if threshold is not None and similarity < threshold:
                continue
            
            results.append({
                "id": doc_id,
                "document": self._documents.get(doc_id),
                "metadata": self._metadata.get(doc_id, {}),
                "distance": float(dist),
                "similarity": similarity,
                "rank": rank + 1,
            })
        
        return results
    
    def delete(self, ids: list[str]):
        """Delete vectors by ID and rebuild index."""
        if not ids:
            return

        self._ensure_embeddings_loaded()
            
        deleted_count = 0
        for doc_id in ids:
            if doc_id in self._embeddings:
                del self._embeddings[doc_id]
                self._documents.pop(doc_id, None)
                self._metadata.pop(doc_id, None)
                deleted_count += 1
                
        if deleted_count > 0:
            self._rebuild_index()
            self._save()
            print(f"Deleted {deleted_count} vectors and rebuilt index")
        
    def _rebuild_index(self):
        """Rebuild the FAISS index from scratch using stored embeddings."""
        if not self._embeddings:
            self._index = None
            self._id_to_idx = {}
            self._idx_to_id = {}
            return

        import faiss
        import numpy as np

        ids = list(self._embeddings.keys())
        matrix = np.array(list(self._embeddings.values()), dtype=np.float32)
        
        if self.config.distance_metric == "cosine":
            faiss.normalize_L2(matrix)
            
        self._create_index(self._dimension)
        self._index.add(matrix)
        
        self._id_to_idx = {doc_id: i for i, doc_id in enumerate(ids)}
        self._idx_to_id = {i: doc_id for i, doc_id in enumerate(ids)}
        
        print(f"Index rebuilt with {self._index.ntotal} vectors.")
    
    def clear(self):
        """Clear all vectors from the index."""
        self._index = None
        self._metadata = {}
        self._documents = {}
        self._embeddings = {}
        self._id_to_idx = {}
        self._idx_to_id = {}
        self._metadata_loaded = True
        self._embeddings_loaded = True
        self._index_needs_rebuild = False
        
        for path in (self.index_path, self.metadata_path, self.embeddings_path, self.summary_path):
            if path.exists():
                path.unlink()
        
        print(f"Cleared FAISS index '{self.config.collection_name}'")
    
    def count(self) -> int:
        """Get the number of vectors in the index."""
        summary = read_store_summary(self.config)
        if summary and not self._metadata_loaded and not self._embeddings_loaded:
            return int(summary.get("count", 0))

        self._ensure_metadata_loaded()
        if self._embeddings_loaded or self._embeddings:
            return len(self._embeddings)
        if self._metadata:
            return len(self._metadata)
        return self._index.ntotal if self._index else 0
    
    def get_stats(self) -> dict:
        """Get statistics about the vector store."""
        summary = read_store_summary(self.config)
        if summary and not self._metadata_loaded:
            return summary

        self._ensure_metadata_loaded()
        return {
            "backend": "faiss",
            "collection_name": self.config.collection_name,
            "count": self.count(),
            "index_type": self.config.faiss_index_type,
            "dimension": self._dimension,
            "index_directory": str(self.config.faiss_index_dir),
            "distance_metric": self.config.distance_metric,
        }
    
    def list_documents(self) -> dict[str, str]:
        """
        List all documents in the store.
        
        Returns:
            Dict mapping ID to source file.
        """
        self._ensure_metadata_loaded()
        if not self._id_to_idx and self._metadata:
            return {
                doc_id: normalize_metadata_paths(meta).get("source_file", "Unknown")
                for doc_id, meta in self._metadata.items()
            }
        return {
            doc_id: normalize_metadata_paths(self._metadata.get(doc_id, {})).get("source_file", "Unknown")
            for doc_id in self._id_to_idx.keys()
        }

    def get_indexed_documents(self) -> tuple[list[str], list[str]]:
        """Return document IDs and text for lexical search indexing."""
        self._ensure_metadata_loaded()
        doc_ids = list(self._documents.keys())
        documents = [self._documents[doc_id] for doc_id in doc_ids]
        return doc_ids, documents


_faiss_store: Optional[FaissVectorStore] = None


def get_faiss_store() -> FaissVectorStore:
    """Get or create the global FAISS store instance."""
    global _faiss_store
    if _faiss_store is None:
        _faiss_store = FaissVectorStore()
    return _faiss_store
