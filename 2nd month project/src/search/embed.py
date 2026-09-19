"""
Configurable text embedding module supporting Gemini embeddings, disk caching,
and offline TF-IDF fallback vectorization.
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import List, Optional, Union
import numpy as np

from src.config import settings, get_gemini_client

logger = logging.getLogger(__name__)

CACHE_FILE = settings.VECTORSTORE_DIR / "embedding_cache.json"

class EmbeddingManager:
    """Manages embedding generation, vector normalization, caching, and offline fallbacks."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        enable_cache: bool = True,
    ):
        self.model_name = model_name or settings.GEMINI_EMBEDDING_MODEL
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.enable_cache = enable_cache
        self.cache: dict = {}
        self._load_cache()

    def _load_cache(self):
        if self.enable_cache and CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    raw_cache = json.load(f)
                # Purge any fallback vectors (local TF-IDF has > 2000 zeros out of 3072)
                self.cache = {
                    k: v for k, v in raw_cache.items()
                    if isinstance(v, list) and np.sum(np.array(v) == 0) < 2000
                }
            except Exception as e:
                logger.warning(f"Could not load embedding cache: {e}")
                self.cache = {}

    def _save_cache(self):
        if self.enable_cache:
            try:
                settings.VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
                with open(CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.cache, f)
            except Exception as e:
                logger.warning(f"Could not save embedding cache: {e}")

    @staticmethod
    def _hash_text(text: str, model: str) -> str:
        key = f"{model}::{text.strip().lower()}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    @staticmethod
    def normalize_vector(vec: np.ndarray) -> np.ndarray:
        """L2 normalize vector for cosine similarity via inner product."""
        norm = np.linalg.norm(vec)
        if norm == 0:
            return vec
        return vec / norm

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text string."""
        vectors = self.embed_texts([text])
        return vectors[0]

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Embed a list of text strings.
        Checks cache first, queries Gemini for missing texts, and saves cache.
        Falls back to local vectorizer if Gemini API is unavailable or unconfigured.
        """
        if not texts:
            return np.empty((0, settings.EMBEDDING_DIMENSION), dtype=np.float32)

        clean_texts = [t.strip() for t in texts]
        results: List[Optional[np.ndarray]] = [None] * len(clean_texts)
        missing_indices = []
        missing_texts = []

        # Check cache
        for idx, txt in enumerate(clean_texts):
            h = self._hash_text(txt, self.model_name)
            if self.enable_cache and h in self.cache:
                results[idx] = np.array(self.cache[h], dtype=np.float32)
            else:
                missing_indices.append(idx)
                missing_texts.append(txt)

        # If missing texts exist, fetch embeddings
        if missing_texts:
            newly_embedded = None
            is_fallback = False
            if self.api_key:
                try:
                    newly_embedded = self._embed_with_gemini(missing_texts)
                except Exception as exc:
                    logger.warning(f"Gemini embedding API call failed after retries: {exc}. Falling back to local vectorizer.")
                    newly_embedded = self._embed_with_local(missing_texts)
                    is_fallback = True
            else:
                logger.info("No GEMINI_API_KEY provided; using local TF-IDF fallback vectorizer.")
                newly_embedded = self._embed_with_local(missing_texts)
                is_fallback = True

            for idx, vec in zip(missing_indices, newly_embedded):
                norm_vec = self.normalize_vector(vec)
                results[idx] = norm_vec
                # Only cache verified Gemini embeddings, never fallback vectors
                if self.enable_cache and not is_fallback:
                    h = self._hash_text(clean_texts[idx], self.model_name)
                    self.cache[h] = norm_vec.tolist()

            if not is_fallback:
                self._save_cache()

        matrix = np.array(results, dtype=np.float32)
        return matrix

    def _embed_with_gemini(self, texts: List[str]) -> List[np.ndarray]:
        """Fetch dense embeddings from Gemini API with exponential backoff retry."""
        import time
        client = get_gemini_client(api_key=self.api_key)
        vectors: List[np.ndarray] = []

        # Process in batches of 10 to avoid payload limits
        batch_size = 10
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            for text in batch:
                max_retries = 3
                last_exc = None
                for attempt in range(max_retries):
                    try:
                        response = client.models.embed_content(
                            model=self.model_name,
                            contents=text,
                        )
                        raw_values = response.embeddings[0].values
                        vectors.append(np.array(raw_values, dtype=np.float32))
                        last_exc = None
                        break
                    except Exception as exc:
                        last_exc = exc
                        wait_sec = (attempt + 1) * 2
                        logger.warning(
                            f"Gemini embed attempt {attempt + 1}/{max_retries} failed ({exc}). Retrying in {wait_sec}s..."
                        )
                        time.sleep(wait_sec)
                if last_exc:
                    raise last_exc

        return vectors

    def _embed_with_local(self, texts: List[str]) -> List[np.ndarray]:
        """
        Deterministic local fallback vectorizer using TF-IDF and character n-grams.
        Ensures consistent feature representation when offline or in test environments.
        """
        from sklearn.feature_extraction.text import TfidfVectorizer

        target_dim = settings.EMBEDDING_DIMENSION
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            max_features=target_dim,
            sublinear_tf=True,
        )

        # Pad with seed career tokens if training corpus is small
        corpus = list(texts) + [
            "python machine learning data science backend devops cloud sql kubernetes docker fast api"
        ]
        matrix = vectorizer.fit_transform(corpus).toarray()
        fitted_vectors = matrix[: len(texts)]

        output_vectors = []
        for row in fitted_vectors:
            # Pad or truncate to target dimension
            if len(row) < target_dim:
                padded = np.zeros(target_dim, dtype=np.float32)
                padded[: len(row)] = row
                output_vectors.append(padded)
            else:
                output_vectors.append(np.array(row[:target_dim], dtype=np.float32))

        return output_vectors


# Notebook compatibility alias
EmbeddingEngine = EmbeddingManager

__all__ = ["EmbeddingManager", "EmbeddingEngine"]
