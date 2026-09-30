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
    # Verify that missing API key strictly raises ValueError without silent fake fallbacks
    manager = EmbeddingManager(api_key="", enable_cache=False)
    texts = ["Python software engineer", "Data analyst with SQL and Tableau"]
    with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
        manager.embed_texts(texts)

def test_embedding_cache_mechanism(tmp_path):
    manager = EmbeddingManager(api_key="mock_key", enable_cache=True)
    text = "Machine learning specialist"
    h = manager._hash_text(text, manager.model_name)
    dummy_vec = np.ones(3072, dtype=np.float32) / np.sqrt(3072)
    manager.cache[h] = dummy_vec.tolist()

    v1 = manager.embed_text(text)
    assert h in manager.cache
    v2 = manager.embed_text(text)
    assert np.allclose(v1, v2)
    assert np.allclose(v1, dummy_vec)
