"""
Unit tests for Human-in-the-Loop (HITL) review, feedback, and state enforcement.
"""

import pytest
from src.models.enums import ReviewStatus
from src.models.schemas import ResumeProfile
from src.human_loop.review import ProfileReviewManager
from src.human_loop.feedback import FeedbackManager
from src.human_loop.audit import AuditLogger

@pytest.fixture
def sample_ai_profile():
    return ResumeProfile(
        name="John Candidate",
        email="john@example.com",
        target_role="Data Engineer",
        skills=["Python", "SQL", "Spark"],
        years_of_experience=3.0,
        summary="Data engineer with expertise in pipelines.",
    )

def test_initialization_requires_review(sample_ai_profile):
    container = ProfileReviewManager.initialize_review(sample_ai_profile)
    assert container.status == ReviewStatus.REQUIRES_REVIEW
    assert container.is_approved is False

    # Downstream pipeline must refuse unapproved profile
    with pytest.raises(PermissionError) as exc_info:
        ProfileReviewManager.validate_approved(container)
    assert "Human review and explicit approval are required" in str(exc_info.value)

def test_human_edit_override(sample_ai_profile):
    container = ProfileReviewManager.initialize_review(sample_ai_profile)
    
    # Human changes skills and target role
    edited = sample_ai_profile.model_copy(deep=True)
    edited.skills = ["Python", "SQL", "Spark", "Snowflake", "dbt"]
    edited.target_role = "Senior Analytics Engineer"

    updated_container = ProfileReviewManager.apply_human_approval(container, edited)
    assert updated_container.is_approved is True
    assert updated_container.status == ReviewStatus.HUMAN_EDITED
    assert "Snowflake" in updated_container.approved_profile.skills
    assert "dbt" in updated_container.approved_profile.skills
    assert updated_container.approved_profile.target_role == "Senior Analytics Engineer"
    
    # Downstream pipeline now accepts the human-approved profile
    validated = ProfileReviewManager.validate_approved(updated_container)
    assert validated.target_role == "Senior Analytics Engineer"
    assert "Snowflake" in validated.skills

def test_approve_without_edits(sample_ai_profile):
    container = ProfileReviewManager.initialize_review(sample_ai_profile)
    approved_container = ProfileReviewManager.apply_human_approval(container, sample_ai_profile)
    assert approved_container.is_approved is True
    assert approved_container.status == ReviewStatus.APPROVED
    assert "Approved without modifications" in approved_container.change_summary

def test_rejection_and_reset(sample_ai_profile):
    container = ProfileReviewManager.initialize_review(sample_ai_profile)
    rejected = ProfileReviewManager.reject_profile(container, "Missing crucial certifications.")
    assert rejected.is_approved is False
    assert rejected.status == ReviewStatus.REJECTED

    # Reset back to original
    rejected.reset_to_ai()
    assert rejected.status == ReviewStatus.REQUIRES_REVIEW
    assert rejected.is_approved is False

def test_feedback_and_audit_logging():
    # Feedback
    FeedbackManager.record_job_feedback("job_99", "ML Engineer", "relevant", "Data Scientist")
    FeedbackManager.record_mentor_feedback("How to study?", "Practice SQL.", "helpful", ["notes.txt"])
    metrics = FeedbackManager.get_feedback_metrics()
    assert metrics["total_job_feedback"] >= 1
    assert metrics["total_mentor_feedback"] >= 1

    # Audit logging
    AuditLogger.log_event("TEST_EVENT", "SYSTEM", "SUCCESS", {"api_key": "secret123", "action": "test"})
    logs = AuditLogger.get_recent_logs(limit=5)
    assert len(logs) > 0
    # Verify secrets are scrubbed
    last_log = logs[-1]
    if "details" in last_log and "api_key" in last_log["details"]:
        assert last_log["details"]["api_key"] == "[REDACTED]"
