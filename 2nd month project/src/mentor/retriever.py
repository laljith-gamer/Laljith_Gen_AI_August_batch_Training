"""
Retriever for AI Career Mentor RAG pipeline.
Searches indexed career guides and job corpus documents.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.config import settings
from src.search.embed import EmbeddingManager
from src.search.faiss_store import FaissVectorStore

logger = logging.getLogger(__name__)

class MentorRetriever:
    """Retrieves grounded knowledge chunks and job descriptions for career queries."""

    def __init__(
        self,
        embed_manager: Optional[EmbeddingManager] = None,
        vector_store: Optional[FaissVectorStore] = None,
    ):
        self.embed_manager = embed_manager or EmbeddingManager()
        self.vector_store = vector_store or FaissVectorStore(settings.MENTOR_INDEX_DIR)

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        min_score: float = 0.25,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context chunks with source metadata.
        Returns list of dicts with:
          - 'text': chunk text
          - 'source_title': human-readable document or job title
          - 'filename': source filename (e.g. data_analyst_roadmap.txt, job_JOB_101.txt)
          - 'chunk_index': index of chunk
          - 'snippet': short excerpt
          - 'score': similarity score
        """
        if not query or not query.strip():
            return []

        query_vec = self.embed_manager.embed_text(query.strip())
        raw_results = self.vector_store.search(query_vec, top_k=top_k)

        chunks = []
        for meta, score in raw_results:
            if score >= min_score:
                chunks.append({
                    "text": meta.get("snippet", "") if "text" not in meta else meta["text"],
                    "source_title": meta.get("source_title", meta.get("filename", "Career Document")),
                    "filename": meta.get("filename", "unknown.txt"),
                    "chunk_index": meta.get("chunk_index", 0),
                    "snippet": meta.get("snippet", "")[:200],
                    "score": round(score, 3),
                    "doc_type": meta.get("doc_type", "general"),
                })

        return chunks
