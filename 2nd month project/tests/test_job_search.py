"""
Unit tests for FAISS vector store loading and semantic job search.
"""

import pytest
from src.config import settings
from src.models.schemas import ResumeProfile, HumanApprovedProfile
from src.search.faiss_store import FaissVectorStore
from src.search.job_search import JobSearchEngine
from src.human_loop.review import ProfileReviewManager

def test_faiss_store_loading():
    store = FaissVectorStore(settings.JOB_INDEX_DIR)
    assert store.exists(), "Job index was not found on disk"
    loaded = store.load()
    assert loaded is True
    assert store.index.ntotal >= 20
    assert len(store.metadata) == store.index.ntotal

def test_skill_overlap_calculation():
    cand_skills = ["Python", "SQL", "Docker", "FastAPI"]
    job_skills = ["Python", "SQL", "Kubernetes", "AWS", "FastAPI"]
    matched, missing = JobSearchEngine.calculate_skill_overlap(cand_skills, job_skills)
    assert "Python" in matched
    assert "SQL" in matched
    assert "FastAPI" in matched
    assert "Kubernetes" in missing
    assert "AWS" in missing

def test_job_search_retrieves_relevant_roles():
    search_engine = JobSearchEngine()
    profile = ResumeProfile(
        target_role="Data Analyst",
        skills=["SQL", "Python", "Tableau", "Power BI", "Excel"],
        summary="Experienced in business intelligence, data visualization, and reporting.",
    )
    # Approve profile
    container = ProfileReviewManager.initialize_review(profile)
    container = ProfileReviewManager.apply_human_approval(container, profile)

    matches = search_engine.search_matching_jobs(container, top_k=3)
    assert len(matches) > 0
    top_match = matches[0]
    # Check that score is labeled clearly as semantic similarity and within [0, 1]
    assert 0.0 <= top_match.similarity_score <= 1.0
    assert top_match.job.title is not None
    # Matched skills should be identified
    assert len(top_match.matched_skills) > 0

def test_unapproved_profile_refusal():
    search_engine = JobSearchEngine()
    profile = ResumeProfile(
        target_role="Software Engineer",
        skills=["Python", "FastAPI"],
    )
    # Profile initialized but not approved
    unapproved_container = ProfileReviewManager.initialize_review(profile)
    with pytest.raises(PermissionError):
        search_engine.search_matching_jobs(unapproved_container, top_k=3)
