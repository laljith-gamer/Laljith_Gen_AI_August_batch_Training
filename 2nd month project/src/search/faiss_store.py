"""
FAISS Vector Store wrapper supporting IndexFlatIP, metadata persistence, and Top-K retrieval.
"""

import pickle
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import faiss

logger = logging.getLogger(__name__)

class FaissVectorStore:
    """Persistent FAISS vector store with associated document metadata."""

    def __init__(self, index_dir: Path, dimension: int = 3072):
        self.index_dir = Path(index_dir)
        self.dimension = dimension
        self.index: Optional[faiss.IndexFlatIP] = None
        self.metadata: List[Dict[str, Any]] = []
        self.index_file = self.index_dir / "index.faiss"
        self.meta_file = self.index_dir / "metadata.pkl"
        if self.exists():
            self.load()

    def exists(self) -> bool:
        """Check if an index already exists on disk."""
        return self.index_file.exists() and self.meta_file.exists()

    def build_index(self, vectors: np.ndarray, metadata: List[Dict[str, Any]]):
        """Build a new FAISS IndexFlatIP from normalized vectors and metadata."""
        if len(vectors) != len(metadata):
            raise ValueError(f"Vectors count ({len(vectors)}) does not match metadata count ({len(metadata)})")

        dim = vectors.shape[1]
        self.dimension = dim
        self.index = faiss.IndexFlatIP(dim)
        
        # Ensure vectors are float32
        vecs = vectors.astype(np.float32)
        self.index.add(vecs)
        self.metadata = list(metadata)

        self.save()
        logger.info(f"Built and saved FAISS index with {self.index.ntotal} vectors to {self.index_dir}")

    def save(self):
        """Serialize index and metadata to disk."""
        self.index_dir.mkdir(parents=True, exist_ok=True)
        if self.index is not None:
            faiss.write_index(self.index, str(self.index_file))
        with open(self.meta_file, "wb") as f:
            pickle.dump(self.metadata, f)

    def load(self) -> bool:
        """Load index and metadata from disk if available."""
        if not self.exists():
            return False

        try:
            self.index = faiss.read_index(str(self.index_file))
            with open(self.meta_file, "rb") as f:
                self.metadata = pickle.load(f)
            self.dimension = self.index.d
            logger.info(f"Loaded FAISS index with {self.index.ntotal} records from {self.index_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to load FAISS index from {self.index_dir}: {e}")
            return False

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        """
        Query index for Top-K nearest neighbors.
        Returns list of (metadata_dict, similarity_score).
        """
        if self.index is None:
            if not self.load():
                raise RuntimeError(f"No FAISS index available in {self.index_dir}. Please build the index first.")

        # Reshape to (1, dim) and ensure float32
        q_vec = query_vector.astype(np.float32)
        if q_vec.ndim == 1:
            q_vec = np.expand_dims(q_vec, axis=0)

        # L2 normalize query vector for cosine similarity
        norm = np.linalg.norm(q_vec)
        if norm > 0:
            q_vec = q_vec / norm

        actual_k = min(top_k, self.index.ntotal)
        if actual_k <= 0:
            return []

        scores, indices = self.index.search(q_vec, actual_k)

        results: List[Tuple[Dict[str, Any], float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1 and idx < len(self.metadata):
                # Clamp score to [0.0, 1.0] for clean UI display
                clean_score = max(0.0, min(1.0, float(score)))
                results.append((self.metadata[idx], clean_score))

        return results
