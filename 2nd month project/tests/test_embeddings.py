"""
Unit tests for EmbeddingManager, caching, normalization, and local vectorizer fallback.
"""

import numpy as np
import pytest
from src.search.embed import EmbeddingManager

def test_vector_normalization():
    vec = np.array([3.0, 4.0], dtype=np.float32)
    norm_vec = EmbeddingManager.normalize_vector(vec)
    assert np.isclose(np.linalg.norm(norm_vec), 1.0)

def test_local_fallback_embedding():
    # Force local fallback by instantiating without API key
    manager = EmbeddingManager(api_key="", enable_cache=False)
    texts = ["Python software engineer", "Data analyst with SQL and Tableau"]
    vectors = manager.embed_texts(texts)
    assert vectors.shape[0] == 2
    assert vectors.shape[1] > 0
    # Vectors should be normalized
    for v in vectors:
        assert np.isclose(np.linalg.norm(v), 1.0, atol=1e-3)

def test_embedding_cache_mechanism(tmp_path):
    manager = EmbeddingManager(api_key="", enable_cache=True)
    text = "Machine learning specialist"
    v1 = manager.embed_text(text)
    # The second lookup should hit the in-memory cache
    h = manager._hash_text(text, manager.model_name)
    assert h in manager.cache
    v2 = manager.embed_text(text)
    assert np.allclose(v1, v2)
