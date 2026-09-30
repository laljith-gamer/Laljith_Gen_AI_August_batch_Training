import json
import hashlib
import logging
import time
from pathlib import Path
from typing import List, Optional
import numpy as np

from src.config import settings, get_gemini_client

logger = logging.getLogger(__name__)

CACHE_FILE = settings.VECTORSTORE_DIR / "embedding_cache.json"


class EmbeddingManager:

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        enable_cache: bool = True,
    ):
        self.model_name = model_name or settings.GEMINI_EMBEDDING_MODEL
        self.api_key = api_key or settings.get_gemini_api_key()
        self.enable_cache = enable_cache
        self.cache: dict = {}
        self._load_cache()

    def _load_cache(self):
        if self.enable_cache and CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
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
        norm = np.linalg.norm(vec)
        if norm == 0:
            return vec
        return vec / norm

    def embed_text(self, text: str) -> np.ndarray:
        vectors = self.embed_texts([text])
        return vectors[0]

    def embed_texts(self, texts: List[str], show_progress: bool = True) -> np.ndarray:
        if not texts:
            return np.empty((0, settings.EMBEDDING_DIMENSION), dtype=np.float32)

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required for embedding generation.")

        total = len(texts)
        clean_texts = [t.strip() for t in texts]
        results: List[Optional[np.ndarray]] = [None] * total

        batch_size = 25
        processed_count = 0
        newly_cached = 0

        if show_progress:
            logger.info(f"Embedding jobs: 0 / {total}")

        for i in range(0, total, batch_size):
            end_idx = min(i + batch_size, total)
            batch_slice = slice(i, end_idx)
            batch_texts = clean_texts[batch_slice]
            batch_indices = list(range(i, end_idx))

            missing_texts = []
            missing_indices = []

            for global_idx, txt in zip(batch_indices, batch_texts):
                h = self._hash_text(txt, self.model_name)
                if self.enable_cache and h in self.cache:
                    results[global_idx] = np.array(self.cache[h], dtype=np.float32)
                else:
                    missing_texts.append(txt)
                    missing_indices.append(global_idx)

            if missing_texts:
                new_vectors = self._embed_batch_with_retry(missing_texts)
                for g_idx, vec in zip(missing_indices, new_vectors):
                    norm_vec = self.normalize_vector(vec)
                    results[g_idx] = norm_vec
                    if self.enable_cache:
                        h = self._hash_text(clean_texts[g_idx], self.model_name)
                        self.cache[h] = norm_vec.tolist()
                        newly_cached += 1

                # Incremental persist to disk after each batch so progress is never lost
                if self.enable_cache and newly_cached > 0:
                    self._save_cache()

            processed_count += len(batch_texts)
            if show_progress and (processed_count % 500 == 0 or processed_count == total):
                logger.info(f"Embedding jobs: {processed_count} / {total}")

        return np.array(results, dtype=np.float32)

    def _embed_batch_with_retry(self, texts: List[str]) -> List[np.ndarray]:
        client = get_gemini_client(api_key=self.api_key)
        max_retries = 4
        last_exc = None

        for attempt in range(max_retries):
            try:
                response = client.models.embed_content(
                    model=self.model_name,
                    contents=texts,
                )
                vectors = []
                for emb in response.embeddings:
                    vectors.append(np.array(emb.values, dtype=np.float32))
                return vectors
            except Exception as exc:
                last_exc = exc
                err_str = str(exc)
                wait_sec = (attempt + 1) * 5
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    wait_sec = max(wait_sec, 25)
                logger.warning(
                    f"Embed batch of {len(texts)} failed (attempt {attempt + 1}/{max_retries}): {exc}. "
                    f"Retrying in {wait_sec}s..."
                )
                time.sleep(wait_sec)

        if last_exc:
            raise last_exc
        return []


__all__ = ["EmbeddingManager"]
