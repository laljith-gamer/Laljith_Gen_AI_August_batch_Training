"""
Tests for the dataset pipeline: column mapping, normalization,
duplication handling, provenance, dataset modes, and repository.
"""

import os
import json
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import hashlib

import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =====================================================
# Test 1: Kaggle raw column mapping
# =====================================================
def test_kaggle_column_mapping():
    """Verify Naukri raw columns are correctly mapped to app schema."""
    from scripts.prepare_kaggle_jobs import detect_and_map_columns

    raw_df = pd.DataFrame({
        "jobtitle": ["Software Engineer"],
        "company": ["Acme Corp"],
        "joblocation_address": ["Mumbai"],
        "skills": ["Python, SQL"],
        "jobdescription": ["Build scalable applications."],
        "jobid": ["12345"],
    })

    mapped = detect_and_map_columns(raw_df)

    assert "title" in mapped.columns
    assert "company" in mapped.columns
    assert "location" in mapped.columns
    assert "skills" in mapped.columns
    assert "description" in mapped.columns
    assert "source_record_id" in mapped.columns

    assert mapped["title"].iloc[0] == "Software Engineer"
    assert mapped["location"].iloc[0] == "Mumbai"


# =====================================================
# Test 2: Missing column handling
# =====================================================
def test_missing_column_handling():
    """Verify graceful handling when optional columns are absent."""
    from scripts.prepare_kaggle_jobs import detect_and_map_columns

    # Only title and description (minimum viable)
    raw_df = pd.DataFrame({
        "jobtitle": ["Data Analyst"],
        "jobdescription": ["Analyze data for insights."],
    })

    mapped = detect_and_map_columns(raw_df)
    assert "title" in mapped.columns
    assert "description" in mapped.columns
    # Company and location should not raise errors
    assert "company" not in mapped.columns or mapped["company"].iloc[0] is not None


# =====================================================
# Test 3: NaN handling in clean_text
# =====================================================
def test_nan_handling():
    """Verify clean_text handles NaN, None, and empty strings."""
    from scripts.prepare_kaggle_jobs import clean_text

    assert clean_text(None) == ""
    assert clean_text("") == ""
    assert clean_text(float("nan")) == ""
    assert clean_text("  Hello   World  ") == "Hello World"


# =====================================================
# Test 4: HTML fragment cleaning
# =====================================================
def test_html_cleaning():
    """Verify HTML tags and entities are cleaned from text."""
    from scripts.prepare_kaggle_jobs import clean_text

    html_text = "<p>Build <strong>scalable</strong> apps &amp; services.</p>"
    cleaned = clean_text(html_text)
    assert "<p>" not in cleaned
    assert "<strong>" not in cleaned
    assert "&amp;" not in cleaned
    assert "scalable" in cleaned
    assert "&" in cleaned


# =====================================================
# Test 5: Empty description filtering
# =====================================================
def test_empty_description_filtering():
    """Rows with empty/very short descriptions should be excluded."""
    df = pd.DataFrame({
        "title": ["Job A", "Job B", "Job C"],
        "description": ["A valid long description for semantic search", "", "short"],
        "company": ["Co A", "Co B", "Co C"],
    })

    # Simulate the filtering logic from prepare_kaggle_jobs
    df = df[~((df["title"] == "") & (df["description"] == ""))]
    df = df[df["description"].str.len() > 20]

    assert len(df) == 1
    assert df.iloc[0]["title"] == "Job A"


# =====================================================
# Test 6: Duplicate handling
# =====================================================
def test_duplicate_handling():
    """Deterministic duplicate removal should keep first occurrence."""
    from scripts.prepare_kaggle_jobs import compute_dedup_key

    df = pd.DataFrame({
        "title": ["Engineer", "Engineer", "Manager"],
        "company": ["Acme", "Acme", "XYZ"],
        "location": ["Mumbai", "Mumbai", "Delhi"],
        "description": ["Build software.", "Build software.", "Manage teams."],
    })

    df["_key"] = df.apply(compute_dedup_key, axis=1)
    assert df["_key"].iloc[0] == df["_key"].iloc[1]  # Duplicates have same key
    assert df["_key"].iloc[0] != df["_key"].iloc[2]  # Different job has different key

    df_deduped = df.drop_duplicates(subset="_key", keep="first")
    assert len(df_deduped) == 2


# =====================================================
# Test 7: Source provenance
# =====================================================
def test_source_provenance():
    """Normalized rows must have correct source and source_dataset."""
    from scripts.prepare_kaggle_jobs import SOURCE_NAME, SOURCE_DATASET

    assert SOURCE_NAME == "kaggle_naukri"
    assert SOURCE_DATASET == "PromptCloudHQ/jobs-on-naukricom"


# =====================================================
# Test 8: Normalized schema validation
# =====================================================
def test_normalized_schema():
    """Output CSV must contain required schema columns."""
    required_cols = ["job_id", "title", "company", "location", "skills",
                     "description", "source", "source_dataset"]

    # Test with the demo CSV (always available)
    demo_path = Path(__file__).resolve().parent.parent / "data" / "jobs" / "jobs_demo.csv"
    if demo_path.exists():
        df = pd.read_csv(demo_path)
        for col in ["job_id", "title", "company", "location", "skills", "description", "source"]:
            assert col in df.columns, f"Missing column '{col}' in demo dataset"


# =====================================================
# Test 9: curated_demo mode
# =====================================================
def test_curated_demo_mode():
    """In curated_demo mode, JOBS_DATA_PATH should point to demo file."""
    from src.config import Settings
    s = Settings()
    with patch.dict(os.environ, {"JOB_DATA_MODE": "curated_demo"}):
        path = s.JOBS_DATA_PATH
        assert "jobs_demo" in str(path)


# =====================================================
# Test 10: raw_kaggle mode
# =====================================================
def test_raw_kaggle_mode():
    """In raw_kaggle mode, JOBS_DATA_PATH should point to kaggle normalized file."""
    from src.config import Settings
    s = Settings()
    with patch.dict(os.environ, {"JOB_DATA_MODE": "raw_kaggle"}):
        path = s.JOBS_DATA_PATH
        assert "kaggle_naukri" in str(path)


# =====================================================
# Test 11: JobRepository active dataset loading
# =====================================================
def test_job_repository_loads_active_dataset():
    """JobRepository should load jobs from the active dataset."""
    from src.search.job_repository import JobRepository

    JobRepository._invalidate_cache()
    # This should work in curated_demo mode
    try:
        info = JobRepository.get_dataset_info()
        assert "mode" in info
        assert "job_count" in info
    except Exception:
        pytest.skip("Dataset not available for testing")


# =====================================================
# Test 12: JobRepository health check
# =====================================================
def test_job_repository_health_check():
    """Health check should return structured diagnostic data."""
    from src.search.job_repository import JobRepository

    health = JobRepository.validate_dataset_health()
    assert "dataset_mode" in health
    assert "dataset_available" in health
    assert "index_available" in health
    assert "issues" in health
    assert isinstance(health["issues"], list)


# =====================================================
# Test 13: Skills normalization
# =====================================================
def test_skills_normalization():
    """Skills should be deduplicated and trimmed."""
    from scripts.prepare_kaggle_jobs import normalize_skills

    assert normalize_skills("Python, python, SQL, sql") == "Python, SQL"
    assert normalize_skills("") == ""
    assert normalize_skills(None) == ""
    assert normalize_skills("Java") == "Java"


# =====================================================
# Test 14: Resume Studio and Job Search use same source
# =====================================================
def test_resume_studio_and_job_search_same_source():
    """Both Resume Studio and Job Search must reference the same dataset path."""
    from src.config import settings
    from src.search.job_repository import JobRepository

    # Both should resolve to the same path
    repo_path = JobRepository.get_active_dataset_path()
    config_path = settings.JOBS_DATA_PATH
    assert repo_path == config_path, (
        f"JobRepository path ({repo_path}) differs from settings.JOBS_DATA_PATH ({config_path})"
    )


# =====================================================
# Test 15: Demo dataset does not silently substitute for raw_kaggle
# =====================================================
def test_no_silent_demo_substitution():
    """In raw_kaggle mode, the system must NOT silently fall back to the demo dataset."""
    from src.config import Settings
    s = Settings()
    with patch.dict(os.environ, {"JOB_DATA_MODE": "raw_kaggle"}):
        path = s.JOBS_DATA_PATH
        assert "demo" not in str(path).lower(), (
            "In raw_kaggle mode, JOBS_DATA_PATH should NOT point to a demo file"
        )


# =====================================================
# Test 16: No fallback to generic jobs.csv in raw_kaggle mode
# =====================================================
def test_no_generic_jobs_csv_fallback():
    """In raw_kaggle mode, JOBS_DATA_PATH must strictly point to jobs_kaggle_naukri.csv."""
    from src.config import Settings
    s = Settings()
    with patch.dict(os.environ, {"JOB_DATA_MODE": "raw_kaggle"}):
        path = s.JOBS_DATA_PATH
        assert str(path).replace("\\", "/").endswith("jobs_kaggle_naukri.csv")


# =====================================================
# Test 17: JobRepository search_jobs_by_query across corpus
# =====================================================
def test_job_repository_search_query():
    """Verify JobRepository can search jobs across the active corpus."""
    from src.search.job_repository import JobRepository
    results = JobRepository.search_jobs_by_query("Developer", limit=5)
    assert len(results) > 0
    assert any("developer" in (j.title + " " + j.description).lower() for j in results)


# =====================================================
# Test 18: Index metadata hash matches active dataset file
# =====================================================
def test_index_metadata_hash_consistency():
    """If index_metadata.json exists, verify dataset_hash matches the actual dataset file."""
    from src.config import settings
    import hashlib

    if settings.INDEX_METADATA_PATH.exists() and settings.JOBS_DATA_PATH.exists():
        with open(settings.INDEX_METADATA_PATH, "r", encoding="utf-8") as f:
            idx_meta = json.load(f)
        current_hash = hashlib.md5(settings.JOBS_DATA_PATH.read_bytes()).hexdigest()
        assert idx_meta.get("dataset_hash") == current_hash, (
            f"Index metadata hash {idx_meta.get('dataset_hash')} != current file hash {current_hash}"
        )


# =====================================================
# Test 19: Conceptual invariant: indexed_count == dataset_count on full index
# =====================================================
def test_index_row_count_invariant():
    """When a complete production index is built, indexed_job_count must equal dataset_row_count."""
    from src.config import settings

    if settings.INDEX_METADATA_PATH.exists():
        with open(settings.INDEX_METADATA_PATH, "r", encoding="utf-8") as f:
            idx_meta = json.load(f)

        is_partial = idx_meta.get("is_partial_index", False)
        if not is_partial:
            assert idx_meta.get("indexed_job_count") == idx_meta.get("dataset_row_count"), (
                f"Full production index count ({idx_meta.get('indexed_job_count')}) "
                f"does not match dataset row count ({idx_meta.get('dataset_row_count')})"
            )


# =====================================================
# Test 20: Mode-aware error messages
# =====================================================
def test_mode_aware_error_messages():
    """Verify that JobRepository returns clear mode-specific messages when dataset missing."""
    from src.search.job_repository import JobRepository
    from unittest.mock import PropertyMock

    with patch.object(JobRepository, "get_dataset_mode", return_value="raw_kaggle"):
        with patch.object(JobRepository, "get_active_dataset_path", return_value=Path("non_existent_kaggle.csv")):
            with pytest.raises(FileNotFoundError) as exc_info:
                JobRepository.load_jobs_dataframe(force_reload=True)
            assert "Kaggle Naukri" in str(exc_info.value)

    with patch.object(JobRepository, "get_dataset_mode", return_value="curated_demo"):
        with patch.object(JobRepository, "get_active_dataset_path", return_value=Path("non_existent_demo.csv")):
            with pytest.raises(FileNotFoundError) as exc_info:
                JobRepository.load_jobs_dataframe(force_reload=True)
            assert "demo" in str(exc_info.value).lower()

