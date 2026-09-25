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
        self.api_key = api_key or settings.GEMINI_API_KEY
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

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, settings.EMBEDDING_DIMENSION), dtype=np.float32)

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required for embedding generation.")

        clean_texts = [t.strip() for t in texts]
        results: List[Optional[np.ndarray]] = [None] * len(clean_texts)
        missing_indices = []
        missing_texts = []

        for idx, txt in enumerate(clean_texts):
            h = self._hash_text(txt, self.model_name)
            if self.enable_cache and h in self.cache:
                results[idx] = np.array(self.cache[h], dtype=np.float32)
            else:
                missing_indices.append(idx)
                missing_texts.append(txt)

        if missing_texts:
            newly_embedded = self._embed_with_gemini(missing_texts)
            for idx, vec in zip(missing_indices, newly_embedded):
                norm_vec = self.normalize_vector(vec)
                results[idx] = norm_vec
                if self.enable_cache:
                    h = self._hash_text(clean_texts[idx], self.model_name)
                    self.cache[h] = norm_vec.tolist()
            self._save_cache()

        return np.array(results, dtype=np.float32)

    def _embed_with_gemini(self, texts: List[str]) -> List[np.ndarray]:
        client = get_gemini_client(api_key=self.api_key)
        vectors: List[np.ndarray] = []

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
                            f"Embed attempt {attempt + 1}/{max_retries} failed ({exc}). Retrying in {wait_sec}s..."
                        )
                        time.sleep(wait_sec)
                if last_exc:
                    raise last_exc

        return vectors


__all__ = ["EmbeddingManager"]
